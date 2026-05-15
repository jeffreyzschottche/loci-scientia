<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('section_relations', function (Blueprint $table) {
            $table->id();
            $table->foreignId('source_section_id')->constrained('document_sections')->onDelete('cascade');
            $table->foreignId('target_section_id')->constrained('document_sections')->onDelete('cascade');
            $table->string('relation_type', 50)->default('references');
            $table->json('metadata')->nullable();
            $table->timestamps();

            $table->unique(['source_section_id', 'target_section_id', 'relation_type'], 'unique_section_relation');
            $table->index('source_section_id');
            $table->index('target_section_id');
            $table->index('relation_type');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('section_relations');
    }
};
