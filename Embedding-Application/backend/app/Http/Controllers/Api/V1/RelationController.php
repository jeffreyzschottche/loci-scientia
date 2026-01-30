<?php

namespace App\Http\Controllers\Api\V1;

use App\Http\Controllers\Controller;
use App\Models\Document;
use App\Models\DocumentRelation;
use App\Services\JsonLdGenerator;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class RelationController extends Controller
{
    public function __construct(
        private readonly JsonLdGenerator $jsonLdGenerator
    ) {}

    /**
     * Get all documents with their relations for mindmap visualization.
     */
    public function graph(Request $request): JsonResponse
    {
        $documents = Document::where('user_id', $request->user()->id)
            ->where('status', 'formatted')
            ->with(['outgoingRelations.targetDocument', 'incomingRelations.sourceDocument'])
            ->get();

        $nodes = $documents->map(fn ($doc) => [
            'id' => (string) $doc->id,
            'doc_id' => $doc->doc_id,
            'title' => $doc->title,
            'category' => $doc->category,
            'position' => $doc->position,
            'priority' => $doc->priority ?? 0,
        ]);

        $edges = [];
        foreach ($documents as $doc) {
            foreach ($doc->outgoingRelations as $relation) {
                $edges[] = [
                    'id' => (string) $relation->id,
                    'source' => (string) $relation->source_document_id,
                    'target' => (string) $relation->target_document_id,
                    'relation_type' => $relation->relation_type,
                    'label' => DocumentRelation::labelFor($relation->relation_type),
                ];
            }
        }

        // Group documents by category for clustering
        $categories = $documents->groupBy('category')->map(fn ($docs) =>
            $docs->pluck('id')->map(fn ($id) => (string) $id)->all()
        )->all();

        return response()->json([
            'nodes' => $nodes,
            'edges' => $edges,
            'categories' => $categories,
        ]);
    }

    /**
     * Get relation types.
     */
    public function types(): JsonResponse
    {
        return response()->json(['types' => DocumentRelation::types()]);
    }

    /**
     * Create a new document relation.
     */
    public function store(Request $request): JsonResponse
    {
        $validated = $request->validate([
            'source_document_id' => 'required|exists:documents,id',
            'target_document_id' => 'required|exists:documents,id|different:source_document_id',
            'relation_type' => 'required|string|in:' . implode(',', array_keys(DocumentRelation::types())),
            'metadata' => 'nullable|array',
        ]);

        $sourceDoc = Document::findOrFail($validated['source_document_id']);
        $targetDoc = Document::findOrFail($validated['target_document_id']);

        // Verify user owns both documents
        if ($sourceDoc->user_id !== $request->user()->id || $targetDoc->user_id !== $request->user()->id) {
            return response()->json(['message' => 'Niet geautoriseerd'], 403);
        }

        $relation = $sourceDoc->addRelationTo(
            $targetDoc,
            $validated['relation_type'],
            $validated['metadata'] ?? null
        );

        // Regenerate JSON-LD for both documents
        $this->jsonLdGenerator->updateDocumentJsonLd($sourceDoc);
        $this->jsonLdGenerator->updateDocumentJsonLd($targetDoc);

        return response()->json([
            'relation' => $relation->load(['sourceDocument', 'targetDocument']),
        ], 201);
    }

    /**
     * Delete a document relation.
     */
    public function destroy(Request $request, DocumentRelation $relation): JsonResponse
    {
        $sourceDoc = $relation->sourceDocument;
        $targetDoc = $relation->targetDocument;

        if ($sourceDoc->user_id !== $request->user()->id) {
            return response()->json(['message' => 'Niet geautoriseerd'], 403);
        }

        $relation->delete();

        // Regenerate JSON-LD
        $this->jsonLdGenerator->updateDocumentJsonLd($sourceDoc);
        $this->jsonLdGenerator->updateDocumentJsonLd($targetDoc);

        return response()->json(['message' => 'Relatie verwijderd']);
    }
}
