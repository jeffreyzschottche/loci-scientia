<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('exports', function (Blueprint $table) {
            $table->id();
            $table->string('version');
            $table->unsignedInteger('document_count');
            $table->unsignedInteger('chunk_count');
            $table->json('metadata')->nullable();
            $table->timestamps();

            $table->unique('version');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('exports');
    }
};
