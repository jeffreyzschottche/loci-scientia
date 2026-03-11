<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::dropIfExists('embeddings');
    }

    public function down(): void
    {
        Schema::create('embeddings', function (Blueprint $table) {
            $table->id();
            $table->foreignId('document_id')->constrained()->onDelete('cascade');
            $table->unsignedInteger('chunk_index');
            $table->text('text_content');
            $table->json('vector');
            $table->timestamps();

            $table->index(['document_id', 'chunk_index']);
        });
    }
};
