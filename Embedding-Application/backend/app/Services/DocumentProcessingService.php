<?php

namespace App\Services;

use App\Enums\ProcessingStage;
use App\Models\Document;
use App\Models\DocumentSection;
use App\Models\DocumentChunk;
use App\Support\DocumentParsing\DocumentParserManager;
use App\Support\Chunking\TextChunker;
use App\Support\Chunking\ChunkIdGenerator;
use App\Support\Chunking\ChunkHasher;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Storage;
use RuntimeException;

class DocumentProcessingService
{
    public function __construct(
        private readonly DocumentParserManager $parserManager,
        private readonly TextChunker $chunker,
        private readonly ChunkIdGenerator $idGenerator,
        private readonly ChunkHasher $hasher,
        private readonly JsonLdGenerator $jsonLdGenerator
    ) {}

    /**
     * Process a document through all stages.
     */
    public function process(Document $document, array $options = []): void
    {
        try {
            $this->updateStage($document, ProcessingStage::PARSING, 0);

            // Stage 1: Parse document
            $parsedDocument = $this->parseDocument($document, $options);
            $this->updateStage($document, ProcessingStage::PARSING, 100);

            // Stage 2: Create sections and chunks
            $this->updateStage($document, ProcessingStage::CHUNKING, 0);
            $this->createSectionsAndChunks($document, $parsedDocument);
            $this->updateStage($document, ProcessingStage::CHUNKING, 100);

            // Stage 3: Generate JSON-LD
            $this->updateStage($document, ProcessingStage::GENERATING_JSONLD, 0);
            $this->generateJsonLd($document);
            $this->updateStage($document, ProcessingStage::GENERATING_JSONLD, 100);

            // Mark as ready
            $document->update([
                'status' => 'formatted',
                'processing_stage' => ProcessingStage::READY,
                'processing_progress' => 100,
                'parsed_at' => now(),
                'metadata' => $this->mergeMetadata($document, [
                    'embedding' => $this->embeddingMetadata(),
                    'last_embedded_at' => now()->toIso8601String(),
                ]),
            ]);

            Log::info("Document processed successfully", [
                'document_id' => $document->id,
            ]);

        } catch (\Throwable $e) {
            $this->handleError($document, $e);
            throw $e;
        }
    }

    /**
     * Parse the document file.
     */
    private function parseDocument(Document $document, array $options): \App\Support\DocumentParsing\ParsedDocument
    {
        $relativePath = "documents/{$document->filename}";

        if (!Storage::exists($relativePath)) {
            throw new RuntimeException("Bestand niet gevonden: {$relativePath}");
        }

        $filePath = Storage::path($relativePath);
        $parser = $this->parserManager->forMime($document->mime_type);

        // Merge options with document data
        $parseOptions = array_merge([
            'doc_id' => $document->doc_id,
            'title' => $document->title,
            'description' => $document->description,
            'category' => $document->category,
        ], $options);

        return $parser->parse($filePath, $parseOptions);
    }

    /**
     * Create sections and chunks from parsed document.
     */
    private function createSectionsAndChunks(Document $document, \App\Support\DocumentParsing\ParsedDocument $parsedDocument): void
    {
        DB::transaction(function () use ($document, $parsedDocument) {
            // Clear existing sections and chunks
            $document->chunks()->delete();
            $document->sections()->delete();

            $totalChunks = 0;
            $contentDate = $document->content_date?->toDateString();

            foreach ($parsedDocument->sections as $index => $sectionData) {
                // Create section
                $section = DocumentSection::create([
                    'document_id' => $document->id,
                    'title' => $sectionData['title'],
                    'slug' => $sectionData['slug'],
                    'order_index' => $sectionData['order_index'] ?? $index,
                    'text' => $sectionData['text'],
                    'metadata' => $sectionData['metadata'] ?? null,
                ]);

                // Create chunks for this section
                $chunks = $this->chunker->chunk($sectionData['text']);
                $pageRanges = $sectionData['metadata']['page_ranges'] ?? [];

                foreach ($chunks as $chunkIndex => $chunkData) {
                    $chunkText = $chunkData['text'];
                    $tokenCount = $chunkData['token_count'] ?? $this->chunker->estimateTokenCount($chunkText);
                    $pages = $this->mapChunkToPages(
                        $chunkData['char_start'] ?? null,
                        $chunkData['char_end'] ?? null,
                        $pageRanges
                    );
                    $chunkMetadata = array_filter([
                        'word_count' => $chunkData['word_count'] ?? null,
                        'content_date' => $contentDate,
                        'embedding_model' => config('embedding.model'),
                        'pages' => $pages ?: null,
                    ], static fn ($value) => $value !== null);

                    $chunkId = $this->idGenerator->generate(
                        $document->doc_id,
                        $section->slug,
                        $chunkIndex
                    );

                    DocumentChunk::create([
                        'document_id' => $document->id,
                        'section_id' => $section->id,
                        'chunk_id' => $chunkId,
                        'chunk_index' => $totalChunks,
                        'text' => $chunkText,
                        'token_count' => $tokenCount,
                        'content_hash' => $this->hasher->hash($chunkText),
                        'metadata' => empty($chunkMetadata) ? null : $chunkMetadata,
                    ]);

                    $totalChunks++;
                }

                // Update progress
                $progress = (int) (($index + 1) / count($parsedDocument->sections) * 100);
                $this->updateStage($document, ProcessingStage::CHUNKING, $progress);
            }

            // Update document metadata
            $document->update([
                'chunk_count' => $totalChunks,
                'metadata' => $this->mergeMetadata($document, $parsedDocument->metadata ?? []),
            ]);
        });
    }

