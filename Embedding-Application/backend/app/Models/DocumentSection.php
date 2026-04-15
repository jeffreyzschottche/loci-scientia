<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Support\Str;

class DocumentSection extends Model
{
    protected $fillable = [
        'document_id',
        'title',
        'slug',
        'order_index',
        'metadata',
        'text',
    ];

    protected $casts = [
        'metadata' => 'array',
    ];

    protected static function booted(): void
    {
        static::creating(function (DocumentSection $section) {
            if (empty($section->slug)) {
                $section->slug = Str::slug($section->title);
            }
        });
    }

    public function document(): BelongsTo
    {
        return $this->belongsTo(Document::class);
    }

    public function chunks(): HasMany
    {
        return $this->hasMany(DocumentChunk::class, 'section_id')->orderBy('chunk_index');
    }

    public function getJsonLdId(): string
    {
        return "sec:{$this->document->doc_id}#{$this->slug}";
    }

    public function wordCount(): int
    {
        return str_word_count($this->text ?? '');
    }
}
