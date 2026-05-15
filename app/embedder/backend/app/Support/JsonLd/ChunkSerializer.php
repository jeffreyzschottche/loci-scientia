<?php

namespace App\Support\JsonLd;

use App\Models\DocumentChunk;

class ChunkSerializer
{
    /**
     * Serialize a chunk to JSON-LD format.
     */
    public function serialize(DocumentChunk $chunk): array
    {
        $section = $chunk->section;
        $document = $chunk->document;
        $wordCount = $chunk->metadata['word_count'] ?? str_word_count($chunk->text);
        $contentDate = $document->content_date?->toDateString();
        $embeddingMeta = $this->embeddingMetadata();
        $pages = $chunk->metadata['pages'] ?? null;

        $payload = [
            '@type' => 'TextDigitalDocument',
            '@id' => "chunk:{$chunk->chunk_id}",
            'identifier' => $chunk->content_hash,
            'text' => $chunk->text,
            'position' => $chunk->chunk_index,
            'wordCount' => $wordCount,
            'tokenCount' => $chunk->token_count,
            'contentDate' => $contentDate,
            'embedding' => $embeddingMeta,
            'isPartOf' => $section ? [
                '@id' => "sec:{$document->doc_id}#{$section->slug}",
            ] : [
                '@id' => "doc:{$document->doc_id}",
            ],
            'inDocument' => [
                '@id' => "doc:{$document->doc_id}",
            ],
        ];

        if (is_array($pages) && ! empty($pages)) {
            $payload['pages'] = array_values(array_map('intval', $pages));
        }

        return $payload;
    }

    /**
     * Serialize multiple chunks.
     */
    public function serializeMany(iterable $chunks): array
    {
        $result = [];
        foreach ($chunks as $chunk) {
            $result[] = $this->serialize($chunk);
        }
        return $result;
    }

    private function embeddingMetadata(): array
    {
        return [
            'model' => config('embedding.model'),
            'vectorDimension' => (int) config('embedding.vector_dimension', 768),
        ];
    }
}
