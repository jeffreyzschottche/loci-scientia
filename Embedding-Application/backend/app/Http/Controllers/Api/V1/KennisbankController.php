<?php

namespace App\Http\Controllers\Api\V1;

use App\Http\Controllers\Controller;
use App\Models\GitConfiguration;
use App\Services\GitSyncService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Log;

class KennisbankController extends Controller
{
    public function __construct(
        private GitSyncService $gitSyncService
    ) {}

    /**
     * Get git configuration (without sensitive token).
     */
    public function getGitConfig(): JsonResponse
    {
        $config = GitConfiguration::first();

        return response()->json(['config' => $config]);
    }

    /**
     * Store or update git configuration.
     */
    public function updateGitConfig(Request $request): JsonResponse
    {
        $validated = $request->validate([
            'repo_url' => 'required|url',
            'branch' => 'required|string',
            'access_token' => 'required|string',
        ]);

        $config = GitConfiguration::updateOrCreate(
            ['id' => 1],
            $validated
        );

        return response()->json([
            'message' => 'Git configuration saved',
            'config' => $config,
        ]);
    }

    /**
     * Export embeddings to SQLite and push to git.
     */
    public function pushToGit(): JsonResponse
    {
        try {
            Log::info('Git push requested');
            $result = $this->gitSyncService->syncToGit();

            Log::info('Git push completed', $result);

            return response()->json([
                'message' => $result['pushed']
                    ? 'Kennisbank pushed to git successfully'
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
