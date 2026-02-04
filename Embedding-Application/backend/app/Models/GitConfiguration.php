<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class GitConfiguration extends Model
{
    protected $fillable = [
        'user_id',
        'repo_url',
        'branch',
        'access_token',
        'last_pushed_at',
    ];

    protected $casts = [
        'last_pushed_at' => 'datetime',
    ];

    protected $hidden = [
        'access_token',
    ];

    protected $appends = [
        'has_access_token',
    ];

    public function user(): BelongsTo
    {
        return $this->belongsTo(User::class);
    }

    public function getHasAccessTokenAttribute(): bool
    {
        return ! empty($this->access_token);
    }
}
