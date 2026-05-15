<?php

namespace App\Models;

use App\Enums\ProcessingStage;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Document extends Model
{
    protected $fillable = [
        'user_id',
        'position',
        'priority',
        'doc_id',
        'title',
        'category',
        'version_tag',
        'content_date',
        'language',
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
        'content_date' => 'date',
        'processing_stage' => ProcessingStage::class,
    ];

    public function user(): BelongsTo
    {
        return $this->belongsTo(User::class);
    }

    public function sections(): HasMany
    {
        return $this->hasMany(DocumentSection::class)->orderBy('order_index');
    }

    public function chunks(): HasMany
    {
        return $this->hasMany(DocumentChunk::class);
    }

    public function isReady(): bool
    {
        return $this->processing_stage === ProcessingStage::READY;
    }

    public function hasFailed(): bool
    {
        return $this->processing_stage === ProcessingStage::FAILED;
    }

    public function isProcessing(): bool
    {
        return $this->processing_stage?->isProcessing() ?? false;
    }
}
