<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Database\Eloquent\Relations\BelongsToMany;
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

    /**
     * Sections this section relates TO (outgoing relations).
     */
    public function relatedTo(): BelongsToMany
    {
        return $this->belongsToMany(
            DocumentSection::class,
            'section_relations',
            'source_section_id',
            'target_section_id'
        )->withPivot('relation_type', 'metadata')->withTimestamps();
    }

    /**
     * Sections that relate TO this section (incoming relations).
     */
    public function relatedFrom(): BelongsToMany
    {
        return $this->belongsToMany(
            DocumentSection::class,
            'section_relations',
            'target_section_id',
            'source_section_id'
        )->withPivot('relation_type', 'metadata')->withTimestamps();
    }

    /**
     * Get all outgoing relations as SectionRelation models.
     */
    public function outgoingRelations(): HasMany
    {
        return $this->hasMany(SectionRelation::class, 'source_section_id');
    }

    /**
     * Get all incoming relations as SectionRelation models.
     */
    public function incomingRelations(): HasMany
    {
        return $this->hasMany(SectionRelation::class, 'target_section_id');
    }

    /**
     * Add a relation to another section.
     */
    public function addRelationTo(DocumentSection $target, string $type = 'references', ?array $metadata = null): SectionRelation
    {
        return SectionRelation::firstOrCreate([
            'source_section_id' => $this->id,
            'target_section_id' => $target->id,
            'relation_type' => $type,
        ], [
            'metadata' => $metadata,
        ]);
    }

    /**
     * Remove a relation to another section.
     */
    public function removeRelationTo(DocumentSection $target, ?string $type = null): int
    {
        $query = SectionRelation::where('source_section_id', $this->id)
            ->where('target_section_id', $target->id);

        if ($type) {
            $query->where('relation_type', $type);
        }

        return $query->delete();
    }

    /**
     * Get unique identifier for JSON-LD.
     */
    public function getJsonLdId(): string
    {
        return "sec:{$this->document->doc_id}#{$this->slug}";
    }

    /**
     * Get word count of this section.
     */
    public function wordCount(): int
    {
        return str_word_count($this->text ?? '');
    }
}
