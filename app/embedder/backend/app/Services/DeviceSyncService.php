<?php

namespace App\Services;

use App\Models\Document;
use App\Models\User;
use Illuminate\Http\Client\PendingRequest;
use Illuminate\Support\Collection;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
use RuntimeException;
use ZipArchive;

/**
 * Push de kennisbank-export rechtstreeks over LAN naar de Aitje-device
 * (FastAPI op http://127.0.0.1:8000 standaard). Vervangt GitSyncService —
 * geen git, geen GitHub, geen access tokens meer in de DB.
 */
class DeviceSyncService
{
    public function __construct(
        private readonly JsonLdGenerator $jsonLdGenerator
    ) {}

    /**
     * Bundel + push de documenten van een gebruiker naar de device.
     */
    public function syncUser(User $user): array
    {
        $documents = $this->fetchDocuments($user);
        $bundlePath = $this->buildBundle($documents);

        try {
            $response = $this->httpClient()
                ->attach(
                    'bundle',
                    file_get_contents($bundlePath),
                    sprintf('kennisbank-%s.zip', now()->format('Ymd-His'))
                )
                ->post($this->endpoint());

            if ($response->failed()) {
                Log::error('Device push failed', [
                    'status' => $response->status(),
                    'body' => $response->body(),
                ]);
                throw new RuntimeException(sprintf(
                    'Device push faalde (HTTP %d): %s',
                    $response->status(),
                    $response->json('detail') ?? $response->body()
                ));
            }

            Log::info('Device push completed', $response->json() ?? []);

            return [
                'pushed' => true,
                'device_response' => $response->json(),
                'last_pushed_at' => now()->toIso8601String(),
            ];
        } finally {
            @unlink($bundlePath);
        }
    }

    /**
     * @return Collection<Document>
     */
    private function fetchDocuments(User $user): Collection
    {
        return Document::where('user_id', $user->id)
            ->where('status', 'formatted')
            ->with(['sections.chunks'])
            ->orderBy('position')
            ->get();
    }

    /**
     * Bouw een ZIP met de knowledge_base-export, exact dezelfde layout als
     * GitSyncService voorheen naar git pushte. Returns het pad naar het
     * tijdelijke ZIP-bestand; caller is verantwoordelijk voor opruimen.
     */
    public function buildBundle(Collection $documents): string
    {
        if (! class_exists(ZipArchive::class)) {
            throw new RuntimeException('PHP zip extension is required (php-zip).');
        }

        $files = $this->jsonLdGenerator->generateStructuredFileMap($documents);

        $tmp = tempnam(sys_get_temp_dir(), 'aitje-kb-');
        if ($tmp === false) {
            throw new RuntimeException('Kon geen tijdelijk bestand maken voor de bundle.');
        }
        // tempnam maakt een leeg bestand; ZipArchive wil zelf openen.
        @unlink($tmp);

        $zip = new ZipArchive();
        if ($zip->open($tmp, ZipArchive::CREATE | ZipArchive::OVERWRITE) !== true) {
            throw new RuntimeException("Kon ZIP niet openen op {$tmp}");
        }

        // Layout: alles onder knowledge_base/ zodat het device 1:1 matcht
        // met wat de oude git-bridge produceerde.
        foreach ($files as $relativePath => $payload) {
            $json = json_encode(
                $payload,
                JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES
            );
            if ($json === false) {
                $zip->close();
                @unlink($tmp);
                throw new RuntimeException("JSON-encoding mislukt voor {$relativePath}");
            }
            $zip->addFromString('knowledge_base/'.$relativePath, $json);
        }
        $zip->close();

        return $tmp;
    }

    private function endpoint(): string
    {
        $base = rtrim((string) config('aitje.device_base_url', 'http://127.0.0.1:8000'), '/');
        return $base.'/api/v1/kennisbank/import';
    }

    private function httpClient(): PendingRequest
    {
        $token = $this->resolveAdminToken();
        if ($token === '') {
            throw new RuntimeException(
                'Aitje admin token niet gevonden. Verwacht in '
                .config('aitje.admin_token_file')
                .' (wordt automatisch geschreven door FastAPI bij eerste start).'
            );
        }

        return Http::timeout((int) config('aitje.push_timeout_seconds', 600))
            ->withToken($token)
            ->acceptJson();
    }

    private function resolveAdminToken(): string
    {
        $path = (string) config('aitje.admin_token_file');
        if ($path === '' || ! is_readable($path)) {
            return '';
        }
        $raw = @file_get_contents($path);
        if ($raw === false) {
            return '';
        }
        $data = json_decode($raw, true);
        if (! is_array($data)) {
            return '';
        }
        return (string) ($data['token'] ?? '');
    }
}
