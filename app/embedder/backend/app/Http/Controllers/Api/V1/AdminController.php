<?php

namespace App\Http\Controllers\Api\V1;

use App\Http\Controllers\Controller;
use App\Http\Middleware\AuthenticateAdmin;
use App\Models\User;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Str;
use Illuminate\Validation\Rules\Password;
use Illuminate\Validation\ValidationException;

class AdminController extends Controller
{
    public function login(Request $request): JsonResponse
    {
        $validated = $request->validate([
            'email' => ['required', 'email'],
            'password' => ['required', 'string'],
        ]);

        $adminEmail = config('admin.email');
        $adminPasswordHash = config('admin.password_hash');

        if (! $adminEmail || ! $adminPasswordHash) {
            return response()->json([
                'message' => 'Admin credentials are not configured.',
            ], 503);
        }

        if (password_get_info($adminPasswordHash)['algoName'] !== 'bcrypt') {
            return response()->json([
                'message' => 'Admin password hash is not configured correctly.',
            ], 503);
        }

        if (
            ! hash_equals(Str::lower($adminEmail), Str::lower($validated['email'])) ||
            ! Hash::check($validated['password'], $adminPasswordHash)
        ) {
            throw ValidationException::withMessages([
                'email' => ['Deze admin-gegevens kloppen niet.'],
            ]);
        }

        $token = Str::random(80);
        Cache::put(
            AuthenticateAdmin::cacheKey($token),
            $adminEmail,
            now()->addMinutes(config('admin.token_ttl_minutes'))
        );

        return response()->json([
            'token' => $token,
            'admin' => ['email' => $adminEmail],
        ]);
    }

    public function me(Request $request): JsonResponse
    {
        return response()->json([
            'admin' => ['email' => $request->attributes->get('admin_email')],
        ]);
    }

    public function logout(Request $request): JsonResponse
    {
        $token = $request->bearerToken();

        if ($token) {
            Cache::forget(AuthenticateAdmin::cacheKey($token));
        }

        return response()->json(['message' => 'Admin logged out']);
    }

    public function users(): JsonResponse
    {
        $users = User::query()
            ->withCount('documents')
            ->latest()
            ->get()
            ->map(fn (User $user) => $this->serializeUser($user));

        return response()->json(['users' => $users]);
    }

    public function createUser(Request $request): JsonResponse
    {
        $validated = $request->validate([
            'name' => ['required', 'string', 'max:255'],
            'email' => ['required', 'email', 'max:255', 'unique:users,email'],
            'password' => ['required', 'confirmed', Password::defaults()],
        ]);

        $user = User::create([
            'name' => $validated['name'],
            'email' => $validated['email'],
            'password' => $validated['password'],
            'email_verified_at' => now(),
        ]);

        return response()->json([
            'message' => 'Klantaccount aangemaakt.',
            'user' => $this->serializeUser($user->loadCount('documents')),
        ], 201);
    }

    public function impersonate(User $user): JsonResponse
    {
        $token = $user->createToken('admin_impersonation')->plainTextToken;

        return response()->json([
            'token' => $token,
            'user' => $user,
        ]);
    }

    private function serializeUser(User $user): array
    {
        return [
            'id' => $user->id,
            'name' => $user->name,
            'email' => $user->email,
            'email_verified_at' => $user->email_verified_at,
            'created_at' => $user->created_at,
            'updated_at' => $user->updated_at,
            'documents_count' => $user->documents_count ?? 0,
        ];
    }
}
