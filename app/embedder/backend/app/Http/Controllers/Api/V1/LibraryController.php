<?php

namespace App\Http\Controllers\Api\V1;

use App\Http\Controllers\Controller;
use App\Models\Document;
use App\Models\DocumentSection;
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
     * Get the full document tree.
     */
    public function tree(Request $request): JsonResponse
    {
        $documents = Document::where('user_id', $request->user()->id)
            ->with(['sections' => function ($q) {
                $q->orderBy('order_index');
            }])
            ->get()
            ->sortBy([
                ['position', 'asc'],
                ['created_at', 'desc'],
            ])
            ->values();

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

        $this->jsonLdGenerator->updateDocumentJsonLd($document);

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

        $section->load(['chunks']);

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

        $this->jsonLdGenerator->updateDocumentJsonLd($document);

        return response()->json(['section' => $section->fresh()]);
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

        foreach ($document->sections as $section) {
            $node['children'][] = [
                'id' => $section->id,
                'title' => $section->title,
                'slug' => $section->slug,
                'type' => 'section',
                'document_id' => $document->id,
            ];
        }

        return $node;
    }
}
