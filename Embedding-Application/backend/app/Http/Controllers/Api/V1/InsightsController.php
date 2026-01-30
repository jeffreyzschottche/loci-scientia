<?php

namespace App\Http\Controllers\Api\V1;

use App\Http\Controllers\Controller;
use App\Models\Document;
use App\Models\DocumentSection;
use App\Models\DocumentChunk;
use App\Models\Export;
use App\Services\JsonLdGenerator;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Storage;

class InsightsController extends Controller
{
    public function __construct(
        private JsonLdGenerator $jsonLdGenerator
    ) {}

    /**
     * Get dashboard statistics.
     */
    public function stats(Request $request): JsonResponse
    {
        $userId = $request->user()->id;

        $documents = Document::where('user_id', $userId);
        $totalDocuments = (clone $documents)->count();
        $processedDocuments = (clone $documents)->where('status', 'formatted')->count();
        $failedDocuments = (clone $documents)->where('status', 'failed')->count();
        $processingDocuments = (clone $documents)->where('status', 'processing')->count();

        $documentIds = Document::where('user_id', $userId)->pluck('id');
        $totalSections = DocumentSection::whereIn('document_id', $documentIds)->count();
        $totalChunks = DocumentChunk::whereIn('document_id', $documentIds)->count();

        // Category breakdown
        $categories = Document::where('user_id', $userId)
            ->whereNotNull('category')
            ->groupBy('category')
            ->selectRaw('category, count(*) as count')
            ->pluck('count', 'category')
            ->toArray();

        // Recent activity
        $recentDocuments = Document::where('user_id', $userId)
            ->orderBy('updated_at', 'desc')
            ->limit(5)
            ->get(['id', 'doc_id', 'title', 'status', 'updated_at']);

        // Estimate word count
        $totalWords = DocumentChunk::whereIn('document_id', $documentIds)
            ->get()
            ->sum(fn ($chunk) => str_word_count($chunk->text));

        return response()->json([
            'stats' => [
                'total_documents' => $totalDocuments,
                'processed_documents' => $processedDocuments,
                'failed_documents' => $failedDocuments,
                'processing_documents' => $processingDocuments,
                'total_sections' => $totalSections,
                'total_chunks' => $totalChunks,
                'estimated_words' => $totalWords,
            ],
            'categories' => $categories,
            'recent_documents' => $recentDocuments,
        ]);
    }

    /**
     * Get category overview.
     */
    public function categories(Request $request): JsonResponse
    {
        $userId = $request->user()->id;

        $categories = Document::where('user_id', $userId)
            ->whereNotNull('category')
            ->where('status', 'formatted')
            ->groupBy('category')
            ->selectRaw('category, count(*) as document_count')
            ->get()
            ->map(function ($item) use ($userId) {
                $docIds = Document::where('user_id', $userId)
                    ->where('category', $item->category)
                    ->pluck('id');

                $item->section_count = DocumentSection::whereIn('document_id', $docIds)->count();
                $item->chunk_count = DocumentChunk::whereIn('document_id', $docIds)->count();

                return $item;
            });

        return response()->json(['categories' => $categories]);
    }

    /**
     * Get version tags overview.
     */
    public function versions(Request $request): JsonResponse
    {
        $userId = $request->user()->id;

        $versions = Document::where('user_id', $userId)
            ->whereNotNull('version_tag')
            ->groupBy('version_tag')
            ->selectRaw('version_tag, count(*) as document_count')
            ->orderBy('version_tag', 'desc')
            ->get();

        return response()->json(['versions' => $versions]);
    }

    /**
     * Generate and return a JSON-LD manifest.
     */
    public function exportManifest(Request $request): JsonResponse
    {
        $request->validate([
            'category' => 'nullable|string',
            'version_tag' => 'nullable|string',
            'include_chunks' => 'nullable|boolean',
        ]);

        $category = $request->input('category');
        $versionTag = $request->input('version_tag');

        // Only export user's own documents
        $manifest = $this->generateUserManifest(
            $request->user()->id,
            $category,
            $versionTag
        );

        return response()->json($manifest);
    }

    /**
     * Export chunks as a flat list (optimized for embedding).
     */
    public function exportChunks(Request $request): JsonResponse
    {
        $request->validate([
            'category' => 'nullable|string',
        ]);

        $userId = $request->user()->id;
        $category = $request->input('category');

        $chunks = $this->generateUserChunkList($userId, $category);

        return response()->json($chunks);
    }

