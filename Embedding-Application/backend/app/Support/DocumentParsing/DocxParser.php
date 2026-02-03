<?php

namespace App\Support\DocumentParsing;

use PhpOffice\PhpWord\IOFactory;
use PhpOffice\PhpWord\Element\TextRun;
use PhpOffice\PhpWord\Element\Text;
use PhpOffice\PhpWord\Element\Title;
use PhpOffice\PhpWord\Element\Table;
use PhpOffice\PhpWord\Element\ListItem;
use Illuminate\Support\Str;

class DocxParser implements DocumentParserInterface
{
    use TextNormalizer;

    public function supports(string $mimeType): bool
    {
        return in_array($mimeType, [
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/msword',
        ]);
    }

    public function parse(string $path, array $options = []): ParsedDocument
    {
        $phpWord = IOFactory::load($path);

        $docId = $options['doc_id'] ?? Str::slug(pathinfo($path, PATHINFO_FILENAME));
        $docInfo = $phpWord->getDocInfo();

        $title = $options['title'] ?? $docInfo->getTitle() ?: pathinfo($path, PATHINFO_FILENAME);

        $sections = $this->extractSections($phpWord, $docId);

        $metadata = [
            'author' => $docInfo->getCreator() ?: null,
            'company' => $docInfo->getCompany() ?: null,
            'description' => $docInfo->getDescription() ?: null,
            'keywords' => $docInfo->getKeywords() ?: null,
            'created' => $docInfo->getCreated() ? date('Y-m-d H:i:s', $docInfo->getCreated()) : null,
            'modified' => $docInfo->getModified() ? date('Y-m-d H:i:s', $docInfo->getModified()) : null,
        ];

        return new ParsedDocument(
            docId: $docId,
            title: $title,
            sections: $sections,
            metadata: array_filter($metadata),
            description: $options['description'] ?? $docInfo->getDescription() ?: null,
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
     * Extract sections from Word document.
     */
    private function extractSections($phpWord, string $docId): array
    {
        $sections = [];
        $currentSection = null;
        $currentText = '';
        $sectionIndex = 0;

        foreach ($phpWord->getSections() as $section) {
            foreach ($section->getElements() as $element) {
                // Check if this is a title/heading
                if ($element instanceof Title) {
                    // Save previous section if exists
                    if ($currentSection !== null && trim($currentText)) {
                        $sections[] = [
                            'title' => $currentSection['title'],
                            'slug' => $currentSection['slug'],
                            'order_index' => $sectionIndex++,
                            'text' => $this->normalizeText($currentText),
                            'metadata' => ['level' => $currentSection['level']],
                        ];
                    }

                    // Start new section
                    $titleText = $this->extractText($element);
                    $currentSection = [
                        'title' => $titleText,
                        'slug' => Str::slug($titleText) ?: 'sectie-' . ($sectionIndex + 1),
                        'level' => $element->getDepth(),
                    ];
                    $currentText = '';
                } else {
                    $currentText .= $this->extractText($element) . "\n";
                }
            }
        }

        // Add remaining content
        if (trim($currentText)) {
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
                'text' => $this->normalizeText($currentText),
                'metadata' => ['level' => $currentSection['level']],
            ];
        }

        // If no sections found, create one body section
        if (empty($sections)) {
            $fullText = '';
            foreach ($phpWord->getSections() as $section) {
                foreach ($section->getElements() as $element) {
                    $fullText .= $this->extractText($element) . "\n";
                }
            }

            $sections[] = [
                'title' => 'Inhoud',
                'slug' => 'inhoud',
                'order_index' => 0,
                'text' => $this->normalizeText($fullText),
                'metadata' => [],
            ];
        }

        return $sections;
    }

    /**
     * Extract text from any Word element.
     */
    private function extractText($element): string
    {
        if ($element instanceof Text) {
            return $element->getText();
        }

        if ($element instanceof TextRun) {
            $text = '';
            foreach ($element->getElements() as $child) {
                $text .= $this->extractText($child);
            }
            return $text;
        }

        if ($element instanceof Title) {
            return $this->extractText($element->getText());
        }

        if ($element instanceof ListItem) {
            return '- ' . $this->extractText($element->getTextObject());
        }

        if ($element instanceof Table) {
            return $this->extractTableText($element);
        }

        if (method_exists($element, 'getText')) {
            $text = $element->getText();
            if (is_string($text)) {
                return $text;
            }
            if (is_object($text)) {
                return $this->extractText($text);
            }
        }

        if (method_exists($element, 'getElements')) {
            $text = '';
            foreach ($element->getElements() as $child) {
                $text .= $this->extractText($child);
            }
            return $text;
        }

        return '';
    }

    /**
     * Extract text from a table.
     */
    private function extractTableText(Table $table): string
    {
        $text = "\n";
        foreach ($table->getRows() as $row) {
            $cells = [];
            foreach ($row->getCells() as $cell) {
                $cellText = '';
                foreach ($cell->getElements() as $element) {
                    $cellText .= $this->extractText($element);
                }
                $cells[] = trim($cellText);
            }
            $text .= implode(' | ', $cells) . "\n";
        }
        return $text . "\n";
    }

    // Image extraction intentionally removed; DOCX parser now focuses solely on text content.
}
