<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('document_relations', function (Blueprint $table) {
            $table->id();
            $table->foreignId('source_document_id')->constrained('documents')->cascadeOnDelete();
            $table->foreignId('target_document_id')->constrained('documents')->cascadeOnDelete();
            $table->string('relation_type', 50)->default('references');
            $table->json('metadata')->nullable();
            $table->timestamps();

            // Prevent duplicate relations of the same type between same documents
            $table->unique(
                ['source_document_id', 'target_document_id', 'relation_type'],
                'unique_document_relation'
            );

            $table->index('source_document_id');
            $table->index('target_document_id');
            $table->index('relation_type');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('document_relations');
    }
};
