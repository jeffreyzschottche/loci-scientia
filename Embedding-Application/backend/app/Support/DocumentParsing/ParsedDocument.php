<?php

namespace App\Support\DocumentParsing;

class ParsedDocument
{
    public function __construct(
        public readonly string $docId,
        public readonly string $title,
        public readonly array $sections,
        public readonly array $metadata = [],
        public readonly ?string $description = null,
        public readonly ?string $category = null,
    ) {}

    /**
     * Get total word count across all sections.
     */
    public function wordCount(): int
    {
        $count = 0;
        foreach ($this->sections as $section) {
            $count += str_word_count($section['text'] ?? '');
        }
        return $count;
    }

    /**
     * Get total character count.
     */
    public function characterCount(): int
    {
        $count = 0;
        foreach ($this->sections as $section) {
            $count += mb_strlen($section['text'] ?? '');
        }
        return $count;
    }
}
