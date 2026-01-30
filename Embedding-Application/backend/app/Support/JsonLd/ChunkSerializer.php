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

        return [
            '@type' => 'TextDigitalDocument',
            '@id' => "chunk:{$chunk->chunk_id}",
            'identifier' => $chunk->content_hash,
            'text' => $chunk->text,
            'position' => $chunk->chunk_index,
            'wordCount' => str_word_count($chunk->text),
            'isPartOf' => $section ? [
                '@id' => "sec:{$document->doc_id}#{$section->slug}",
            ] : [
                '@id' => "doc:{$document->doc_id}",
            ],
            'inDocument' => [
                '@id' => "doc:{$document->doc_id}",
            ],
        ];
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
}
