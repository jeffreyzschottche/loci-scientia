<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        if (! Schema::hasColumn('documents', 'images')) {
            return;
        }

        Schema::table('documents', function (Blueprint $table) {
            $table->dropColumn('images');
        });
    }

    public function down(): void
    {
        // Column intentionally not recreated; image support removed.
    }
};
