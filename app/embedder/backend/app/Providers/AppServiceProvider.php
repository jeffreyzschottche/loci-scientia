<?php

namespace App\Providers;

use Illuminate\Support\Facades\URL;
use Illuminate\Support\ServiceProvider;

class AppServiceProvider extends ServiceProvider
{
    public function register(): void
    {
        //
    }

    public function boot(): void
    {
        // De app draait achter een FastAPI reverse-proxy. Forceer scheme/host
        // op basis van APP_URL zodat gegenereerde absolute URLs (o.a. signed
        // email-verificatie links) het publieke origin gebruiken in plaats
        // van het loopback-adres dat `php artisan serve` ziet.
        // De /embedder-prefix zit al in de Laravel-routes (apiPrefix in
        // bootstrap/app.php), dus APP_URL bevat alleen scheme://host[:port].
        $appUrl = (string) config('app.url', '');
        if ($appUrl !== '') {
            URL::forceRootUrl($appUrl);

            if (str_starts_with($appUrl, 'https://')) {
                URL::forceScheme('https');
            }
        }
    }
}
