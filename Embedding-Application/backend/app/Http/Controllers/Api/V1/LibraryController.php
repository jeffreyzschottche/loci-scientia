<?php

namespace App\Http\Controllers\Api\V1;

use App\Http\Controllers\Controller;
use App\Models\Document;
use App\Models\DocumentSection;
use App\Models\SectionRelation;
use App\Services\JsonLdGenerator;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;

class LibraryController extends Controller
{
    public function __construct(
        private JsonLdGenerator $jsonLdGenerator
    ) {}

    /**
     * Get the full document tree (hierarchy).
     */
    public function tree(Request $request): JsonResponse
    {
        $documents = Document::where('user_id', $request->user()->id)
            ->whereNull('parent_id')
            ->with(['children' => function ($q) {
                $q->orderBy('position');
            }, 'sections' => function ($q) {
                $q->orderBy('order_index');
            }])
            ->orderBy('position')
            ->orderBy('created_at', 'desc')
            ->get();

        $tree = $documents->map(fn ($doc) => $this->buildTreeNode($doc));

        return response()->json(['tree' => $tree]);
    }

    /**
     * Get a single document with all details.
     */
    public function document(Request $request, Document $document): JsonResponse
    {
        if ($document->user_id !== $request->user()->id) {
            return response()->json(['message' => 'Unauthorized'], 403);
        }

        $document->load([
            'sections' => function ($q) {
                $q->orderBy('order_index')->with('chunks');
            },
            'children',
            'parent',
        ]);

        return response()->json([
            'document' => $document,
            'json_ld' => $this->jsonLdGenerator->forDocument($document),
        ]);
    }

    /**
     * Update document metadata.
     */
    public function updateDocument(Request $request, Document $document): JsonResponse
    {
        if ($document->user_id !== $request->user()->id) {
            return response()->json(['message' => 'Unauthorized'], 403);
        }

        $validated = $request->validate([
            'title' => 'sometimes|string|max:255',
            'category' => 'nullable|string|max:100',
            'version_tag' => 'nullable|string|max:50',
            'description' => 'nullable|string|max:1000',
        ]);

        $document->update($validated);

        // Regenerate JSON-LD
        $this->jsonLdGenerator->updateDocumentJsonLd($document);

        return response()->json(['document' => $document->fresh()]);
    }

    /**
     * Move a document in the hierarchy.
     */
    public function moveDocument(Request $request, Document $document): JsonResponse
    {
        if ($document->user_id !== $request->user()->id) {
            return response()->json(['message' => 'Unauthorized'], 403);
        }

        $validated = $request->validate([
            'parent_id' => 'nullable|exists:documents,id',
            'position' => 'nullable|integer|min:0',
        ]);

        // Prevent circular references
        if (isset($validated['parent_id'])) {
            $newParent = Document::find($validated['parent_id']);
            if ($newParent && $document->descendants()->contains('id', $newParent->id)) {
                return response()->json([
                    'message' => 'Kan document niet naar een eigen subdocument verplaatsen',
                ], 422);
            }
        }

        $document->update([
            'parent_id' => $validated['parent_id'] ?? null,
            'position' => $validated['position'] ?? $document->position,
        ]);

        // Reorder siblings if position changed
        if (isset($validated['position'])) {
            $this->reorderSiblings($document);
        }

        return response()->json(['document' => $document->fresh()]);
    }

    /**
     * Get a section with details.
     */
    public function section(Request $request, DocumentSection $section): JsonResponse
    {
        $document = $section->document;

        if ($document->user_id !== $request->user()->id) {
            return response()->json(['message' => 'Unauthorized'], 403);
        }

        $section->load(['chunks', 'outgoingRelations.targetSection.document', 'incomingRelations.sourceSection.document']);

        return response()->json([
            'section' => $section,
            'json_ld' => $this->jsonLdGenerator->forSection($section, true),
        ]);
    }

    /**
     * Update a section.
     */
    public function updateSection(Request $request, DocumentSection $section): JsonResponse
    {
        $document = $section->document;

        if ($document->user_id !== $request->user()->id) {
            return response()->json(['message' => 'Unauthorized'], 403);
        }

        $validated = $request->validate([
            'title' => 'sometimes|string|max:255',
            'text' => 'sometimes|string',
            'metadata' => 'nullable|array',
        ]);

        $section->update($validated);

        // Regenerate document JSON-LD
        $this->jsonLdGenerator->updateDocumentJsonLd($document);

        return response()->json(['section' => $section->fresh()]);
    }

