<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('documents', function (Blueprint $table) {
            // Priority per category (lower number = higher priority, 0 = default/unset)
            $table->unsignedInteger('priority')->default(0)->after('position');

            // Index for efficient category+priority queries
            $table->index(['category', 'priority']);
        });
    }

    public function down(): void
    {
        Schema::table('documents', function (Blueprint $table) {
            $table->dropIndex(['category', 'priority']);
            $table->dropColumn('priority');
        });
    }
};
