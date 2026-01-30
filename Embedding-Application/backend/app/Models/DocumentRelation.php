<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class DocumentRelation extends Model
{
    // Reuse the same relation types as SectionRelation for consistency
    public const TYPE_REFERENCES = 'references';
    public const TYPE_EXTENDS = 'extends';
    public const TYPE_CONTRADICTS = 'contradicts';
    public const TYPE_SUPPLEMENTS = 'supplements';
    public const TYPE_PARENT_OF = 'parent_of';
    public const TYPE_RELATED_TO = 'related_to';

    protected $fillable = [
        'source_document_id',
        'target_document_id',
        'relation_type',
        'metadata',
    ];

    protected $casts = [
        'metadata' => 'array',
    ];

    /**
     * Get all available relation types with Dutch labels.
     */
    public static function types(): array
    {
        return [
            self::TYPE_REFERENCES => 'Verwijst naar',
            self::TYPE_EXTENDS => 'Breidt uit',
            self::TYPE_CONTRADICTS => 'Spreekt tegen',
            self::TYPE_SUPPLEMENTS => 'Vult aan',
            self::TYPE_PARENT_OF => 'Is parent van',
            self::TYPE_RELATED_TO => 'Gerelateerd aan',
        ];
    }

    /**
     * Get the label for a given relation type.
     */
    public static function labelFor(string $type): string
    {
        return self::types()[$type] ?? $type;
    }

    public function sourceDocument(): BelongsTo
    {
        return $this->belongsTo(Document::class, 'source_document_id');
    }

    public function targetDocument(): BelongsTo
    {
        return $this->belongsTo(Document::class, 'target_document_id');
    }
}
