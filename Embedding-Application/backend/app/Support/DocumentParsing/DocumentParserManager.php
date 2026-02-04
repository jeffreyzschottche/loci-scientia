<?php

namespace App\Support\DocumentParsing;

use Illuminate\Support\Collection;
use RuntimeException;

class DocumentParserManager
{
    public function __construct(
        /** @var Collection<int, DocumentParserInterface> */
        private readonly Collection $parsers
    ) {}

    public function forMime(string $mimeType): DocumentParserInterface
    {
        $parser = $this->parsers->first(fn (DocumentParserInterface $parser) => $parser->supports($mimeType));

        if (! $parser) {
            throw new RuntimeException("Geen parser voor mime type {$mimeType}");
        }

        return $parser;
    }
}
