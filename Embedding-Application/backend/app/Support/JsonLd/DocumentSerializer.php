<?php

namespace App\Support\JsonLd;

use App\Models\Document;
use App\Models\DocumentRelation;

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

        // Add optional fields
        if ($document->description) {
            $jsonLd['description'] = $document->description;
        }

        if ($document->category) {
            $jsonLd['articleSection'] = $document->category;
        }

        if ($document->version_tag) {
            $jsonLd['version'] = $document->version_tag;
        }

        if ($document->source_url) {
            $jsonLd['url'] = $document->source_url;
        }

        // Add hierarchy info
        if ($document->parent_id) {
            $jsonLd['isPartOf'] = [
                '@id' => "doc:{$document->parent->doc_id}",
            ];
        }

        // Add children if any
        $children = $document->children;
        if ($children->isNotEmpty()) {
            $jsonLd['hasPart'] = $children->map(fn ($child) => [
                '@type' => 'Article',
                '@id' => "doc:{$child->doc_id}",
                'name' => $child->title,
            ])->all();
        }

        // Add sections
        if ($includeSections) {
            $sections = $document->sections()->orderBy('order_index')->get();
            if ($sections->isNotEmpty()) {
                // Replace hasPart with sections if no children
                if ($children->isEmpty()) {
                    $jsonLd['hasPart'] = $this->sectionSerializer->serializeMany($sections, $includeChunks);
                } else {
                    $jsonLd['mainEntity'] = $this->sectionSerializer->serializeMany($sections, $includeChunks);
                }
            }
        }

        // Add priority
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

        // Add document-level relations
        $document->loadMissing('outgoingRelations.targetDocument');
        $relations = $this->serializeDocumentRelations($document);
        if (!empty($relations)) {
            $jsonLd['relatedLink'] = $relations;
        }

        // Add metadata
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
     * Serialize document-level relations as LinkRole objects.
     */
    private function serializeDocumentRelations(Document $document): array
    {
        $relations = [];

        foreach ($document->outgoingRelations as $relation) {
            $targetDoc = $relation->targetDocument;
            if (!$targetDoc) {
                continue;
            }

            $relations[] = [
                '@type' => 'LinkRole',
                '@id' => "doc:{$targetDoc->doc_id}",
                'linkRelationship' => $relation->relation_type,
                'name' => $targetDoc->title,
                'description' => DocumentRelation::labelFor($relation->relation_type),
            ];
        }

        return $relations;
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

        $children = $document->children;
        if ($children->isNotEmpty()) {
            $jsonLd['hasPart'] = $children->map(fn ($child) => $this->serializeTree($child))->all();
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
