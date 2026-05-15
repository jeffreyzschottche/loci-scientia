<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        if (! Schema::hasTable('documents')) {
            return;
        }

        Schema::table('documents', function (Blueprint $table) {
            if (! Schema::hasColumn('documents', 'content_date')) {
                $table->date('content_date')->nullable()->after('version_tag');
            }
        });

        DB::table('documents')
            ->whereNull('content_date')
            ->update(['content_date' => DB::raw('DATE(`created_at`)')]);
    }

    public function down(): void
    {
        if (! Schema::hasTable('documents')) {
            return;
        }

        Schema::table('documents', function (Blueprint $table) {
            if (Schema::hasColumn('documents', 'content_date')) {
                $table->dropColumn('content_date');
            }
        });
    }
};
