<?php

use App\Http\Controllers\Api\V1\AuthController;
use App\Http\Controllers\Api\V1\DocumentController;
use App\Http\Controllers\Api\V1\LibraryController;
use App\Http\Controllers\Api\V1\InsightsController;
use App\Http\Controllers\Api\V1\KennisbankController;
use App\Http\Controllers\Api\V1\PriorityController;
use Illuminate\Support\Facades\Route;

Route::prefix('v1')->group(function () {
    // Public routes
    Route::post('/register', [AuthController::class, 'register']);
    Route::post('/login', [AuthController::class, 'login']);
    Route::post('/forgot-password', [AuthController::class, 'forgotPassword']);
    Route::post('/reset-password', [AuthController::class, 'resetPassword']);

    // Email verification
    Route::get('/email/verify/{id}/{hash}', [AuthController::class, 'verifyEmail'])
        ->name('verification.verify');

    // Protected routes
    Route::middleware('auth:sanctum')->group(function () {
        Route::post('/logout', [AuthController::class, 'logout']);
        Route::get('/me', [AuthController::class, 'me']);
        Route::post('/email/resend', [AuthController::class, 'resendVerification']);
        Route::patch('/profile', [AuthController::class, 'updateProfile']);
        Route::patch('/password', [AuthController::class, 'updatePassword']);

        // Documents (Upload API)
        Route::get('/documents', [DocumentController::class, 'index']);
        Route::post('/documents', [DocumentController::class, 'store']);
        Route::get('/documents/{document}', [DocumentController::class, 'show']);
        Route::patch('/documents/{document}', [DocumentController::class, 'update']);
        Route::post('/documents/{document}/mapping', [DocumentController::class, 'saveMapping']);
        Route::post('/documents/{document}/process', [DocumentController::class, 'process']);
        Route::get('/documents/{document}/status', [DocumentController::class, 'status']);
        Route::delete('/documents/{document}', [DocumentController::class, 'destroy']);

        // Library API
        Route::prefix('library')->group(function () {
            Route::get('/tree', [LibraryController::class, 'tree']);
            Route::get('/search', [LibraryController::class, 'search']);

            Route::get('/documents/{document}', [LibraryController::class, 'document']);
            Route::patch('/documents/{document}', [LibraryController::class, 'updateDocument']);

            Route::get('/sections/{section}', [LibraryController::class, 'section']);
            Route::patch('/sections/{section}', [LibraryController::class, 'updateSection']);
        });

        // Insights API
        Route::prefix('insights')->group(function () {
            Route::get('/stats', [InsightsController::class, 'stats']);
            Route::get('/categories', [InsightsController::class, 'categories']);
            Route::get('/versions', [InsightsController::class, 'versions']);

            Route::get('/export/manifest', [InsightsController::class, 'exportManifest']);
            Route::get('/export/chunks', [InsightsController::class, 'exportChunks']);
            Route::post('/exports', [InsightsController::class, 'createExport']);
            Route::get('/exports', [InsightsController::class, 'listExports']);
            Route::get('/exports/{export}/download', [InsightsController::class, 'downloadExport']);
        });

        // Priority API
        Route::prefix('priorities')->group(function () {
            Route::get('/', [PriorityController::class, 'index']);
            Route::patch('/{document}', [PriorityController::class, 'update']);
            Route::post('/bulk', [PriorityController::class, 'bulkUpdate']);
        });

        // Kennisbank / Git sync (legacy - kept for compatibility)
        Route::get('/kennisbank/git-config', [KennisbankController::class, 'getGitConfig']);
        Route::post('/kennisbank/git-config', [KennisbankController::class, 'updateGitConfig']);
        Route::post('/kennisbank/push', [KennisbankController::class, 'pushToGit']);
    });
});
