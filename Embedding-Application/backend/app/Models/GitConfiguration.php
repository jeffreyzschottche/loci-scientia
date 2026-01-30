<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class GitConfiguration extends Model
{
    protected $fillable = [
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
}
