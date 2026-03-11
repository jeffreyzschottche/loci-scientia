<?php

namespace App\Http\Controllers\Api\V1;

use App\Http\Controllers\Controller;
use App\Models\Document;
use App\Services\JsonLdGenerator;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;

class PriorityController extends Controller
{
    public function __construct(
        private readonly JsonLdGenerator $jsonLdGenerator
    ) {}

    /**
     * Get documents grouped by category with priorities.
     */
    public function index(Request $request): JsonResponse
    {
        $documents = Document::where('user_id', $request->user()->id)
            ->where('status', 'formatted')
            ->orderBy('category')
            ->orderBy('priority')
            ->orderBy('title')
            ->get(['id', 'doc_id', 'title', 'category', 'priority']);

        $byCategory = $documents->groupBy(fn ($doc) => $doc->category ?? 'Geen categorie');

        return response()->json(['categories' => $byCategory]);
    }

    /**
     * Update priority for a single document.
     */
    public function update(Request $request, Document $document): JsonResponse
    {
        if ($document->user_id !== $request->user()->id) {
            return response()->json(['message' => 'Niet geautoriseerd'], 403);
        }

        $validated = $request->validate([
            'priority' => 'required|integer|min:0',
        ]);

        $document->update(['priority' => $validated['priority']]);

        // Regenerate JSON-LD
        $this->jsonLdGenerator->updateDocumentJsonLd($document);

        return response()->json(['document' => $document]);
    }

    /**
     * Bulk update priorities for documents (for drag & drop).
     */
    public function bulkUpdate(Request $request): JsonResponse
    {
        $validated = $request->validate([
            'priorities' => 'required|array',
            'priorities.*.id' => 'required|exists:documents,id',
            'priorities.*.priority' => 'required|integer|min:0',
        ]);

        $userId = $request->user()->id;
        $documentIds = array_column($validated['priorities'], 'id');

        // Verify user owns all documents
        $ownedCount = Document::whereIn('id', $documentIds)
            ->where('user_id', $userId)
            ->count();

        if ($ownedCount !== count($documentIds)) {
            return response()->json(['message' => 'Niet geautoriseerd'], 403);
        }

        DB::transaction(function () use ($validated, $userId) {
            foreach ($validated['priorities'] as $item) {
                Document::where('id', $item['id'])
                    ->where('user_id', $userId)
                    ->update(['priority' => $item['priority']]);
            }
        });

        // Regenerate JSON-LD for affected documents
        $documents = Document::whereIn('id', $documentIds)->get();

        foreach ($documents as $doc) {
            $this->jsonLdGenerator->updateDocumentJsonLd($doc);
        }

        return response()->json(['message' => 'Prioriteiten bijgewerkt']);
    }
}
