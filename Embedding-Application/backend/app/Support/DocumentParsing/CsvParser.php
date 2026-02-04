<?php

namespace App\Support\DocumentParsing;

use Illuminate\Support\Str;
use RuntimeException;

class CsvParser implements DocumentParserInterface
{
    use TextNormalizer;

    public function supports(string $mimeType): bool
    {
        return in_array($mimeType, [
            'text/csv',
            'application/csv',
            'application/vnd.ms-excel',
        ]);
    }

    public function parse(string $path, array $options = []): ParsedDocument
    {
        $handle = fopen($path, 'r');
        if (!$handle) {
            throw new RuntimeException("Kan bestand niet openen: {$path}");
        }

        $delimiter = $options['delimiter'] ?? $this->detectDelimiter($path);
        $hasHeader = $options['has_header'] ?? true;
        $mapping = $options['mapping'] ?? null;

        $headers = [];
        $rows = [];
        $lineNumber = 0;

        while (($data = fgetcsv($handle, 0, $delimiter)) !== false) {
            $lineNumber++;

            if ($lineNumber === 1 && $hasHeader) {
                $headers = $data;
                continue;
            }

            $rows[] = $hasHeader ? array_combine($headers, $data) : $data;
        }

        fclose($handle);

        $docId = $options['doc_id'] ?? Str::slug(pathinfo($path, PATHINFO_FILENAME));
        $title = $options['title'] ?? pathinfo($path, PATHINFO_FILENAME);

        // Convert rows to sections based on mapping
        $sections = $this->rowsToSections($rows, $headers, $mapping, $docId);

        $metadata = [
            'row_count' => count($rows),
            'column_count' => count($headers),
            'columns' => $headers,
            'delimiter' => $delimiter,
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
        $handle = fopen($path, 'r');
        if (!$handle) {
            return [];
        }

        $delimiter = $this->detectDelimiter($path);
        $headers = fgetcsv($handle, 0, $delimiter);
        fclose($handle);

        if (!$headers) {
            return [];
        }

        $fields = [];
        foreach ($headers as $index => $header) {
            $key = Str::slug($header) ?: "column_{$index}";
            $fields[$key] = $header;
        }

        return $fields;
    }

    public function requiresMapping(): bool
    {
        return true;
    }

    /**
     * Detect the CSV delimiter.
     */
    private function detectDelimiter(string $path): string
    {
        $handle = fopen($path, 'r');
        $line = fgets($handle);
        fclose($handle);

        if (!$line) {
            return ',';
        }

        $delimiters = [
            ',' => substr_count($line, ','),
            ';' => substr_count($line, ';'),
            "\t" => substr_count($line, "\t"),
            '|' => substr_count($line, '|'),
        ];

        return array_search(max($delimiters), $delimiters);
    }

    /**
     * Convert CSV rows to document sections.
     */
    private function rowsToSections(array $rows, array $headers, ?array $mapping, string $docId): array
    {
        // If no mapping provided, create one section with all data as text
        if (!$mapping) {
            $text = $this->rowsToText($rows, $headers);
            return [
                [
                    'title' => 'Data',
                    'slug' => 'data',
                    'order_index' => 0,
                    'text' => $this->normalizeText($text),
                    'metadata' => ['row_count' => count($rows)],
                ],
            ];
        }

        $sections = [];
        $titleColumn = $mapping['title_column'] ?? null;
        $contentColumn = $mapping['content_column'] ?? null;
        $groupColumn = $mapping['group_column'] ?? null;

        // Group by column if specified
        if ($groupColumn && isset($rows[0][$groupColumn])) {
            $grouped = [];
            foreach ($rows as $row) {
                $group = $row[$groupColumn] ?? 'Overig';
                $grouped[$group][] = $row;
            }

            $index = 0;
            foreach ($grouped as $groupName => $groupRows) {
                $text = '';
                foreach ($groupRows as $row) {
                    if ($titleColumn && isset($row[$titleColumn])) {
                        $text .= "### {$row[$titleColumn]}\n";
                    }
                    if ($contentColumn && isset($row[$contentColumn])) {
                        $text .= $row[$contentColumn] . "\n\n";
                    } else {
                        $text .= $this->rowToText($row, $headers) . "\n\n";
                    }
                }

                $sections[] = [
                    'title' => $groupName,
                    'slug' => Str::slug($groupName) ?: "groep-{$index}",
                    'order_index' => $index++,
                    'text' => $this->normalizeText($text),
                    'metadata' => ['row_count' => count($groupRows)],
                ];
            }
        } else {
            // Create one section per row if title column is specified
            if ($titleColumn) {
                foreach ($rows as $index => $row) {
                    $rowTitle = $row[$titleColumn] ?? "Rij " . ($index + 1);
                    $content = $contentColumn && isset($row[$contentColumn])
                        ? $row[$contentColumn]
                        : $this->rowToText($row, $headers);

                    $sections[] = [
                        'title' => $rowTitle,
                        'slug' => Str::slug($rowTitle) ?: "rij-{$index}",
                        'order_index' => $index,
                        'text' => $this->normalizeText($content),
                        'metadata' => ['row_data' => $row],
                    ];
                }
            } else {
                // Single section with all data
                $text = $this->rowsToText($rows, $headers);
                $sections[] = [
                    'title' => 'Data',
                    'slug' => 'data',
                    'order_index' => 0,
                    'text' => $this->normalizeText($text),
                    'metadata' => ['row_count' => count($rows)],
                ];
            }
        }

        return $sections;
    }

    /**
     * Convert all rows to readable text.
     */
    private function rowsToText(array $rows, array $headers): string
    {
        $text = '';
        foreach ($rows as $index => $row) {
            $text .= "--- Rij " . ($index + 1) . " ---\n";
            $text .= $this->rowToText($row, $headers) . "\n\n";
        }
        return trim($text);
    }

    /**
     * Convert a single row to readable text.
     */
    private function rowToText(array $row, array $headers): string
    {
        $lines = [];
        foreach ($row as $key => $value) {
            if (!empty($value)) {
                $label = is_numeric($key) && isset($headers[$key]) ? $headers[$key] : $key;
                $lines[] = "{$label}: {$value}";
            }
        }
        return implode("\n", $lines);
    }
}
