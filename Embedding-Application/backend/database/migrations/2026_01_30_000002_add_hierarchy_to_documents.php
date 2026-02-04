<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('documents', function (Blueprint $table) {
            $table->foreignId('parent_id')->nullable()->after('user_id')
                ->constrained('documents')->nullOnDelete();
            $table->unsignedInteger('position')->default(0)->after('parent_id');

            $table->index('parent_id');
            $table->index(['parent_id', 'position']);
        });
    }

    public function down(): void
    {
        Schema::table('documents', function (Blueprint $table) {
            $table->dropForeign(['parent_id']);
            $table->dropIndex(['parent_id']);
            $table->dropIndex(['parent_id', 'position']);
            $table->dropColumn(['parent_id', 'position']);
        });
    }
};
