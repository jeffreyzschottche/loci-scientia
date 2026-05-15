<?php

namespace Tests\Feature\Auth;

use App\Models\User;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;
use Tests\TestCase;

class LoginRateLimitTest extends TestCase
{
    protected function setUp(): void
    {
        parent::setUp();

        Schema::dropIfExists('personal_access_tokens');
        Schema::dropIfExists('users');

        Schema::create('users', function (Blueprint $table) {
            $table->id();
            $table->string('name');
            $table->string('email')->unique();
            $table->timestamp('email_verified_at')->nullable();
            $table->string('password');
            $table->rememberToken();
            $table->timestamps();
        });

        Schema::create('personal_access_tokens', function (Blueprint $table) {
            $table->id();
            $table->morphs('tokenable');
            $table->string('name');
            $table->string('token', 64)->unique();
            $table->text('abilities')->nullable();
            $table->timestamp('last_used_at')->nullable();
            $table->timestamp('expires_at')->nullable();
            $table->timestamps();
        });
    }

    public function test_login_is_locked_for_an_hour_after_five_failed_attempts(): void
    {
        $user = User::factory()->create([
            'email' => 'lockout@example.com',
        ]);

        for ($attempt = 0; $attempt < 5; $attempt++) {
            $this->postJson('/api/v1/login', [
                'email' => $user->email,
                'password' => 'verkeerd-wachtwoord',
            ])->assertStatus(422);
        }

        $this->postJson('/api/v1/login', [
            'email' => $user->email,
            'password' => 'password',
        ])
            ->assertStatus(429)
            ->assertJsonValidationErrors('email');
    }

    public function test_successful_login_clears_failed_attempts(): void
    {
        $user = User::factory()->create([
            'email' => 'clear-lockout@example.com',
        ]);

        for ($attempt = 0; $attempt < 4; $attempt++) {
            $this->postJson('/api/v1/login', [
                'email' => $user->email,
                'password' => 'verkeerd-wachtwoord',
            ])->assertStatus(422);
        }

        $this->postJson('/api/v1/login', [
            'email' => $user->email,
            'password' => 'password',
        ])->assertOk();

        $this->postJson('/api/v1/login', [
            'email' => $user->email,
            'password' => 'verkeerd-wachtwoord',
        ])->assertStatus(422);
    }
}
