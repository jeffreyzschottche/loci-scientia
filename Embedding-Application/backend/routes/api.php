<?php

use Illuminate\Support\Facades\Route;
use App\Http\Controllers\Api\V1\AuthController;
use App\Http\Controllers\Api\V1\DocumentController;
use App\Http\Controllers\Api\V1\KennisbankController;

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

        // Documents
        Route::get('/documents', [DocumentController::class, 'index']);
        Route::post('/documents', [DocumentController::class, 'store']);
        Route::post('/documents/{document}/process', [DocumentController::class, 'process']);
        Route::delete('/documents/{document}', [DocumentController::class, 'destroy']);

        // Kennisbank / Git sync
        Route::get('/kennisbank/git-config', [KennisbankController::class, 'getGitConfig']);
        Route::post('/kennisbank/git-config', [KennisbankController::class, 'updateGitConfig']);
        Route::post('/kennisbank/push', [KennisbankController::class, 'pushToGit']);
    });
});
