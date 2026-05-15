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
     * Build one section from all pages, recording per-page char ranges into the
     * concatenated text so chunks can later be mapped back to source pages.
     *
     * @param array $pages
     */
    private function extractSections(array $pages, string $docId): array
    {
        $separator = "\n\n";
        $separatorLen = strlen($separator);
        $combined = '';
        $pageRanges = [];

        foreach ($pages as $index => $page) {
            $pageNumber = $index + 1;
            $pageText = $this->normalizeText($page->getText() ?? '');
            if ($pageText === '') {
                continue;
            }

            $start = strlen($combined);
            $combined .= $pageText;
            $end = strlen($combined);

            $pageRanges[] = [
                'page' => $pageNumber,
                'start' => $start,
                'end' => $end,
            ];

            $combined .= $separator;
        }

        // Trim trailing separator and adjust last range end if needed.
        if (str_ends_with($combined, $separator)) {
            $combined = substr($combined, 0, -$separatorLen);
        }

        return [
            [
                'title' => 'Inhoud',
                'slug' => 'inhoud',
                'order_index' => 0,
                'text' => $combined,
                'metadata' => [
                    'start_page' => 1,
                    'end_page' => count($pages),
                    'page_ranges' => $pageRanges,
                ],
            ],
        ];
    }
}
