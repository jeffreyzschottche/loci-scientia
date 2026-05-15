<?php

namespace App\Support\Chunking;

class ChunkIdGenerator
{
    /**
     * Generate a unique chunk ID.
     */
    public function generate(string $docId, string $sectionSlug, int $chunkIndex): string
    {
        return sprintf('%s#%s#%04d', $docId, $sectionSlug, $chunkIndex);
    }

    /**
     * Alias for generate() - backwards compatibility.
     */
    public function make(string $docId, string $sectionSlug, int $chunkIndex): string
    {
        return $this->generate($docId, $sectionSlug, $chunkIndex);
    }

    /**
     * Parse a chunk ID back to its components.
     */
    public function parse(string $chunkId): ?array
    {
        if (preg_match('/^(.+)#(.+)#(\d{4})$/', $chunkId, $matches)) {
            return [
                'doc_id' => $matches[1],
                'section_slug' => $matches[2],
                'chunk_index' => (int) $matches[3],
            ];
        }
        return null;
    }
}