    /**
     * Generate JSON-LD for the document.
     */
    private function generateJsonLd(Document $document): void
    {
        $document->refresh();
        $this->jsonLdGenerator->updateDocumentJsonLd($document);
    }

    /**
     * Update processing stage and progress.
     */
    private function updateStage(Document $document, ProcessingStage $stage, int $progress): void
    {
        $document->update([
            'processing_stage' => $stage,
            'processing_progress' => $progress,
        ]);
    }

    /**
     * Handle processing error.
     */
    private function handleError(Document $document, \Throwable $e): void
    {
        Log::error("Document processing failed", [
            'document_id' => $document->id,
            'error' => $e->getMessage(),
            'trace' => $e->getTraceAsString(),
        ]);

        $document->update([
            'status' => 'failed',
            'processing_stage' => ProcessingStage::FAILED,
            'processing_progress' => 0,
            'metadata' => array_merge($document->metadata ?? [], [
                'error' => $e->getMessage(),
                'failed_at' => now()->toIso8601String(),
            ]),
        ]);
    }

    /**
     * Find which page numbers a chunk's char range overlaps. Empty array if
     * the section has no page-range metadata (non-PDF sources).
     *
     * @param array<int, array{page:int,start:int,end:int}> $pageRanges
     * @return array<int, int>
     */
    private function mapChunkToPages(?int $chunkStart, ?int $chunkEnd, array $pageRanges): array
    {
        if ($chunkStart === null || $chunkEnd === null || empty($pageRanges)) {
            return [];
        }

        $pages = [];
        foreach ($pageRanges as $range) {
            $start = (int) ($range['start'] ?? 0);
            $end = (int) ($range['end'] ?? 0);
            if ($chunkStart < $end && $chunkEnd > $start) {
                $pages[] = (int) $range['page'];
            }
        }

        return array_values(array_unique($pages));
    }

    private function mergeMetadata(Document $document, array $payload): array
    {
        $existing = $document->metadata;

        if (! is_array($existing)) {
            $existing = [];
        }

        return array_replace_recursive($existing, $payload);
    }

    private function embeddingMetadata(): array
    {
        return [
            'model' => config('embedding.model'),
            'vector_dimension' => (int) config('embedding.vector_dimension', 768),
            'chunk_tokens' => (int) config('embedding.chunk_tokens', 150),
            'chunk_overlap_tokens' => (int) config('embedding.chunk_overlap_tokens', 80),
        ];
    }

    /**
     * Get mappable fields for a document (for CSV/XML).
     */
    public function getMappableFields(Document $document): array
    {
        $relativePath = "documents/{$document->filename}";

        if (!Storage::exists($relativePath)) {
            return [];
        }

        $filePath = Storage::path($relativePath);

        try {
            $parser = $this->parserManager->forMime($document->mime_type);
            return $parser->getMappableFields($filePath);
        } catch (\Throwable) {
            return [];
        }
    }

    /**
     * Check if document requires mapping before processing.
     */
    public function requiresMapping(Document $document): bool
    {
        try {
            $parser = $this->parserManager->forMime($document->mime_type);
            return $parser->requiresMapping();
        } catch (\Throwable) {
            return false;
        }
    }
}
