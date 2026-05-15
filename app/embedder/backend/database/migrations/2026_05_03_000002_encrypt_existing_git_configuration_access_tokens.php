<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Support\Facades\Crypt;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        if (! Schema::hasTable('git_configurations')) {
            return;
        }

        DB::table('git_configurations')
            ->whereNotNull('access_token')
            ->orderBy('id')
            ->each(function (object $configuration): void {
                if ($configuration->access_token === '') {
                    return;
                }

                try {
                    Crypt::decryptString($configuration->access_token);
                    return;
                } catch (Throwable) {
                    //
                }

                DB::table('git_configurations')
                    ->where('id', $configuration->id)
                    ->update([
                        'access_token' => Crypt::encryptString($configuration->access_token),
                    ]);
            });
    }

    public function down(): void
    {
        //
    }
};
