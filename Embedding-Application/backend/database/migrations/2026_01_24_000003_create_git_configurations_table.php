<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('git_configurations', function (Blueprint $table) {
            $table->id();
            $table->string('repo_url');
            $table->string('branch')->default('main');
            $table->string('access_token');
            $table->timestamp('last_pushed_at')->nullable();
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('git_configurations');
    }
};
