<?php

namespace App\Support\DocumentParsing;

use Illuminate\Support\Str;
use Smalot\PdfParser\Parser as PdfTextParser;

class PdfParser implements DocumentParserInterface
{
    use TextNormalizer;

    public function __construct(
        private readonly PdfTextParser $parser
    ) {}

    public function supports(string $mimeType): bool
    {
        return $mimeType === 'application/pdf';
    }

    public function parse(string $path, array $options = []): ParsedDocument
    {
        $pdf = $this->parser->parseFile($path);
        $details = $pdf->getDetails();
        $pages = $pdf->getPages();

        $docId = $options['doc_id'] ?? Str::slug(pathinfo($path, PATHINFO_FILENAME));
        $title = $options['title'] ?? $details['Title'] ?? pathinfo($path, PATHINFO_FILENAME);

        // Try to detect chapters/sections from the text structure
        $sections = $this->extractSections($pages, $docId);

        $metadata = [
            'page_count' => count($pages),
            'author' => $details['Author'] ?? null,
            'creator' => $details['Creator'] ?? null,
            'creation_date' => $details['CreationDate'] ?? null,
            'modification_date' => $details['ModDate'] ?? null,
        ];

        return new ParsedDocument(
            docId: $docId,
            title: $title,
            sections: $sections,
            metadata: array_filter($metadata),
            description: $options['description'] ?? null,
            category: $options['category'] ?? null,
        );
    }

    public function getMappableFields(string $path): array
    {
        return [];
    }

    public function requiresMapping(): bool
    {
        return false;
    }

    /**
     * Extract sections from PDF pages.
     * Basic implementation - creates one section per page or combines into body.
     */
    private function extractSections(array $pages, string $docId): array
    {
        // For now, combine all pages into a single body section
        // Future: detect headers/chapters using font size analysis
        $fullText = '';
        foreach ($pages as $page) {
            $fullText .= $page->getText() . "\n\n";
        }

        $fullText = $this->normalizeText($fullText);

        return [
            [
                'title' => 'Inhoud',
                'slug' => 'inhoud',
                'order_index' => 0,
                'text' => $fullText,
                'metadata' => [
                    'start_page' => 1,
                    'end_page' => count($pages),
                ],
            ],
        ];
    }

    // Image extraction intentionally removed; parser focuses on text only.
}
