<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        if ($this->hasIndex('documents', 'documents_user_parent_position_created_at_index')) {
            return;
        }

        Schema::table('documents', function (Blueprint $table) {
            $table->index(
                ['user_id', 'parent_id', 'position', 'created_at'],
                'documents_user_parent_position_created_at_index'
            );
        });
    }

    public function down(): void
    {
        if (! $this->hasIndex('documents', 'documents_user_parent_position_created_at_index')) {
            return;
        }

        Schema::table('documents', function (Blueprint $table) {
            $table->dropIndex('documents_user_parent_position_created_at_index');
        });
    }

    private function hasIndex(string $tableName, string $index): bool
    {
        $connection = Schema::getConnection();
        $indexes = $connection->select("SHOW INDEX FROM `{$tableName}` WHERE Key_name = ?", [$index]);

        return ! empty($indexes);
    }
};
