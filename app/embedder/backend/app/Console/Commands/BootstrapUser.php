<?php

namespace App\Console\Commands;

use App\Models\User;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\Hash;

class BootstrapUser extends Command
{
    protected $signature = 'aitje:bootstrap-user
        {--force : Wachtwoord opnieuw zetten als de gebruiker al bestaat}';

    protected $description = 'Maak de single-tenant embedder-gebruiker aan uit EMBEDDER_USER_EMAIL / EMBEDDER_USER_PASSWORD env vars (idempotent).';

    public function handle(): int
    {
        $email = trim((string) env('EMBEDDER_USER_EMAIL', ''));
        $password = (string) env('EMBEDDER_USER_PASSWORD', '');
        $name = trim((string) env('EMBEDDER_USER_NAME', '')) ?: 'Aitje';

        if ($email === '' || $password === '') {
            $this->info('EMBEDDER_USER_EMAIL of EMBEDDER_USER_PASSWORD niet gezet — gebruiker wordt niet aangemaakt.');
            return self::SUCCESS;
        }

        $existing = User::where('email', $email)->first();
        if ($existing !== null) {
            if ($this->option('force')) {
                $existing->forceFill([
                    'name' => $name,
                    'password' => Hash::make($password),
                    'email_verified_at' => $existing->email_verified_at ?? now(),
                ])->save();
                $this->info("Gebruiker {$email} bestond al; wachtwoord opnieuw gezet (--force).");
                return self::SUCCESS;
            }
            $this->info("Gebruiker {$email} bestaat al — overgeslagen (gebruik --force om wachtwoord te overschrijven).");
            return self::SUCCESS;
        }

        User::create([
            'name' => $name,
            'email' => $email,
            'password' => $password,  // het 'hashed' cast op het User-model regelt hashing
            'email_verified_at' => now(),
        ]);

        $this->info("Embedder-gebruiker {$email} aangemaakt.");
        return self::SUCCESS;
    }
}
