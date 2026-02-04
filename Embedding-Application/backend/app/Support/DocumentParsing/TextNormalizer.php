<?php

namespace App\Support\DocumentParsing;

/**
 * Trait for normalizing text extracted from documents.
 * Removes excessive whitespace, control characters, and other pollution
 * that can negatively impact embedding quality.
 */
trait TextNormalizer
{
    /**
     * Clean and normalize extracted text for embedding.
     */
    protected function normalizeText(string $text): string
    {
        // Remove invisible/control characters (except newline, tab, carriage return)
        $text = preg_replace('/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/u', '', $text);

        // Normalize Unicode whitespace characters to regular spaces
        $text = preg_replace('/[\x{00A0}\x{2000}-\x{200B}\x{202F}\x{205F}\x{3000}]/u', ' ', $text);

        // Remove zero-width characters
        $text = preg_replace('/[\x{200C}\x{200D}\x{FEFF}]/u', '', $text);

        // Replace Windows line endings with Unix
        $text = str_replace("\r\n", "\n", $text);
        $text = str_replace("\r", "\n", $text);

        // Replace multiple newlines (3+) with double newline
        $text = preg_replace('/\n{3,}/', "\n\n", $text);

        // Replace multiple spaces/tabs with single space
        $text = preg_replace('/[ \t]+/', ' ', $text);

        // Trim each line
        $lines = explode("\n", $text);
        $lines = array_map('trim', $lines);
        $text = implode("\n", $lines);

        // Remove empty lines at start/end
        return trim($text);
    }
}
