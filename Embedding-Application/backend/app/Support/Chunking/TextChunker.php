<?php

namespace App\Support\Chunking;

class TextChunker
{
    public function chunk(
        string $text,
        int $targetTokens = 700,
        int $overlapTokens = 150
    ): array {
        $words = preg_split('/\s+/', trim($text));

        if (! $words) {
            return [];
        }

        $chunks = [];
        $start = 0;
        $totalWords = count($words);

        while ($start < $totalWords) {
            $end = min($start + $targetTokens, $totalWords);
            $chunkWords = array_slice($words, $start, $end - $start);
            $chunks[] = trim(implode(' ', $chunkWords));

            $start += $targetTokens - $overlapTokens;
            if ($start < 0 || $start >= $totalWords) {
                break;
            }
        }

        return $chunks;
    }
}
