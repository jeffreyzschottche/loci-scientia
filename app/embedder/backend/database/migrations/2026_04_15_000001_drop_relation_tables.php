<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    private function hasIndex(string $tableName, string $index): bool
    {
        foreach (Schema::getIndexes($tableName) as $idx) {
            if (($idx['name'] ?? null) === $index) {
                return true;
            }
        }

        return false;
    }

    public function up(): void
    {
        Schema::dropIfExists('document_relations');
        Schema::dropIfExists('section_relations');

        if (! Schema::hasColumn('documents', 'parent_id')) {
            return;
        }

        // Drop de FK eerst — verplicht op SQLite (anders weigert dropColumn
        // omdat de constraint nog naar parent_id verwijst) én portabel op
        // MySQL. `dropForeign(['parent_id'])` leidt de constraint-naam af uit
        // de kolom, dus geen information_schema lookup nodig.
        try {
            Schema::table('documents', function (Blueprint $table) {
                $table->dropForeign(['parent_id']);
            });
        } catch (\Throwable $e) {
            // FK bestond niet meer (oude installaties of eerdere mislukte run).
        }

        if ($this->hasIndex('documents', 'documents_user_parent_position_created_at_index')) {
            if (! $this->hasIndex('documents', 'documents_user_id_index')) {
                Schema::table('documents', function (Blueprint $table) {
                    $table->index('user_id', 'documents_user_id_index');
                });
            }
            Schema::table('documents', function (Blueprint $table) {
                $table->dropIndex('documents_user_parent_position_created_at_index');
            });
        }

        foreach (['documents_parent_id_index', 'documents_parent_id_position_index'] as $idxName) {
            if ($this->hasIndex('documents', $idxName)) {
                Schema::table('documents', function (Blueprint $table) use ($idxName) {
                    $table->dropIndex($idxName);
                });
            }
        }

        Schema::table('documents', function (Blueprint $table) {
            $table->dropColumn('parent_id');
        });
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
