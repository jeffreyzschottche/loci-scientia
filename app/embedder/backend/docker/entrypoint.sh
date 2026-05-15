#!/usr/bin/env sh
set -e

mkdir -p storage/framework/cache/data storage/framework/sessions storage/framework/views storage/logs bootstrap/cache

if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
  php artisan migrate --force
fi

if [ "${CACHE_CONFIG:-true}" = "true" ]; then
  php artisan config:cache
fi

exec "$@"