    /**
     * Add a relation between sections.
     */
    public function addRelation(Request $request, DocumentSection $section): JsonResponse
    {
        $document = $section->document;

        if ($document->user_id !== $request->user()->id) {
            return response()->json(['message' => 'Unauthorized'], 403);
        }

        $validated = $request->validate([
            'target_section_id' => 'required|exists:document_sections,id',
            'relation_type' => 'required|string|in:' . implode(',', array_keys(SectionRelation::types())),
            'metadata' => 'nullable|array',
        ]);

        $targetSection = DocumentSection::findOrFail($validated['target_section_id']);

        // Verify user owns target document too
        if ($targetSection->document->user_id !== $request->user()->id) {
            return response()->json(['message' => 'Kan geen relatie maken naar document van andere gebruiker'], 403);
        }

        // Prevent self-reference
        if ($section->id === $targetSection->id) {
            return response()->json(['message' => 'Sectie kan niet naar zichzelf verwijzen'], 422);
        }

        $relation = $section->addRelationTo(
            $targetSection,
            $validated['relation_type'],
            $validated['metadata'] ?? null
        );

        // Regenerate JSON-LD for both documents
        $this->jsonLdGenerator->updateDocumentJsonLd($document);
        if ($document->id !== $targetSection->document_id) {
            $this->jsonLdGenerator->updateDocumentJsonLd($targetSection->document);
        }

        return response()->json([
            'relation' => $relation->load(['sourceSection', 'targetSection']),
        ], 201);
    }

    /**
     * Remove a relation.
     */
    public function removeRelation(Request $request, SectionRelation $relation): JsonResponse
    {
        $sourceDocument = $relation->sourceSection->document;

        if ($sourceDocument->user_id !== $request->user()->id) {
            return response()->json(['message' => 'Unauthorized'], 403);
        }

        $targetDocument = $relation->targetSection->document;

        $relation->delete();

        // Regenerate JSON-LD for affected documents
        $this->jsonLdGenerator->updateDocumentJsonLd($sourceDocument);
        if ($sourceDocument->id !== $targetDocument->id) {
            $this->jsonLdGenerator->updateDocumentJsonLd($targetDocument);
        }

        return response()->json(['message' => 'Relatie verwijderd']);
    }

    /**
     * Get available relation types.
     */
    public function relationTypes(): JsonResponse
    {
        return response()->json(['types' => SectionRelation::types()]);
    }

    /**
     * Search sections across all documents.
     */
    public function search(Request $request): JsonResponse
    {
        $request->validate([
            'query' => 'required|string|min:2|max:100',
            'category' => 'nullable|string',
        ]);

        $query = $request->input('query');
        $category = $request->input('category');

        $sections = DocumentSection::whereHas('document', function ($q) use ($request, $category) {
            $q->where('user_id', $request->user()->id);
            if ($category) {
                $q->where('category', $category);
            }
        })
            ->where(function ($q) use ($query) {
                $q->where('title', 'like', "%{$query}%")
                    ->orWhere('text', 'like', "%{$query}%");
            })
            ->with('document:id,doc_id,title,category')
            ->limit(50)
            ->get(['id', 'document_id', 'title', 'slug']);

        return response()->json(['sections' => $sections]);
    }

    /**
     * Build a tree node for a document.
     */
    private function buildTreeNode(Document $document): array
    {
        $node = [
            'id' => $document->id,
            'doc_id' => $document->doc_id,
            'title' => $document->title,
            'category' => $document->category,
            'status' => $document->status,
            'position' => $document->position,
            'type' => 'document',
            'children' => [],
        ];

        // Add sections as children
        foreach ($document->sections as $section) {
            $node['children'][] = [
                'id' => $section->id,
                'title' => $section->title,
                'slug' => $section->slug,
                'type' => 'section',
                'document_id' => $document->id,
            ];
        }

        // Add child documents
        foreach ($document->children as $child) {
            $node['children'][] = $this->buildTreeNode($child);
        }

        return $node;
    }

    /**
     * Reorder siblings after a position change.
     */
    private function reorderSiblings(Document $document): void
    {
        $siblings = Document::where('parent_id', $document->parent_id)
            ->where('id', '!=', $document->id)
            ->orderBy('position')
            ->get();

        $position = 0;
        foreach ($siblings as $sibling) {
            if ($position === $document->position) {
                $position++;
            }
            if ($sibling->position !== $position) {
                $sibling->update(['position' => $position]);
            }
            $position++;
        }
    }
}
