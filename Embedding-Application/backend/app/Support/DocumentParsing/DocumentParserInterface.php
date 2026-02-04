<?php

namespace App\Support\DocumentParsing;

interface DocumentParserInterface
{
    /**
     * Check if this parser supports the given MIME type.
     */
    public function supports(string $mimeType): bool;

    /**
     * Parse the document at the given path.
     *
     * @param string $path Path to the file
     * @param array $options Parser options (e.g., column mapping for CSV)
     */
    public function parse(string $path, array $options = []): ParsedDocument;

    /**
     * Get fields that can be mapped (for CSV/XML).
     * Returns empty array if mapping is not applicable.
     *
     * @param string $path Path to file for inspection
     * @return array<string, string> Field key => human label
     */
    public function getMappableFields(string $path): array;

    /**
     * Check if this parser requires field mapping before parsing.
     */
    public function requiresMapping(): bool;
}
