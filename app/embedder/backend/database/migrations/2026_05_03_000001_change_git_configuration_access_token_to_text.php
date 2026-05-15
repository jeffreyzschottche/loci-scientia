<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        if (! Schema::hasTable('git_configurations')) {
            return;
        }

        if (DB::getDriverName() === 'mysql') {
            DB::statement('ALTER TABLE git_configurations MODIFY access_token TEXT NOT NULL');
        }
    }

    public function down(): void
    {
        if (! Schema::hasTable('git_configurations')) {
            return;
        }

        if (DB::getDriverName() === 'mysql') {
            DB::statement('ALTER TABLE git_configurations MODIFY access_token VARCHAR(255) NOT NULL');
        }
    }
};
