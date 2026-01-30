<?php

namespace App\Services;

use App\Models\Document;
use App\Models\DocumentSection;
use App\Models\DocumentChunk;
use App\Models\DocumentRelation;
use App\Support\JsonLd\DocumentSerializer;
use App\Support\JsonLd\SectionSerializer;
use App\Support\JsonLd\ChunkSerializer;
use Illuminate\Support\Collection;

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
            ->whereNull('parent_id') // Only root documents
            ->where('status', 'formatted')
            ->with(['sections.chunks', 'children', 'outgoingRelations.targetDocument']);

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

        return [
            '@context' => 'https://schema.org',
            '@type' => 'Dataset',
            '@id' => 'kennisbank:manifest',
            'name' => 'Kennisbank Export',
            'dateCreated' => now()->toIso8601String(),
            'description' => 'Volledige kennisbank export in JSON-LD formaat',
            'license' => 'Proprietary',
            'distribution' => [
                '@type' => 'DataDownload',
                'encodingFormat' => 'application/ld+json',
            ],
            'hasPart' => $documents->map(fn ($doc) => $this->forDocument($doc, true, true))->all(),
            'statistics' => $this->generateStatistics($documents),
            'documentRelations' => $this->generateRelationsGraph($documents),
        ];
    }

    /**
     * Generate a graph representation of all document relations.
     */
    private function generateRelationsGraph(Collection $documents): array
    {
        $relations = [];

        foreach ($documents as $doc) {
            foreach ($doc->outgoingRelations as $relation) {
                $targetDoc = $relation->targetDocument;
                if (!$targetDoc) {
                    continue;
                }

                $relations[] = [
                    '@type' => 'LinkRole',
                    'source' => "doc:{$doc->doc_id}",
                    'target' => "doc:{$targetDoc->doc_id}",
                    'linkRelationship' => $relation->relation_type,
                    'description' => DocumentRelation::labelFor($relation->relation_type),
                ];
            }
        }

        return $relations;
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
            'numberOfItems' => $chunks->count(),
            'itemListElement' => $chunks->map(fn ($chunk, $index) => [
                '@type' => 'ListItem',
                'position' => $index + 1,
                'item' => $this->forChunk($chunk),
            ])->all(),
        ];
    }

    /**
     * Generate document hierarchy tree.
     */
    public function generateTree(?int $userId = null): array
    {
        $query = Document::query()
            ->whereNull('parent_id')
            ->with('children')
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

    /**
     * Update the JSON-LD field on a document after processing.
     */
    public function updateDocumentJsonLd(Document $document): void
    {
        $jsonLd = $this->forDocument($document, true, false);
        $document->update(['json_ld' => $jsonLd]);
    }
}
