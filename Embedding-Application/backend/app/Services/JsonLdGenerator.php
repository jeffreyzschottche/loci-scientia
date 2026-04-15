<?php

namespace App\Services;

use App\Models\Document;
use App\Models\DocumentSection;
use App\Models\DocumentChunk;
use App\Support\JsonLd\DocumentSerializer;
use App\Support\JsonLd\SectionSerializer;
use App\Support\JsonLd\ChunkSerializer;
use Illuminate\Support\Collection;
use Illuminate\Support\Str;

class JsonLdGenerator
{
    public function __construct(
        private readonly DocumentSerializer $documentSerializer,
        private readonly SectionSerializer $sectionSerializer,
        private readonly ChunkSerializer $chunkSerializer
    ) {}

    /**
     * Generate JSON-LD for a single document.
     */
    public function forDocument(Document $document, bool $includeSections = true, bool $includeChunks = false): array
    {
        return $this->documentSerializer->serialize($document, $includeSections, $includeChunks);
    }

    /**
     * Generate JSON-LD for a single section.
     */
    public function forSection(DocumentSection $section, bool $includeChunks = false): array
    {
        return $this->sectionSerializer->serialize($section, $includeChunks);
    }

    /**
     * Generate JSON-LD for a single chunk.
     */
    public function forChunk(DocumentChunk $chunk): array
    {
        return $this->chunkSerializer->serialize($chunk);
    }

    /**
     * Generate a complete knowledge base manifest.
     * This is the main export format for embedding systems.
     */
    public function generateManifest(?string $category = null, ?string $versionTag = null): array
    {
        $query = Document::query()
            ->where('status', 'formatted')
            ->with(['sections.chunks']);

        if ($category) {
            $query->where('category', $category);
        }

        if ($versionTag) {
            $query->where('version_tag', $versionTag);
        }

        // Order by priority first (lower = higher priority), then by position
        $documents = $query
            ->orderBy('priority')
            ->orderBy('position')
            ->get();

        return $this->generateManifestFromDocuments($documents, 'kennisbank:manifest');
    }

    public function generateManifestFromDocuments(Collection $documents, string $identifier = 'kennisbank:manifest'): array
    {
        return [
            '@context' => 'https://schema.org',
            '@type' => 'Dataset',
            '@id' => $identifier,
            'name' => 'Kennisbank Export',
            'dateCreated' => now()->toIso8601String(),
            'description' => 'Kennisbank export in JSON-LD formaat',
            'license' => 'Proprietary',
            'model' => $this->modelMetadata(),
            'distribution' => [
                '@type' => 'DataDownload',
                'encodingFormat' => 'application/ld+json',
            ],
            'hasPart' => $documents->map(fn ($doc) => $this->forDocument($doc, true, true))->all(),
            'statistics' => $this->generateStatistics($documents),
        ];
    }

