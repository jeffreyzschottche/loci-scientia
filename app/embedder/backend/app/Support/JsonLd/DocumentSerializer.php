<?php

namespace App\Support\JsonLd;

use App\Models\Document;

class DocumentSerializer
{
    public function __construct(
        private readonly SectionSerializer $sectionSerializer,
        private readonly ChunkSerializer $chunkSerializer
    ) {}

    /**
     * Serialize a document to JSON-LD format.
     */
    public function serialize(Document $document, bool $includeSections = true, bool $includeChunks = false): array
    {
        $jsonLd = [
            '@context' => 'https://schema.org',
            '@type' => 'Article',
            '@id' => "doc:{$document->doc_id}",
            'identifier' => $document->doc_id,
            'name' => $document->title,
            'dateCreated' => $document->created_at->toIso8601String(),
            'dateModified' => $document->updated_at->toIso8601String(),
        ];

        if ($document->original_filename) {
            $jsonLd['originalFilename'] = $document->original_filename;
        }

        if ($document->description) {
            $jsonLd['description'] = $document->description;
        }

        if ($document->category) {
            $jsonLd['articleSection'] = $document->category;
        }

        if ($document->version_tag) {
            $jsonLd['version'] = $document->version_tag;
        }

        if ($document->content_date) {
            $jsonLd['datePublished'] = $document->content_date->toDateString();
        }

        if ($document->source_url) {
            $jsonLd['url'] = $document->source_url;
        }

        if ($document->language) {
            $jsonLd['inLanguage'] = $document->language;
        }

        if ($includeSections) {
            $sections = $document->sections()->orderBy('order_index')->get();
            if ($sections->isNotEmpty()) {
                $jsonLd['hasPart'] = $this->sectionSerializer->serializeMany($sections, $includeChunks);
            }
        }

        if ($document->priority > 0) {
            $jsonLd['position'] = $document->priority;
            $additionalProperties = $jsonLd['additionalProperty'] ?? [];
            $additionalProperties[] = [
                '@type' => 'PropertyValue',
                'name' => 'embeddingPriority',
                'value' => $document->priority,
            ];
            $jsonLd['additionalProperty'] = $additionalProperties;
        }

        if ($document->metadata) {
            $metadataProps = $this->serializeMetadata($document->metadata);
            $jsonLd['additionalProperty'] = array_merge(
                $jsonLd['additionalProperty'] ?? [],
                $metadataProps
            );
        }

        return $jsonLd;
    }

    /**
     * Serialize document hierarchy (tree structure).
     */
    public function serializeTree(Document $document): array
    {
        $jsonLd = [
            '@type' => 'Article',
            '@id' => "doc:{$document->doc_id}",
            'name' => $document->title,
            'position' => $document->position,
        ];

        if ($document->category) {
            $jsonLd['articleSection'] = $document->category;
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

}
