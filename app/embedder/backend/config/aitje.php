<?php

/**
 * Aitje device integration — vervangt de oude git-bridge.
 *
 * Bij elke boot seed't `lociscientia.sh` de relevante waarden in
 * app/embedder/backend/.env, zodat dezelfde Laravel-install meerdere
 * Aitje-devices kan bedienen door alleen .env te wisselen.
 */

return [
    /*
     * Publieke FastAPI base-URL van de Aitje device. Default is loopback
     * (embedder draait op hetzelfde device als de backend). Wijzig dit als
     * de embedder uiteindelijk naar een externe device pusht — dan moet de
     * AITJE_DEVICE_BASE_URL daadwerkelijk een mDNS- of IP-adres bevatten.
     */
    'device_base_url' => env('AITJE_DEVICE_BASE_URL', 'http://127.0.0.1:8000'),

    /*
     * Pad naar het admin-token JSON-bestand dat door FastAPI's
     * AdminTokenManager wordt geschreven (devices_db/admin_token.json).
     * Wordt door DeviceSyncService lazy ingelezen — werkt dus ook als
     * Laravel eerder start dan FastAPI bij de eerste boot.
     */
    'admin_token_file' => env(
        'AITJE_ADMIN_TOKEN_FILE',
        base_path('../../../devices_db/admin_token.json')
    ),

    /*
     * Timeout (seconden) voor de push-request. Grote kennisbanken kunnen
     * minuten kosten — fastembed CPU-inference + Qdrant upserts.
     */
    'push_timeout_seconds' => (int) env('AITJE_PUSH_TIMEOUT', 600),
];