    /**
     * Generate a flat list of all chunks (optimized for embedding).
     */
    public function generateChunkList(?string $category = null): array
    {
        $query = DocumentChunk::query()
            ->whereHas('document', function ($q) use ($category) {
                $q->where('status', 'formatted');
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
            '@id' => 'kennisbank:chunks',
            'name' => 'Kennisbank Chunks voor Embedding',
            'model' => $this->modelMetadata(),
            'numberOfItems' => $chunks->count(),
            'itemListElement' => $chunks->map(fn ($chunk, $index) => [
                '@type' => 'ListItem',
                'position' => $index + 1,
                'item' => $this->forChunk($chunk),
            ])->all(),
        ];
    }

    /**
     * Build an associative array of JSON files for structured exports.
     *
     * @return array<string, mixed>
     */
    public function generateStructuredFileMap(Collection $documents): array
    {
        $files = [];
        $modelMeta = $this->modelMetadata();

        $files['manifest.json'] = $this->generateManifestFromDocuments($documents);
        $files['model.json'] = $modelMeta;
        $files['statistics.json'] = $this->generateStatistics($documents);

        $documentsByCategory = $documents->groupBy(fn ($doc) => $doc->category ?? 'uncategorized');
        foreach ($documentsByCategory as $category => $group) {
            $slug = $this->sanitizePathSegment($category ?? 'uncategorized');
            $files["categories/{$slug}.json"] = [
                'category' => $category,
                'documentCount' => $group->count(),
                'documents' => $group->map(fn ($doc) => [
                    '@id' => "doc:{$doc->doc_id}",
                    'title' => $doc->title,
                    'chunkCount' => $doc->chunk_count,
                    'contentDate' => $doc->content_date?->toDateString(),
                ])->values()->all(),
            ];
        }

        foreach ($documents as $document) {
            $docSlug = $this->sanitizePathSegment($document->doc_id ?? (string) $document->id);
            $files["documents/{$docSlug}.json"] = $this->forDocument($document, true, true);

            foreach ($document->sections as $section) {
                $sectionSlug = $this->sanitizePathSegment($section->slug ?? (string) $section->id);
                $files["sections/{$docSlug}/{$sectionSlug}.json"] = $this->sectionSerializer->serialize($section, true);
            }

            $chunks = $document->sections
                ->flatMap(fn ($section) => $section->chunks)
                ->values();

            if ($chunks->isNotEmpty()) {
                $files["chunks/{$docSlug}.json"] = [
                    '@context' => 'https://schema.org',
                    '@type' => 'ItemList',
                    '@id' => "kennisbank:chunks:doc:{$document->doc_id}",
                    'name' => "Chunks voor {$document->title}",
                    'document' => "doc:{$document->doc_id}",
                    'model' => $modelMeta,
                    'numberOfItems' => $chunks->count(),
                    'itemListElement' => $chunks->map(function ($chunk, $index) {
                        return [
                            '@type' => 'ListItem',
                            'position' => $index + 1,
                            'item' => $this->forChunk($chunk),
                        ];
                    })->all(),
                ];
            }
        }

        return $files;
    }

    /**
     * Generate document hierarchy tree.
     */
    public function generateTree(?int $userId = null): array
    {
        $query = Document::query()
            ->orderBy('position');

        if ($userId) {
            $query->where('user_id', $userId);
        }

        $documents = $query->get();

        return [
            '@context' => 'https://schema.org',
            '@type' => 'ItemList',
            '@id' => 'kennisbank:tree',
            'name' => 'Kennisbank Structuur',
            'itemListElement' => $documents->map(fn ($doc) => $this->documentSerializer->serializeTree($doc))->all(),
        ];
    }

    /**
     * Generate statistics about the knowledge base.
     */
    public function generateStatistics(?Collection $documents = null): array
    {
        if ($documents === null) {
            $documents = Document::where('status', 'formatted')->get();
        }

        $totalChunks = DocumentChunk::whereIn('document_id', $documents->pluck('id'))->count();
        $totalSections = DocumentSection::whereIn('document_id', $documents->pluck('id'))->count();
        $totalWords = DocumentChunk::whereIn('document_id', $documents->pluck('id'))
            ->get()
            ->sum(fn ($chunk) => str_word_count($chunk->text));

        $categories = $documents->groupBy('category')->map->count();

        return [
            'documentCount' => $documents->count(),
            'sectionCount' => $totalSections,
            'chunkCount' => $totalChunks,
            'estimatedWordCount' => $totalWords,
            'categories' => $categories->all(),
            'generatedAt' => now()->toIso8601String(),
        ];
    }

    private function modelMetadata(): array
    {
        return [
            'model' => config('embedding.model'),
            'vectorDimension' => (int) config('embedding.vector_dimension', 768),
            'chunkTokens' => (int) config('embedding.chunk_tokens', 448),
            'chunkOverlapTokens' => (int) config('embedding.chunk_overlap_tokens', 96),
        ];
    }

    private function sanitizePathSegment(string $value): string
    {
        $slug = Str::slug($value, '-');

        return $slug !== '' ? $slug : 'item';
    }

    /**
     * Update the JSON-LD field on a document after processing.
     */
    public function updateDocumentJsonLd(Document $document): void
    {
        $jsonLd = $this->forDocument($document, true, false);
        $document->update(['json_ld' => $jsonLd]);
    }
}
