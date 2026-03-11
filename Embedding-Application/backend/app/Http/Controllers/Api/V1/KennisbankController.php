<?php

namespace App\Http\Controllers\Api\V1;

use App\Http\Controllers\Controller;
use App\Models\GitConfiguration;
use App\Services\GitSyncService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Log;
use Illuminate\Validation\ValidationException;

class KennisbankController extends Controller
{
    public function __construct(
        private GitSyncService $gitSyncService
    ) {}

    /**
     * Get git configuration (without sensitive token).
     */
    public function getGitConfig(Request $request): JsonResponse
    {
        $config = GitConfiguration::where('user_id', $request->user()->id)->first();

        return response()->json(['config' => $config]);
    }

    /**
     * Store or update git configuration.
     */
    public function updateGitConfig(Request $request): JsonResponse
    {
        $validated = $request->validate([
            'repo_url' => 'required|url',
            'branch' => 'required|string|max:255',
            'access_token' => 'nullable|string',
        ]);

        $existing = GitConfiguration::where('user_id', $request->user()->id)->first();

        if (! $existing && empty($validated['access_token'])) {
            throw ValidationException::withMessages([
                'access_token' => ['Access token is required for the first configuration.'],
            ]);
        }

        $data = [
            'user_id' => $request->user()->id,
            'repo_url' => $validated['repo_url'],
            'branch' => $validated['branch'],
        ];

        if (! empty($validated['access_token'])) {
            $data['access_token'] = $validated['access_token'];
        }

        $config = GitConfiguration::updateOrCreate(
            ['user_id' => $request->user()->id],
            $data
        );

        return response()->json([
            'message' => 'Git configuration saved',
            'config' => $config,
        ]);
    }

    /**
     * Export embeddings to SQLite and push to git.
     */
    public function pushToGit(Request $request): JsonResponse
    {
        try {
            Log::info('Git push requested', ['user_id' => $request->user()->id]);
            $result = $this->gitSyncService->syncUser($request->user());

            Log::info('Git push completed', $result);

            return response()->json([
                'message' => $result['pushed']
                    ? 'Kennisbank synced to OS successfully'
                    : 'No changes to push',
                'last_pushed_at' => $result['last_pushed_at'],
            ]);
        } catch (\Exception $e) {
            Log::error('Git push failed', ['error' => $e->getMessage()]);

            return response()->json([
                'message' => 'Git push failed',
                'error' => $e->getMessage(),
            ], 500);
        }
    }
}
