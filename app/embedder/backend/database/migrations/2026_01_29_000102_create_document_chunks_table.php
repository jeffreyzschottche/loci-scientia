<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('document_chunks', function (Blueprint $table) {
            $table->id();
            $table->foreignId('document_id')->constrained()->onDelete('cascade');
            $table->foreignId('section_id')->nullable()->constrained('document_sections')->onDelete('cascade');
            $table->string('chunk_id')->unique();
            $table->unsignedInteger('chunk_index');
            $table->text('text');
            $table->unsignedInteger('token_count')->default(0);
            $table->string('content_hash', 80);
            $table->json('metadata')->nullable();
            $table->timestamps();

            $table->index(['document_id', 'chunk_index']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('document_chunks');
    }
};
