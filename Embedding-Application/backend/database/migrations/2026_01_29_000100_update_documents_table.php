<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    private function dropIndexIfExists(string $tableName, string $index): void
    {
        $connection = Schema::getConnection();
        $indexes = $connection->select("SHOW INDEX FROM `{$tableName}` WHERE Key_name = ?", [$index]);

        if (! empty($indexes)) {
            Schema::table($tableName, function (Blueprint $table) use ($index) {
                $table->dropIndex($index);
            });
        }
    }

    private function hasIndex(string $tableName, string $index): bool
    {
        $connection = Schema::getConnection();
        $indexes = $connection->select("SHOW INDEX FROM `{$tableName}` WHERE Key_name = ?", [$index]);

        return ! empty($indexes);
    }
    public function up(): void
    {
        Schema::table('documents', function (Blueprint $table) {
            if (! Schema::hasColumn('documents', 'doc_id')) {
                $table->string('doc_id')->nullable()->after('id');
            }

            if (! Schema::hasColumn('documents', 'title')) {
                $table->string('title')->nullable()->after('doc_id');
            }

            if (! Schema::hasColumn('documents', 'category')) {
                $table->string('category')->nullable()->after('title');
            }

            if (! Schema::hasColumn('documents', 'version_tag')) {
                $table->string('version_tag')->nullable()->after('category');
            }

            if (! Schema::hasColumn('documents', 'source_url')) {
                $table->string('source_url')->nullable()->after('version_tag');
            }

            if (! Schema::hasColumn('documents', 'description')) {
                $table->text('description')->nullable()->after('source_url');
            }

            if (! Schema::hasColumn('documents', 'parsed_at')) {
                $table->timestamp('parsed_at')->nullable()->after('chunk_count');
            }

            if (! Schema::hasColumn('documents', 'metadata')) {
                $table->json('metadata')->nullable()->after('parsed_at');
            }

            if (! Schema::hasColumn('documents', 'json_ld')) {
                $table->json('json_ld')->nullable()->after('metadata');
            }

            if (! Schema::hasColumn('documents', 'processing_stage')) {
                $table->string('processing_stage')->nullable()->after('json_ld');
            }

            if (! Schema::hasColumn('documents', 'processing_progress')) {
                $table->unsignedTinyInteger('processing_progress')->default(0)->after('processing_stage');
            }
        });

        if (! Schema::hasTable('documents')) {
            return;
        }

        if (Schema::hasColumn('documents', 'doc_id') && !$this->hasIndex('documents', 'documents_doc_id_unique')) {
            Schema::table('documents', function (Blueprint $table) {
                $table->unique('doc_id');
            });
        }

        if (Schema::hasColumn('documents', 'status')) {
            DB::statement("ALTER TABLE `documents` MODIFY `status` ENUM('uploaded','processing','formatted','failed') NOT NULL DEFAULT 'uploaded'");
        }
    }

    public function down(): void
    {
        Schema::table('documents', function (Blueprint $table) {
            if (Schema::hasColumn('documents', 'doc_id')) {
                $this->dropIndexIfExists('documents', 'documents_doc_id_unique');
                $table->dropColumn('doc_id');
            }

            foreach (['title', 'category', 'version_tag', 'source_url', 'description', 'parsed_at', 'metadata', 'json_ld', 'processing_stage', 'processing_progress'] as $column) {
                if (Schema::hasColumn('documents', $column)) {
                    $table->dropColumn($column);
                }
            }
        });

        if (Schema::hasColumn('documents', 'status')) {
            DB::statement("ALTER TABLE `documents` MODIFY `status` ENUM('uploaded','processing','embedded','failed') NOT NULL DEFAULT 'uploaded'");
        }
    }
};
