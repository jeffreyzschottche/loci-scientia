<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Support\Facades\RateLimiter;
use Illuminate\Support\Str;
use Illuminate\Validation\ValidationException;

class LoginRequest extends FormRequest
{
    private const MAX_ATTEMPTS = 5;

    private const DECAY_SECONDS = 3600;

    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'email' => ['required', 'email'],
            'password' => ['required'],
        ];
    }

    public function ensureIsNotRateLimited(): void
    {
        if (! $this->isRateLimited()) {
            return;
        }

        throw ValidationException::withMessages([
            'email' => [
                "Te veel mislukte inlogpogingen. Probeer het opnieuw over {$this->retryAfterMinutes()} minuten.",
            ],
        ])->status(429);
    }

    public function isRateLimited(): bool
    {
        return RateLimiter::tooManyAttempts($this->throttleKey(), self::MAX_ATTEMPTS);
    }

    public function hitRateLimiter(): void
    {
        RateLimiter::hit($this->throttleKey(), self::DECAY_SECONDS);
    }

    public function clearRateLimiter(): void
    {
        RateLimiter::clear($this->throttleKey());
    }

    public function rateLimitMeta(): array
    {
        $attempts = RateLimiter::attempts($this->throttleKey());

        return [
            'attempts' => $attempts,
            'max_attempts' => self::MAX_ATTEMPTS,
            'remaining' => max(0, self::MAX_ATTEMPTS - $attempts),
            'retry_after_seconds' => $this->isRateLimited()
                ? RateLimiter::availableIn($this->throttleKey())
                : null,
        ];
    }

    public function retryAfterMinutes(): int
    {
        return (int) ceil(RateLimiter::availableIn($this->throttleKey()) / 60);
    }

    private function throttleKey(): string
    {
        return Str::lower((string) $this->string('email')).'|'.$this->ip();
    }
}
