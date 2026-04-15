# Handoff: Remove All Relation-Based Logic

## Task
Remove all relation-based logic and features throughout the entire repo. The user confirmed:
1. Remove document hierarchy (parent/children) too — only want documents processed into chunks
2. Remove all relation logic everywhere, make sure nothing breaks
3. Cleanse kennisbank_repo including cached relation files
4. Remove the "Relaties" nav tab from the frontend
5. Add a drop migration so the current DB setup doesn't break

## Repo structure
- `/Embedding-Application/backend/` — Laravel API
- `/Embedding-Application/frontend/` — Nuxt.js frontend
- `/app/backend/` — Python FastAPI + RAG system
- `/kennisbank_repo/` — Git-synced knowledge base (already pulled)

---

## FILES TO DELETE

```
Embedding-Application/backend/app/Models/DocumentRelation.php
Embedding-Application/backend/app/Models/SectionRelation.php
Embedding-Application/backend/app/Http/Controllers/Api/V1/RelationController.php
Embedding-Application/frontend/pages/kennisbank/relations.vue
Embedding-Application/frontend/components/kennisbank/RelationModal.vue
Embedding-Application/frontend/components/kennisbank/DocumentNode.vue   ← only used in relations.vue
kennisbank_repo/knowledge_base/relations/documents.json
kennisbank_repo/knowledge_base/relations/sections.json
```

---

## FILE TO CREATE

### `Embedding-Application/backend/database/migrations/2026_04_15_000001_drop_relation_tables.php`
Drop both relation tables (and parent_id column from documents):
```php
<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::dropIfExists('document_relations');
        Schema::dropIfExists('section_relations');

        if (Schema::hasColumn('documents', 'parent_id')) {
            Schema::table('documents', function (Blueprint $table) {
                $table->dropForeign(['parent_id']);
                $table->dropColumn('parent_id');
            });
        }
    }

    public function down(): void
    {
        // Restore section_relations
        Schema::create('section_relations', function (Blueprint $table) {
            $table->id();
            $table->foreignId('source_section_id')->constrained('document_sections')->onDelete('cascade');
            $table->foreignId('target_section_id')->constrained('document_sections')->onDelete('cascade');
            $table->string('relation_type', 50)->default('references');
            $table->json('metadata')->nullable();
            $table->timestamps();
            $table->unique(['source_section_id', 'target_section_id', 'relation_type'], 'unique_section_relation');
        });

        // Restore document_relations
        Schema::create('document_relations', function (Blueprint $table) {
            $table->id();
            $table->foreignId('source_document_id')->constrained('documents')->cascadeOnDelete();
            $table->foreignId('target_document_id')->constrained('documents')->cascadeOnDelete();
            $table->string('relation_type', 50)->default('references');
            $table->json('metadata')->nullable();
            $table->timestamps();
            $table->unique(['source_document_id', 'target_document_id', 'relation_type'], 'unique_document_relation');
        });

        // Restore parent_id
        Schema::table('documents', function (Blueprint $table) {
            $table->foreignId('parent_id')->nullable()->constrained('documents')->nullOnDelete();
        });
    }
};
```

---

## FILES TO MODIFY

### 1. `Embedding-Application/backend/app/Models/Document.php`
- Remove from `$fillable`: `'parent_id'`
- Remove import: `use Illuminate\Database\Eloquent\Collection;`
- Remove methods: `parent()`, `children()`, `outgoingRelations()`, `incomingRelations()`, `addRelationTo()`, `removeRelationTo()`, `descendants()`, `ancestors()`, `isRoot()`, `depth()`, `moveTo()`
- Keep: `user()`, `sections()`, `chunks()`, `isReady()`, `hasFailed()`, `isProcessing()`
- Keep imports: `BelongsTo`, `HasMany`

### 2. `Embedding-Application/backend/app/Models/DocumentSection.php`
- Remove import: `use Illuminate\Database\Eloquent\Relations\BelongsToMany;`
- Remove methods: `relatedTo()`, `relatedFrom()`, `outgoingRelations()`, `incomingRelations()`, `addRelationTo()`, `removeRelationTo()`
- Keep: `document()`, `chunks()`, `booted()`, `getJsonLdId()`, `wordCount()`

