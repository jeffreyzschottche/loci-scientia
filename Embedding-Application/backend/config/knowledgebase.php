<?php

use App\Support\RootEnv;

return [
    'user' => [
        'email' => env('KENNISBANK_USER', RootEnv::get('KENNISBANK_USER')),
        'password' => env('KENNISBANK_PW', RootEnv::get('KENNISBANK_PW')),
    ],
    'git' => [
        'repo' => env('KENNISBANK_GIT_REPO', RootEnv::get('KENNISBANK_GIT_REPO')),
        'branch' => env('KENNISBANK_GIT_BRANCH', RootEnv::get('KENNISBANK_GIT_BRANCH', 'main')),
        'token' => env('KENNISBANK_GIT_TOKEN', RootEnv::get('KENNISBANK_GIT_TOKEN')),
    ],
    'export' => [
        'base_path' => storage_path('app/exports'),
        'current_dir' => 'current',
        'history_dir' => 'exports',
        'manifest' => 'manifest.json',
        'documents_file' => 'documents.jsonl',
    ],
];
