<?php

namespace App\Http\Controllers\Api\V1;

use App\Http\Controllers\Controller;
use App\Services\DeviceSyncService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Log;

class KennisbankController extends Controller
{
    public function __construct(
        private DeviceSyncService $deviceSync
    ) {}

    /**
     * Bundel de kennisbank en push hem naar de Aitje device over LAN.
     * Vervangt de oude pushToGit-flow.
     */
    public function pushToDevice(Request $request): JsonResponse
    {
        try {
            Log::info('Device push requested', ['user_id' => $request->user()->id]);

            $result = $this->deviceSync->syncUser($request->user());

            Log::info('Device push completed', $result);

            return response()->json([
                'message' => 'Kennisbank gesynchroniseerd met device.',
                'last_pushed_at' => $result['last_pushed_at'],
                'device_response' => $result['device_response'] ?? null,
            ]);
        } catch (\Throwable $e) {
            Log::error('Device push failed', ['error' => $e->getMessage()]);

            return response()->json([
                'message' => 'Synchronisatie naar device mislukt.',
                'error' => $e->getMessage(),
            ], 500);
        }
    }
}
