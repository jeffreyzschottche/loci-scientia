<?php

namespace App\Support\DocumentParsing;

use Illuminate\Support\Str;

class TextParser implements DocumentParserInterface
{
    use TextNormalizer;

    public function supports(string $mimeType): bool
    {
        return in_array($mimeType, ['text/plain', 'text/markdown']);
    }

    public function parse(string $path, array $options = []): ParsedDocument
    {
        $text = file_get_contents($path) ?: '';
        $isMarkdown = str_ends_with(strtolower($path), '.md');

        $docId = $options['doc_id'] ?? Str::slug(pathinfo($path, PATHINFO_FILENAME));
        $title = $options['title'] ?? pathinfo($path, PATHINFO_FILENAME);

        // Try to extract sections from markdown headers
        $sections = $isMarkdown
            ? $this->parseMarkdownSections($text, $docId)
            : $this->parseTextSections($text, $docId);

        $metadata = [
            'line_count' => substr_count($text, "\n") + 1,
            'format' => $isMarkdown ? 'markdown' : 'plain',
        ];

        return new ParsedDocument(
            docId: $docId,
            title: $title,
            sections: $sections,
            metadata: $metadata,
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
     * Parse markdown into sections based on headers.
     */
    private function parseMarkdownSections(string $text, string $docId): array
    {
        $sections = [];
        $lines = explode("\n", $text);
        $currentSection = null;
        $currentContent = '';
        $sectionIndex = 0;

        foreach ($lines as $line) {
            // Check for markdown headers (# ## ### etc.)
            if (preg_match('/^(#{1,6})\s+(.+)$/', $line, $matches)) {
                // Save previous section
                if ($currentSection !== null && trim($currentContent)) {
                    $sections[] = [
                        'title' => $currentSection['title'],
                        'slug' => $currentSection['slug'],
                        'order_index' => $sectionIndex++,
                        'text' => $this->normalizeText($currentContent),
                        'metadata' => ['level' => $currentSection['level']],
                    ];
                }

                // Start new section
                $level = strlen($matches[1]);
                $sectionTitle = trim($matches[2]);
                $currentSection = [
                    'title' => $sectionTitle,
                    'slug' => Str::slug($sectionTitle) ?: "sectie-{$sectionIndex}",
                    'level' => $level,
                ];
                $currentContent = '';
            } else {
                $currentContent .= $line . "\n";
            }
        }

        // Add remaining content
        if (trim($currentContent)) {
            if ($currentSection === null) {
                $currentSection = [
                    'title' => 'Inhoud',
                    'slug' => 'inhoud',
                    'level' => 0,
                ];
            }

            $sections[] = [
                'title' => $currentSection['title'],
                'slug' => $currentSection['slug'],
                'order_index' => $sectionIndex,
                'text' => $this->normalizeText($currentContent),
                'metadata' => ['level' => $currentSection['level']],
            ];
        }

        // If no sections found, create one body section
        if (empty($sections)) {
            $sections[] = [
                'title' => 'Inhoud',
                'slug' => 'inhoud',
                'order_index' => 0,
                'text' => $this->normalizeText($text),
                'metadata' => [],
            ];
        }

        return $sections;
    }

    /**
     * Parse plain text into sections (single body section).
     */
    private function parseTextSections(string $text, string $docId): array
    {
        return [
            [
                'title' => 'Inhoud',
                'slug' => 'inhoud',
                'order_index' => 0,
                'text' => $this->normalizeText($text),
                'metadata' => [],
            ],
        ];
    }
}
