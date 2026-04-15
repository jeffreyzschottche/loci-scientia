<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::dropIfExists('document_relations');
        Schema::dropIfExists('section_relations');

        if (Schema::hasColumn('documents', 'parent_id')) {
            $connection = Schema::getConnection();

            $fks = $connection->select(
                "SELECT CONSTRAINT_NAME FROM information_schema.KEY_COLUMN_USAGE
                 WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'documents'
                   AND COLUMN_NAME = 'parent_id' AND REFERENCED_TABLE_NAME IS NOT NULL"
            );
            foreach ($fks as $fk) {
                $connection->statement("ALTER TABLE `documents` DROP FOREIGN KEY `{$fk->CONSTRAINT_NAME}`");
            }

            $indexes = $connection->select(
                "SHOW INDEX FROM `documents` WHERE Key_name = ?",
                ['documents_user_parent_position_created_at_index']
            );
            if (! empty($indexes)) {
                $userIdx = $connection->select(
                    "SHOW INDEX FROM `documents` WHERE Key_name = ?",
                    ['documents_user_id_index']
                );
                if (empty($userIdx)) {
                    Schema::table('documents', function (Blueprint $table) {
                        $table->index('user_id', 'documents_user_id_index');
                    });
                }

                Schema::table('documents', function (Blueprint $table) {
                    $table->dropIndex('documents_user_parent_position_created_at_index');
                });
            }

            $parentIdx = $connection->select(
                "SHOW INDEX FROM `documents` WHERE Key_name = ?",
                ['documents_parent_id_index']
            );
            if (! empty($parentIdx)) {
                Schema::table('documents', function (Blueprint $table) {
                    $table->dropIndex('documents_parent_id_index');
                });
            }

            $parentPosIdx = $connection->select(
                "SHOW INDEX FROM `documents` WHERE Key_name = ?",
                ['documents_parent_id_position_index']
            );
            if (! empty($parentPosIdx)) {
                Schema::table('documents', function (Blueprint $table) {
                    $table->dropIndex('documents_parent_id_position_index');
                });
            }

            Schema::table('documents', function (Blueprint $table) {
                $table->dropColumn('parent_id');
            });
        }
    }

    public function down(): void
    {
        // Restore section_relations
        Schema::create('section_relations', function (Blueprint $table) {
            $table->id();
            $table->foreignId('source_section_id')->constrained('document_sections')->onDelete('cascade');
            $table->foreignId('target_section_id')->constrained('document_sections')->onDelete('cascade');
            $table->string('relation_type', 50)->default('references');
            $table->json('metadata')->nullable();
            $table->timestamps();
            $table->unique(['source_section_id', 'target_section_id', 'relation_type'], 'unique_section_relation');
        });

        // Restore document_relations
        Schema::create('document_relations', function (Blueprint $table) {
            $table->id();
            $table->foreignId('source_document_id')->constrained('documents')->cascadeOnDelete();
            $table->foreignId('target_document_id')->constrained('documents')->cascadeOnDelete();
            $table->string('relation_type', 50)->default('references');
            $table->json('metadata')->nullable();
            $table->timestamps();
            $table->unique(['source_document_id', 'target_document_id', 'relation_type'], 'unique_document_relation');
        });

        // Restore parent_id
        Schema::table('documents', function (Blueprint $table) {
            $table->foreignId('parent_id')->nullable()->constrained('documents')->nullOnDelete();
        });
    }
};