    /**
     * Create an export and save to storage.
     */
    public function createExport(Request $request): JsonResponse
    {
        $request->validate([
            'name' => 'nullable|string|max:100',
            'category' => 'nullable|string',
            'format' => 'required|in:manifest,chunks',
        ]);

        $userId = $request->user()->id;
        $category = $request->input('category');
        $format = $request->input('format');

        // Generate export data
        $data = $format === 'chunks'
            ? $this->generateUserChunkList($userId, $category)
            : $this->generateUserManifest($userId, $category);

        // Generate version
        $version = date('Y.m.d') . '-' . substr(md5(json_encode($data)), 0, 8);

        // Count documents and chunks
        $documentIds = Document::where('user_id', $userId)
            ->when($category, fn ($q) => $q->where('category', $category))
            ->where('status', 'formatted')
            ->pluck('id');

        $documentCount = $documentIds->count();
        $chunkCount = DocumentChunk::whereIn('document_id', $documentIds)->count();

        // Save to storage
        $filename = "exports/{$userId}/{$version}-{$format}.json";
        Storage::put($filename, json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));

        // Record export
        $export = Export::create([
            'version' => $version,
            'document_count' => $documentCount,
            'chunk_count' => $chunkCount,
            'metadata' => [
                'format' => $format,
                'category' => $category,
                'filename' => $filename,
                'user_id' => $userId,
                'created_at' => now()->toIso8601String(),
            ],
        ]);

        return response()->json([
            'export' => $export,
            'download_url' => "/api/v1/insights/exports/{$export->id}/download",
        ], 201);
    }

    /**
     * List previous exports.
     */
    public function listExports(Request $request): JsonResponse
    {
        $userId = $request->user()->id;

        $exports = Export::whereJsonContains('metadata->user_id', $userId)
            ->orderBy('created_at', 'desc')
            ->limit(20)
            ->get();

        return response()->json(['exports' => $exports]);
    }

    /**
     * Download an export file.
     */
    public function downloadExport(Request $request, Export $export): mixed
    {
        $userId = $request->user()->id;

        if (($export->metadata['user_id'] ?? null) !== $userId) {
            return response()->json(['message' => 'Unauthorized'], 403);
        }

        $filename = $export->metadata['filename'] ?? null;

        if (!$filename || !Storage::exists($filename)) {
            return response()->json(['message' => 'Export bestand niet gevonden'], 404);
        }

        return Storage::download($filename, "{$export->version}.json");
    }

    /**
     * Generate manifest for a specific user's documents.
     */
    private function generateUserManifest(int $userId, ?string $category = null, ?string $versionTag = null): array
    {
        $query = Document::where('user_id', $userId)
            ->whereNull('parent_id')
            ->where('status', 'formatted')
            ->with(['sections.chunks', 'children']);

        if ($category) {
            $query->where('category', $category);
        }

        if ($versionTag) {
            $query->where('version_tag', $versionTag);
        }

        $documents = $query->orderBy('position')->get();

        return [
            '@context' => 'https://schema.org',
            '@type' => 'Dataset',
            '@id' => "kennisbank:manifest:{$userId}",
            'name' => 'Kennisbank Export',
            'dateCreated' => now()->toIso8601String(),
            'description' => 'Kennisbank export in JSON-LD formaat',
            'hasPart' => $documents->map(fn ($doc) => $this->jsonLdGenerator->forDocument($doc, true, true))->all(),
            'statistics' => $this->jsonLdGenerator->generateStatistics($documents),
        ];
    }

    /**
     * Generate chunk list for a specific user.
     */
    private function generateUserChunkList(int $userId, ?string $category = null): array
    {
        $query = DocumentChunk::whereHas('document', function ($q) use ($userId, $category) {
            $q->where('user_id', $userId)
                ->where('status', 'formatted');
            if ($category) {
                $q->where('category', $category);
            }
        })
            ->with(['document', 'section'])
            ->orderBy('document_id')
            ->orderBy('chunk_index');

        $chunks = $query->get();

        return [
            '@context' => 'https://schema.org',
            '@type' => 'ItemList',
            '@id' => "kennisbank:chunks:{$userId}",
            'name' => 'Kennisbank Chunks voor Embedding',
            'numberOfItems' => $chunks->count(),
            'itemListElement' => $chunks->map(fn ($chunk, $index) => [
                '@type' => 'ListItem',
                'position' => $index + 1,
                'item' => $this->jsonLdGenerator->forChunk($chunk),
            ])->all(),
        ];
    }
}
