<?php

use Illuminate\Foundation\Application;
use Illuminate\Foundation\Configuration\Exceptions;
use Illuminate\Foundation\Configuration\Middleware;

return Application::configure(basePath: dirname(__DIR__))
    ->withRouting(
        web: __DIR__.'/../routes/web.php',
        api: __DIR__.'/../routes/api.php',
        // Routes worden door FastAPI ge-reverse-proxied onder /embedder/api/*
        // (zie app/backend/main.py). Door dezelfde prefix in Laravel te
        // registreren, klopt request->fullUrl() in de signed-URL middleware
        // exact met de URL die we via URL::forceRootUrl genereren.
        apiPrefix: 'embedder/api',
        commands: __DIR__.'/../routes/console.php',
        health: '/up',
    )
    ->withMiddleware(function (Middleware $middleware): void {
        // De Laravel-backend draait achter de FastAPI reverse-proxy (127.0.0.1)
        // op het device; vertrouw de X-Forwarded-* headers van de loopback.
        $middleware->trustProxies(at: '*');
    })
    ->withExceptions(function (Exceptions $exceptions): void {
        //
    })->create();
