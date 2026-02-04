<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class SectionRelation extends Model
{
    public const TYPE_REFERENCES = 'references';
    public const TYPE_EXTENDS = 'extends';
    public const TYPE_CONTRADICTS = 'contradicts';
    public const TYPE_SUPPLEMENTS = 'supplements';
    public const TYPE_PARENT_OF = 'parent_of';
    public const TYPE_RELATED_TO = 'related_to';

    protected $fillable = [
        'source_section_id',
        'target_section_id',
        'relation_type',
        'metadata',
    ];

    protected $casts = [
        'metadata' => 'array',
    ];

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

    public function sourceSection(): BelongsTo
    {
        return $this->belongsTo(DocumentSection::class, 'source_section_id');
    }

    public function targetSection(): BelongsTo
    {
        return $this->belongsTo(DocumentSection::class, 'target_section_id');
    }
}
