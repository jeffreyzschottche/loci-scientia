<?php

namespace App\Services;

use App\Models\User;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Str;


class KennisbankUserSynchronizer
{
    public function sync(): void
    {
        $email = config('knowledgebase.user.email');
        $password = config('knowledgebase.user.password');

        if (empty($email) || empty($password)) {
            return;
        }

        $user = User::firstOrNew(['email' => $email]);

        $needsPasswordUpdate = ! $user->exists || ! Hash::check($password, $user->password);

        $user->fill([
            'name' => $user->name ?: 'Kennisbank Admin',
            'email_verified_at' => $user->email_verified_at ?: now(),
            'remember_token' => $user->remember_token ?: Str::random(10),
        ]);

        if ($needsPasswordUpdate) {
            $user->password = Hash::make($password);
        }

        $user->save();
    }
}
