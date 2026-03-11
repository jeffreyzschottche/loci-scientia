<?php

namespace App\Support\Chunking;

class ChunkHasher
{
    /**
     * Generate a content hash for a chunk.
     * Only hashes the text content for deduplication purposes.
     */
    public function hash(string $text): string
    {
        return 'sha256:' . hash('sha256', trim($text));
    }

    /**
     * Generate a hash including context (title, section).
     */
    public function hashWithContext(string $title, string $section, string $text): string
    {
        return 'sha256:' . hash('sha256', $title . '|' . $section . '|' . $text);
    }

    /**
     * Compare two hashes.
     */
    public function compare(string $hash1, string $hash2): bool
    {
        return hash_equals($hash1, $hash2);
    }
}
