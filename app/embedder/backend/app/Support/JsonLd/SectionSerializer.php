<?php

namespace App\Support\JsonLd;

use App\Models\DocumentSection;

class SectionSerializer
{
    public function __construct(
        private readonly ChunkSerializer $chunkSerializer
    ) {}

    /**
     * Serialize a section to JSON-LD format.
     */
    public function serialize(DocumentSection $section, bool $includeChunks = false): array
    {
        $document = $section->document;

        $jsonLd = [
            '@type' => 'Chapter',
            '@id' => "sec:{$document->doc_id}#{$section->slug}",
            'name' => $section->title,
            'position' => $section->order_index,
            'text' => $section->text,
            'wordCount' => $section->wordCount(),
            'isPartOf' => [
                '@id' => "doc:{$document->doc_id}",
            ],
        ];

        if ($includeChunks) {
            $chunks = $section->chunks()->orderBy('chunk_index')->get();
            if ($chunks->isNotEmpty()) {
                $jsonLd['hasPart'] = $this->chunkSerializer->serializeMany($chunks);
            }
        }

        if ($section->metadata) {
            $jsonLd['additionalProperty'] = $this->serializeMetadata($section->metadata);
        }

        return $jsonLd;
    }

    /**
     * Serialize metadata as PropertyValue array.
     */
    private function serializeMetadata(array $metadata): array
    {
        $properties = [];
        foreach ($metadata as $key => $value) {
            if (is_scalar($value)) {
                $properties[] = [
                    '@type' => 'PropertyValue',
                    'name' => $key,
                    'value' => $value,
                ];
            }
        }
        return $properties;
    }

    /**
     * Serialize multiple sections.
     */
    public function serializeMany(iterable $sections, bool $includeChunks = false): array
    {
        $result = [];
        foreach ($sections as $section) {
            $result[] = $this->serialize($section, $includeChunks);
        }
        return $result;
    }
}