### 3. `Embedding-Application/backend/app/Http/Controllers/Api/V1/LibraryController.php`
- Remove `use App\Models\SectionRelation;`
- Remove methods: `addRelation()`, `removeRelation()`, `relationTypes()`, `moveDocument()`, `reorderSiblings()`
- In `section()`: change `$section->load(['chunks', 'outgoingRelations.targetSection.document', 'incomingRelations.sourceSection.document'])` → `$section->load(['chunks'])`
- In `tree()`: change `->with(['children' => function ($q) { $q->orderBy('position'); }, 'sections' => ...])` → `->with(['sections' => function ($q) { $q->orderBy('order_index'); }])` and remove `->whereNull('parent_id')`; actually keep whereNull until migration runs. Remove `->whereNull('parent_id')` since parent_id is being dropped. Actually: after migration drops parent_id, just load all documents. Change to: `Document::where('user_id', $request->user()->id)->with(['sections' => ...])->get()` (no whereNull, no children).
- In `buildTreeNode()`: remove the `foreach ($document->children ...)` block

### 4. `Embedding-Application/backend/app/Services/JsonLdGenerator.php`
- Remove imports: `use App\Models\DocumentRelation;`, `use App\Models\SectionRelation;`
- In `generateManifest()`: remove `'outgoingRelations.targetDocument'` from `->with([...])`
- In `generateManifestFromDocuments()`: remove `'documentRelations' => $this->generateRelationsGraph($documents),`
- Remove entire `generateRelationsGraph()` private method
- Remove entire `generateSectionRelationsGraph()` private method
- In `generateStructuredFileMap()`: remove lines:
  - `$files['relations/documents.json'] = $this->generateRelationsGraph($documents);`
  - `$files['relations/sections.json'] = $this->generateSectionRelationsGraph($documents);`

### 5. `Embedding-Application/backend/routes/api.php`
- Remove `use App\Http\Controllers\Api\V1\RelationController;`
- Remove route: `Route::get('/library/relation-types', [LibraryController::class, 'relationTypes']);`
- Remove route: `Route::post('/sections/{section}/relations', [LibraryController::class, 'addRelation']);`
- Remove route: `Route::delete('/relations/{relation}', [LibraryController::class, 'removeRelation']);`
- Remove route: `Route::patch('/documents/{document}/move', [LibraryController::class, 'moveDocument']);`
- Remove entire `Route::prefix('relations')` group (graph, types, store, delete)

### 6. `Embedding-Application/frontend/stores/kennisbank.ts`
- Remove from imports: `DocumentRelation`, `RelationTypesResponse`, `GraphNode`, `GraphEdge`, `GraphResponse`
- Remove state vars: `relationTypes`, `documentRelationTypes`, `graphNodes`, `graphEdges`, `graphCategories`
- Remove actions: `addRelation()`, `removeRelation()`, `fetchRelationTypes()`, `fetchGraph()`, `fetchDocumentRelationTypes()`, `createDocumentRelation()`, `deleteDocumentRelation()`
- Remove from return object: all of the above

### 7. `Embedding-Application/frontend/types/Kennisbank.ts`
- Remove interfaces: `SectionRelation`, `DocumentRelation`, `GraphNode`, `GraphEdge`, `GraphResponse`
- Remove from `Document` interface: `outgoing_relations?: DocumentRelation[];` and `incoming_relations?: DocumentRelation[];`
- Remove from `DocumentSection` interface: `outgoing_relations?: SectionRelation[];` and `incoming_relations?: SectionRelation[];`
- Remove `RelationTypesResponse` interface

### 8. `Embedding-Application/frontend/components/kennisbank/TabLayout.vue`
- Remove the entire `<NuxtLink to="/kennisbank/relations" ...>` block (the "Relaties"/"Relations" tab)

### 9. `app/backend/knowledge_library.py`
- Remove entire `_load_document_relations()` function (lines 79-106)
- In `get_library_overview()`: remove `relations = _load_document_relations()` call and remove `'relations': relations,` from return dict

### 10. `kennisbank_repo/knowledge_base/manifest.json`
- Remove the `"documentRelations": []` key at the bottom of the JSON

---

## NOTES
- `kennisbank_sync.py` — checked and does NOT reference relations at all, no changes needed
- `DocumentNode.vue` is only used in `relations.vue`, safe to delete
- The `kennisbank_repo/knowledge_base/relations/` directory will become empty after deleting the two JSON files — the directory itself can be left (git will ignore empty dirs) or removed
- All 4 original migration files for creating relations tables are kept as historical record; the new drop migration handles cleanup
- The `position` column on `documents` is kept (used for ordering, not hierarchy)
