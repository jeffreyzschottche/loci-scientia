<?php

namespace App\Models;

use App\Enums\ProcessingStage;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Database\Eloquent\Collection;

class Document extends Model
{
    protected $fillable = [
        'user_id',
        'parent_id',
        'position',
        'priority',
        'doc_id',
        'title',
        'category',
        'version_tag',
        'source_url',
        'description',
        'metadata',
        'filename',
        'original_filename',
        'mime_type',
        'file_size',
        'status',
        'chunk_count',
        'parsed_at',
        'json_ld',
        'processing_stage',
        'processing_progress',
    ];

    protected $casts = [
        'metadata' => 'array',
        'json_ld' => 'array',
        'parsed_at' => 'datetime',
        'processing_stage' => ProcessingStage::class,
    ];

    public function user(): BelongsTo
    {
        return $this->belongsTo(User::class);
    }

    public function parent(): BelongsTo
    {
        return $this->belongsTo(Document::class, 'parent_id');
    }

    public function children(): HasMany
    {
        return $this->hasMany(Document::class, 'parent_id')->orderBy('position');
    }

    public function sections(): HasMany
    {
        return $this->hasMany(DocumentSection::class)->orderBy('order_index');
    }

    public function chunks(): HasMany
    {
        return $this->hasMany(DocumentChunk::class);
    }

    /**
     * Get outgoing relations (this document is the source).
     */
    public function outgoingRelations(): HasMany
    {
        return $this->hasMany(DocumentRelation::class, 'source_document_id');
    }

    /**
     * Get incoming relations (this document is the target).
     */
    public function incomingRelations(): HasMany
    {
        return $this->hasMany(DocumentRelation::class, 'target_document_id');
    }

    /**
     * Add a relation from this document to another document.
     */
    public function addRelationTo(Document $target, string $type = 'references', ?array $metadata = null): DocumentRelation
    {
        return DocumentRelation::firstOrCreate([
            'source_document_id' => $this->id,
            'target_document_id' => $target->id,
            'relation_type' => $type,
        ], [
            'metadata' => $metadata,
        ]);
    }

    /**
     * Remove a relation from this document to another document.
     */
    public function removeRelationTo(Document $target, ?string $type = null): int
    {
        $query = DocumentRelation::where('source_document_id', $this->id)
            ->where('target_document_id', $target->id);

        if ($type) {
            $query->where('relation_type', $type);
        }

        return $query->delete();
    }

    /**
     * Get all descendants (children, grandchildren, etc.) recursively.
     */
    public function descendants(): Collection
    {
        $descendants = new Collection();

        foreach ($this->children as $child) {
            $descendants->push($child);
            $descendants = $descendants->merge($child->descendants());
        }

        return $descendants;
    }

    /**
     * Get all ancestors (parent, grandparent, etc.) up to root.
     */
    public function ancestors(): Collection
    {
        $ancestors = new Collection();
        $current = $this->parent;

        while ($current) {
            $ancestors->push($current);
            $current = $current->parent;
        }

        return $ancestors;
    }

    /**
     * Check if this document is a root document (no parent).
     */
    public function isRoot(): bool
    {
        return $this->parent_id === null;
    }

    /**
     * Get the depth of this document in the hierarchy.
     */
    public function depth(): int
    {
        return $this->ancestors()->count();
    }

    /**
     * Move this document to a new parent or position.
     */
    public function moveTo(?Document $newParent, ?int $position = null): void
    {
        $this->parent_id = $newParent?->id;

        if ($position !== null) {
            $this->position = $position;
        }

        $this->save();
    }

    /**
     * Check if processing is complete.
     */
    public function isReady(): bool
    {
        return $this->processing_stage === ProcessingStage::READY;
    }

    /**
     * Check if processing failed.
     */
    public function hasFailed(): bool
    {
        return $this->processing_stage === ProcessingStage::FAILED;
    }

    /**
     * Check if document is currently being processed.
     */
    public function isProcessing(): bool
    {
        return $this->processing_stage?->isProcessing() ?? false;
    }
}
