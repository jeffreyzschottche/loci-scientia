<?php

namespace App\Providers;

use App\Support\DocumentParsing\DocumentParserManager;
use App\Support\DocumentParsing\PdfParser;
use App\Support\DocumentParsing\DocxParser;
use App\Support\DocumentParsing\CsvParser;
use App\Support\DocumentParsing\XmlParser;
use App\Support\DocumentParsing\TextParser;
use Illuminate\Support\ServiceProvider;

class DocumentServiceProvider extends ServiceProvider
{
    public function register(): void
    {
        $this->app->singleton(DocumentParserManager::class, function ($app) {
            $parsers = collect([
                $app->make(PdfParser::class),
                $app->make(DocxParser::class),
                $app->make(CsvParser::class),
                $app->make(XmlParser::class),
                $app->make(TextParser::class), // Keep TextParser last as fallback for text/plain
            ]);

            return new DocumentParserManager($parsers);
        });
    }
}
