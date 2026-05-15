<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * De git-bridge is verdwenen — de embedder pusht nu rechtstreeks over
     * LAN naar de Aitje-device (zie App\Services\DeviceSyncService). De
     * git_configurations tabel + bijbehorende access tokens zijn dus
     * obsoleet. We droppen de tabel volledig; mocht iemand alsnog rollback
     * willen, dan herstelt down() de structuur in de oude vorm.
     */
    public function up(): void
    {
        Schema::dropIfExists('git_configurations');
    }

    public function down(): void
    {
        Schema::create('git_configurations', function (Blueprint $table) {
            $table->id();
            $table->foreignId('user_id')->constrained()->cascadeOnDelete();
            $table->string('repo_url');
            $table->string('branch')->default('main');
            $table->text('access_token');
            $table->timestamp('last_pushed_at')->nullable();
            $table->timestamps();
            $table->unique('user_id');
        });
    }
};
