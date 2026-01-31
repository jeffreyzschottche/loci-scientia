<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        if (! Schema::hasTable('git_configurations')) {
            return;
        }

        Schema::table('git_configurations', function (Blueprint $table) {
            if (! Schema::hasColumn('git_configurations', 'user_id')) {
                $table->foreignId('user_id')
                    ->nullable()
                    ->after('id')
                    ->constrained()
                    ->onDelete('cascade')
                    ->unique();
            }
        });

        $firstUserId = DB::table('users')->min('id');

        if ($firstUserId) {
            DB::table('git_configurations')
                ->whereNull('user_id')
                ->update(['user_id' => $firstUserId]);
        }
    }

    public function down(): void
    {
        if (! Schema::hasTable('git_configurations')) {
            return;
        }

        Schema::table('git_configurations', function (Blueprint $table) {
            if (Schema::hasColumn('git_configurations', 'user_id')) {
                $table->dropConstrainedForeignId('user_id');
            }
        });
    }
};
