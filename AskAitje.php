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
 *   AITJE_BASE_URL   (standaard: http://aitje-2.local:8000)
 *   AITJE_ENDPOINT   (standaard: /api/v1/ask)
 */

$baseUrl = rtrim(getenv('AITJE_BASE_URL') ?: 'http://aitje-2.local:8000', '/');
$endpoint = getenv('AITJE_ENDPOINT') ?: '/api/v1/ask';
$url = $baseUrl . $endpoint;

if (!function_exists('readline')) {
    fwrite(STDERR, "readline()-functie ontbreekt. Draai dit script via de PHP-CLI.\n");
    exit(1);
}

echo "Standaard endpoint: {$url}\n";
$prompt = trim(readline("Wat wil je AITJE vragen? "));

if ($prompt === '') {
    fwrite(STDERR, "Geen vraag opgegeven. Stop.\n");
    exit(1);
}

if (!function_exists('curl_init')) {
    fwrite(STDERR, "cURL-extensie ontbreekt in PHP (installeer php-curl).\n");
    exit(1);
}

$payload = json_encode(['prompt' => $prompt], JSON_UNESCAPED_UNICODE);
$ch = curl_init($url);
curl_setopt_array($ch, [
    CURLOPT_POST => true,
    CURLOPT_HTTPHEADER => ['Content-Type: application/json'],
    CURLOPT_POSTFIELDS => $payload,
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_TIMEOUT => 30,
]);

$response = curl_exec($ch);
$error = curl_error($ch);
$status = curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
curl_close($ch);

if ($response === false) {
    fwrite(STDERR, "Fout bij verzoek: {$error}\n");
    exit(1);
}

if ($status >= 400) {
    fwrite(STDERR, "Server gaf status {$status}. Body:\n{$response}\n");
    exit(1);
}

$data = json_decode($response, true);
if ($data === null) {
    echo "Antwoord:\n{$response}\n";
    exit(0);
}

if (isset($data['message'])) {
    echo "AITJE zegt:\n{$data['message']}\n";
} else {
    echo "AITJE antwoord (JSON):\n" . json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE) . "\n";
}
