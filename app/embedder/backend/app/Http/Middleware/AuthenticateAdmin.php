<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Cache;
use Symfony\Component\HttpFoundation\Response;

class AuthenticateAdmin
{
    public function handle(Request $request, Closure $next): Response
    {
        $token = $request->bearerToken();

        if (! $token) {
            return response()->json(['message' => 'Admin login required'], 401);
        }

        $email = Cache::get($this->cacheKey($token));

        if (! $email) {
            return response()->json(['message' => 'Admin session expired'], 401);
        }

        $request->attributes->set('admin_email', $email);

        return $next($request);
    }

    public static function cacheKey(string $token): string
    {
        return 'admin_token:'.hash('sha256', $token);
    }
}
