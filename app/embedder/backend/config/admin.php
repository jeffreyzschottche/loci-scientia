<?php

return [
    'email' => env('ADMIN_EMAIL'),
    'password_hash' => env('ADMIN_PASSWORD_HASH'),
    'token_ttl_minutes' => (int) env('ADMIN_TOKEN_TTL_MINUTES', 480),
];
