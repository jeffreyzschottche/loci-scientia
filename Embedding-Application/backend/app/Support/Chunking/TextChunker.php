<?php

namespace App\Support\Chunking;

class TextChunker
{
    /**
     * Chunk text based on the configured target token counts for the embedding model.
     *
     * @return array<int, array{text: string, token_count: int, word_count: int}>
     */
    public function chunk(
        string $text,
        ?int $targetTokens = null,
        ?int $overlapTokens = null
    ): array {
        $targetTokens ??= config('embedding.chunk_tokens', 448);
        $overlapTokens ??= config('embedding.chunk_overlap_tokens', 96);
        $tokensPerWord = max(0.1, (float) config('embedding.tokens_per_word', 1.3));

        $words = preg_split('/\s+/u', trim($text));

        if (! $words) {
            return [];
        }

        $targetWords = max(1, (int) floor($targetTokens / $tokensPerWord));
        $overlapWords = max(0, (int) floor($overlapTokens / $tokensPerWord));

        $chunks = [];
        $start = 0;
        $totalWords = count($words);

        while ($start < $totalWords) {
            $end = min($totalWords, $start + $targetWords);
            $chunkWords = array_slice($words, $start, $end - $start);
            $chunkText = trim(implode(' ', $chunkWords));

            if ($chunkText === '') {
                break;
            }

            $wordCount = max(1, str_word_count($chunkText));
            $tokenEstimate = $this->estimateTokenCount($chunkText);

            $chunks[] = [
                'text' => $chunkText,
                'token_count' => min($tokenEstimate, $targetTokens),
                'word_count' => $wordCount,
            ];

            if ($end >= $totalWords) {
                break;
            }

            $start = max(($end - $overlapWords), 0);
            if ($start >= $totalWords) {
                break;
            }
        }

        return $chunks;
    }

    public function estimateTokenCount(string $text): int
    {
        $words = max(1, str_word_count($text));
        $tokensPerWord = max(0.1, (float) config('embedding.tokens_per_word', 1.3));

        return (int) ceil($words * $tokensPerWord);
    }
}
