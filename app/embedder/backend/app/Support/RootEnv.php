<?php

namespace App\Support;

use Dotenv\Dotenv;

class RootEnv
{
    private static ?array $values = null;

    public static function get(string $key, $default = null): mixed
    {
        if (array_key_exists($key, $_ENV)) {
            return $_ENV[$key];
        }

        if (array_key_exists($key, $_SERVER)) {
            return $_SERVER[$key];
        }

        if (self::$values === null) {
            self::$values = self::loadRootEnv();
        }

        return self::$values[$key] ?? $default;
    }

    private static function loadRootEnv(): array
    {
        $rootPath = base_path('../..');
        $envFile = $rootPath.DIRECTORY_SEPARATOR.'.env';

        if (! file_exists($envFile)) {
            return [];
        }

        $dotEnv = Dotenv::createArrayBacked($rootPath);

        return $dotEnv->load();
    }
}
