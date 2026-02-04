<?php

namespace App\Console\Commands;

use App\Services\KennisbankUserSynchronizer;
use Illuminate\Console\Command;

class SyncKennisbankUser extends Command
{
    protected $signature = 'kennisbank:sync-user';

    protected $description = 'Zorg dat de kennisbank-user uit de root .env in de database staat';

    public function handle(KennisbankUserSynchronizer $synchronizer): int
    {
        $synchronizer->sync();

        $this->info('Kennisbank user gesynchroniseerd.');

        return static::SUCCESS;
    }
}
