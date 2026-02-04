<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Export extends Model
{
    protected $fillable = [
        'version',
        'document_count',
        'chunk_count',
        'metadata',
    ];

    protected $casts = [
        'metadata' => 'array',
    ];
}
