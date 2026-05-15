<?php

namespace App\Support\Chunking;

class TextChunker
{
    /**
     * Chunk text by word, returning per-chunk char offsets into the input string
     * so callers can map chunks back to source-position metadata (e.g. PDF pages).
     *
     * @return array<int, array{text: string, token_count: int, word_count: int, char_start: int, char_end: int}>
     */
    public function chunk(
        string $text,
        ?int $targetTokens = null,
        ?int $overlapTokens = null
    ): array {
        $targetTokens ??= config('embedding.chunk_tokens', 150);
        $overlapTokens ??= config('embedding.chunk_overlap_tokens', 80);
        $tokensPerWord = max(0.1, (float) config('embedding.tokens_per_word', 1.3));

        if (! preg_match_all('/\S+/u', $text, $matches, PREG_OFFSET_CAPTURE)) {
            return [];
        }

        $words = $matches[0];
        $totalWords = count($words);
        if ($totalWords === 0) {
            return [];
        }

        $targetWords = max(1, (int) floor($targetTokens / $tokensPerWord));
        $overlapWords = max(0, (int) floor($overlapTokens / $tokensPerWord));

        $chunks = [];
        $start = 0;

        while ($start < $totalWords) {
            $end = min($totalWords, $start + $targetWords);
            $slice = array_slice($words, $start, $end - $start);

            $firstWord = $slice[0];
            $lastWord = $slice[count($slice) - 1];
            $charStart = (int) $firstWord[1];
            $charEnd = (int) $lastWord[1] + strlen($lastWord[0]);

            $chunkText = trim(implode(' ', array_map(static fn ($w) => $w[0], $slice)));
            if ($chunkText === '') {
                break;
            }

            $wordCount = count($slice);
            $tokenEstimate = $this->estimateTokenCount($chunkText);

            $chunks[] = [
                'text' => $chunkText,
                'token_count' => min($tokenEstimate, $targetTokens),
                'word_count' => $wordCount,
                'char_start' => $charStart,
                'char_end' => $charEnd,
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
