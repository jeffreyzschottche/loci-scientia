<?php

namespace App\Providers;

use App\Services\KennisbankUserSynchronizer;
use Illuminate\Support\Facades\App;
use Illuminate\Support\ServiceProvider;

class AppServiceProvider extends ServiceProvider
{
    public function register(): void
    {
        //
    }

    public function boot(): void
    {
        App::booted(function () {
            App::make(KennisbankUserSynchronizer::class)->sync();
        });
    }
}
