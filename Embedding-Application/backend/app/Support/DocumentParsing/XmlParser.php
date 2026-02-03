<?php

namespace App\Support\DocumentParsing;

use Illuminate\Support\Str;
use RuntimeException;
use SimpleXMLElement;

class XmlParser implements DocumentParserInterface
{
    use TextNormalizer;

    public function supports(string $mimeType): bool
    {
        return in_array($mimeType, [
            'text/xml',
            'application/xml',
            'application/xhtml+xml',
        ]);
    }

    public function parse(string $path, array $options = []): ParsedDocument
    {
        $content = file_get_contents($path);
        if ($content === false) {
            throw new RuntimeException("Kan bestand niet lezen: {$path}");
        }

        libxml_use_internal_errors(true);
        $xml = simplexml_load_string($content);

        if ($xml === false) {
            $errors = libxml_get_errors();
            libxml_clear_errors();
            throw new RuntimeException("Ongeldige XML: " . ($errors[0]->message ?? 'Onbekende fout'));
        }

        $docId = $options['doc_id'] ?? Str::slug(pathinfo($path, PATHINFO_FILENAME));
        $title = $options['title'] ?? $this->extractTitle($xml) ?? pathinfo($path, PATHINFO_FILENAME);
        $mapping = $options['mapping'] ?? null;

        $sections = $this->xmlToSections($xml, $mapping, $docId);

        $metadata = [
            'root_element' => $xml->getName(),
            'namespaces' => $xml->getNamespaces(true),
            'child_count' => count($xml->children()),
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
        $content = file_get_contents($path);
        if ($content === false) {
            return [];
        }

        libxml_use_internal_errors(true);
        $xml = simplexml_load_string($content);
        libxml_clear_errors();

        if ($xml === false) {
            return [];
        }

        return $this->extractXPaths($xml);
    }

    public function requiresMapping(): bool
    {
        return true;
    }

    /**
     * Extract title from XML.
     */
    private function extractTitle(SimpleXMLElement $xml): ?string
    {
        // Try common title elements
        $titlePaths = ['title', 'name', 'heading', 'header', 'Title', 'Name'];

        foreach ($titlePaths as $path) {
            if (isset($xml->$path) && (string) $xml->$path) {
                return (string) $xml->$path;
            }
        }

        // Try attributes
        foreach (['title', 'name', 'id'] as $attr) {
            if (isset($xml[$attr]) && (string) $xml[$attr]) {
                return (string) $xml[$attr];
            }
        }

        return null;
    }

    /**
     * Convert XML to document sections.
     */
    private function xmlToSections(SimpleXMLElement $xml, ?array $mapping, string $docId): array
    {
        if ($mapping && isset($mapping['section_xpath'])) {
            return $this->mappedXmlToSections($xml, $mapping, $docId);
        }

        // Auto-detect structure
        return $this->autoDetectSections($xml, $docId);
    }

    /**
     * Parse XML using provided mapping.
     */
    private function mappedXmlToSections(SimpleXMLElement $xml, array $mapping, string $docId): array
    {
        $sections = [];
        $sectionXPath = $mapping['section_xpath'];
        $titleXPath = $mapping['title_xpath'] ?? null;
        $contentXPath = $mapping['content_xpath'] ?? null;

        $elements = $xml->xpath($sectionXPath);

        $index = 0;
        foreach ($elements as $element) {
            $sectionTitle = 'Sectie ' . ($index + 1);
            if ($titleXPath) {
                $titleResult = $element->xpath($titleXPath);
                if ($titleResult) {
                    $sectionTitle = (string) $titleResult[0];
                }
            }

            $content = '';
            if ($contentXPath) {
                $contentResult = $element->xpath($contentXPath);
                if ($contentResult) {
                    $content = (string) $contentResult[0];
                }
            } else {
                $content = $this->elementToText($element);
            }

            $sections[] = [
                'title' => $sectionTitle,
                'slug' => Str::slug($sectionTitle) ?: "sectie-{$index}",
                'order_index' => $index,
                'text' => $this->normalizeText($content),
                'metadata' => ['xpath' => $sectionXPath . '[' . ($index + 1) . ']'],
            ];
            $index++;
        }

        // If no sections found, create one with all content
        if (empty($sections)) {
            $sections[] = [
                'title' => 'Inhoud',
                'slug' => 'inhoud',
                'order_index' => 0,
                'text' => $this->normalizeText($this->elementToText($xml)),
                'metadata' => [],
            ];
        }

        return $sections;
    }

    /**
     * Auto-detect sections from XML structure.
     */
    private function autoDetectSections(SimpleXMLElement $xml, string $docId): array
    {
        $sections = [];
        $children = $xml->children();

        // If root has repeating children of same type, treat each as a section
        $childNames = [];
        foreach ($children as $child) {
            $childNames[] = $child->getName();
        }

        $uniqueNames = array_unique($childNames);

        // If most children have the same name, treat each as a section
        if (count($uniqueNames) === 1 && count($children) > 1) {
            $index = 0;
            foreach ($children as $child) {
                $title = $this->extractTitle($child) ?? $child->getName() . ' ' . ($index + 1);
                $sections[] = [
                    'title' => $title,
                    'slug' => Str::slug($title) ?: "{$child->getName()}-{$index}",
                    'order_index' => $index,
                    'text' => $this->normalizeText($this->elementToText($child)),
                    'metadata' => ['element' => $child->getName()],
                ];
                $index++;
            }
        } else {
            // Treat each unique child as a section
            $index = 0;
            foreach ($children as $child) {
                $title = $this->extractTitle($child) ?? ucfirst($child->getName());
                $sections[] = [
                    'title' => $title,
                    'slug' => Str::slug($title) ?: $child->getName(),
                    'order_index' => $index++,
                    'text' => $this->normalizeText($this->elementToText($child)),
                    'metadata' => ['element' => $child->getName()],
                ];
            }
        }

        // If still no sections, create one body
        if (empty($sections)) {
            $sections[] = [
                'title' => 'Inhoud',
                'slug' => 'inhoud',
                'order_index' => 0,
                'text' => $this->normalizeText($this->elementToText($xml)),
                'metadata' => [],
            ];
        }

        return $sections;
    }

    /**
     * Extract XPaths from XML for mapping UI.
     */
    private function extractXPaths(SimpleXMLElement $xml, string $prefix = ''): array
    {
        $paths = [];
        $name = $xml->getName();
        $currentPath = $prefix ? "{$prefix}/{$name}" : "/{$name}";

        // Add this element
        $paths[$currentPath] = $name;

        // Add attributes
        foreach ($xml->attributes() as $attrName => $attrValue) {
            $paths["{$currentPath}/@{$attrName}"] = "{$name}/@{$attrName}";
        }

        // Add children (limited depth to avoid explosion)
        if (substr_count($currentPath, '/') < 5) {
            foreach ($xml->children() as $child) {
                $childPaths = $this->extractXPaths($child, $currentPath);
                $paths = array_merge($paths, $childPaths);
            }
        }

        return $paths;
    }

    /**
     * Convert XML element to text.
     */
    private function elementToText(SimpleXMLElement $element, int $depth = 0): string
    {
        $text = '';

        // Get direct text content
        $directText = trim((string) $element);
        if ($directText) {
            $text .= $directText . "\n";
        }

        // Process children
        foreach ($element->children() as $child) {
            $childName = $child->getName();
            $childText = trim((string) $child);
            $attributes = $child->attributes();

            // Check if this element has meaningful attributes (self-closing tags with data)
            if ($attributes && count($attributes) > 0) {
                $attrParts = [];
                foreach ($attributes as $attrName => $attrValue) {
                    $attrParts[] = "{$attrName}: {$attrValue}";
                }
                $text .= "{$childName}: " . implode(', ', $attrParts) . "\n";
            }

            if ($childText && !$child->count()) {
                // Leaf node with text
                $text .= "{$childName}: {$childText}\n";
            } elseif ($child->count()) {
                // Has children, recurse
                $text .= "\n{$childName}:\n";
                $text .= $this->elementToText($child, $depth + 1);
            }
        }

        return $text;
    }
}
