<?php

namespace App\Enums;

enum ProcessingStage: string
{
    case UPLOADED = 'uploaded';
    case QUEUED = 'queued';
    case PARSING = 'parsing';
    case CHUNKING = 'chunking';
    case GENERATING_JSONLD = 'generating_jsonld';
    case READY = 'ready';
    case FAILED = 'failed';

    public function label(): string
    {
        return match ($this) {
            self::UPLOADED => 'Geüpload',
            self::QUEUED => 'In wachtrij',
            self::PARSING => 'Tekst extraheren',
            self::CHUNKING => 'Opdelen in chunks',
            self::GENERATING_JSONLD => 'JSON-LD genereren',
            self::READY => 'Klaar',
            self::FAILED => 'Mislukt',
        };
    }

    public function isProcessing(): bool
    {
        return in_array($this, [
            self::QUEUED,
            self::PARSING,
            self::CHUNKING,
            self::GENERATING_JSONLD,
        ]);
    }

    public function progress(): int
    {
        return match ($this) {
            self::UPLOADED => 0,
            self::QUEUED => 10,
            self::PARSING => 30,
            self::CHUNKING => 60,
            self::GENERATING_JSONLD => 85,
            self::READY => 100,
            self::FAILED => 0,
        };
    }
}
