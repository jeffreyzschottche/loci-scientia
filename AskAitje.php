<?php
/**
 * AskAitje.php
 *
 * Eenvoudige CLI-helper om vragen naar een lokale AITJE te sturen.
 *
 * Gebruik:
 *   php AskAitje.php
 *
 * Optionele env-variabelen:
 *   AITJE_BASE_URL       (standaard: http://aitje-2.local:8000)
 *   AITJE_ENDPOINT       (standaard: /api/v1/ask)
 *   AITJE_SIGNON_ENDPOINT (standaard: /api/v1/signon)
 *   AITJE_USERNAME, AITJE_PASSWORD om interactief invullen over te slaan.
 */

$baseUrl = rtrim(getenv('AITJE_BASE_URL') ?: 'http://aitje-2.local:8000', '/');
$endpoint = getenv('AITJE_ENDPOINT') ?: '/api/v1/ask';
$signonEndpoint = getenv('AITJE_SIGNON_ENDPOINT') ?: '/api/v1/signon';
$url = $baseUrl . $endpoint;
$signonUrl = $baseUrl . $signonEndpoint;

if (!function_exists('readline')) {
    fwrite(STDERR, "readline()-functie ontbreekt. Draai dit script via de PHP-CLI.\n");
    exit(1);
}

echo "Sign-on endpoint: {$signonUrl}\n";
echo "Ask endpoint: {$url}\n";
echo "[1] Sign-on (token ophalen)\n";
echo "[2] Ask (vraag stellen met bestaande token)\n";
$mode = trim(readline("Kies modus (1/2): "));

if (!in_array($mode, ['1', '2'], true)) {
    fwrite(STDERR, "Ongeldige keuze. Gebruik 1 of 2.\n");
    exit(1);
}

if (!function_exists('curl_init')) {
    fwrite(STDERR, "cURL-extensie ontbreekt in PHP (installeer php-curl).\n");
    exit(1);
}

function aitje_api_post(string $url, array $payload, array $headers = []): array {
    $body = json_encode($payload, JSON_UNESCAPED_UNICODE);
    $ch = curl_init($url);
    $defaultHeaders = ['Content-Type: application/json'];
    $headers = array_merge($defaultHeaders, $headers);
    curl_setopt_array($ch, [
        CURLOPT_POST => true,
        CURLOPT_HTTPHEADER => $headers,
        CURLOPT_POSTFIELDS => $body,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT => 30,
    ]);

    $response = curl_exec($ch);
    $error = curl_error($ch);
    $status = curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
    curl_close($ch);

    if ($response === false) {
        throw new RuntimeException("Fout bij verzoek: {$error}");
    }
    if ($status >= 400) {
        throw new RuntimeException("Server gaf status {$status}. Body:\n{$response}");
    }
    $data = json_decode($response, true);
    if ($data === null) {
        throw new RuntimeException("Kon JSON niet ontleden:\n{$response}");
    }
    return $data;
}

if ($mode === '1') {
    $username = getenv('AITJE_USERNAME') ?: trim(readline("Gebruikersnaam: "));
    $passwordEnv = getenv('AITJE_PASSWORD');
    if ($passwordEnv !== false && $passwordEnv !== '') {
        $password = $passwordEnv;
    } else {
        $password = trim(readline("Wachtwoord: "));
    }

    if ($username === '' || $password === '') {
        fwrite(STDERR, "Gebruikersnaam en wachtwoord zijn verplicht.\n");
        exit(1);
    }

    try {
        $signonData = aitje_api_post($signonUrl, [
            'user_name' => $username,
            'password' => $password,
        ]);
    } catch (RuntimeException $e) {
        fwrite(STDERR, "Sign-on mislukt:\n{$e->getMessage()}\n");
        exit(1);
    }

    if (!isset($signonData['token'])) {
        fwrite(STDERR, "Sign-on antwoord bevatte geen token.\n");
        exit(1);
    }

    $token = $signonData['token'];
    $expiresAt = $signonData['expires_at'] ?? 'onbekend';
    fwrite(STDERR, "Bearer token (geldig tot {$expiresAt}):\n");
    echo $token . "\n";
    exit(0);
}

$token = getenv('AITJE_BEARER_TOKEN') ?: trim(readline("Bearer token: "));
if ($token === '') {
    fwrite(STDERR, "Bearer token is verplicht in modus 'Ask'.\n");
    exit(1);
}

do {
    $prompt = trim(readline("Wat wil je AITJE vragen? "));
    if ($prompt === '') {
        echo "Voer een vraag in om verder te gaan.\n";
    }
} while ($prompt === '');

try {
    $askData = aitje_api_post(
        $url,
        ['prompt' => $prompt],
        ["Authorization: Bearer {$token}"]
    );
} catch (RuntimeException $e) {
    fwrite(STDERR, "Vraag versturen mislukt:\n{$e->getMessage()}\n");
    exit(1);
}

if (isset($askData['message'])) {
    echo "AITJE zegt:\n{$askData['message']}\n";
} else {
    echo "AITJE antwoord (JSON):\n" . json_encode($askData, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE) . "\n";
}
