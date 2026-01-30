<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('document_sections', function (Blueprint $table) {
            $table->id();
            $table->foreignId('document_id')->constrained()->onDelete('cascade');
            $table->string('title');
            $table->string('slug');
            $table->unsignedInteger('order_index')->default(0);
            $table->json('metadata')->nullable();
            $table->longText('text');
            $table->timestamps();

            $table->index(['document_id', 'order_index']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('document_sections');
    }
};
