<?php

namespace App\Services;

use App\Models\Document;
use App\Models\GitConfiguration;
use App\Models\User;
use Illuminate\Support\Collection;
use Illuminate\Support\Facades\File;
use Illuminate\Support\Facades\Process;
use Illuminate\Support\Str;
use RuntimeException;

class GitSyncService
{
    private string $basePath;

    private string $exportRoot = 'knowledge_base';

    public function __construct(
        private readonly JsonLdGenerator $jsonLdGenerator
    ) {
        $this->basePath = storage_path('app/git-repos');
        if (! is_dir($this->basePath)) {
            mkdir($this->basePath, 0755, true);
        }
    }

    /**
     * Sync the authenticated user's knowledge base to their configured Git repo.
     */
    public function syncUser(User $user): array
    {
        $config = GitConfiguration::where('user_id', $user->id)->firstOrFail();
        $repoPath = $this->repoPathFor($user->id, $config->repo_url);

        $this->ensureRepoCloned($config, $repoPath);
        $this->ensureRepoIdentity($repoPath);

        $documents = $this->fetchDocuments($user);
        $this->exportStructuredFiles($documents, $repoPath);

        $pushed = $this->commitAndPush($config, $repoPath);

        if ($pushed) {
            $config->update(['last_pushed_at' => now()]);
        }

        return [
            'pushed' => $pushed,
            'last_pushed_at' => $config->fresh()->last_pushed_at,
        ];
    }

    private function fetchDocuments(User $user): Collection
    {
        return Document::where('user_id', $user->id)
            ->where('status', 'formatted')
            ->with([
                'sections.chunks',
            ])
            ->orderBy('position')
            ->get();
    }

    private function exportStructuredFiles(Collection $documents, string $repoPath): void
    {
        $files = $this->jsonLdGenerator->generateStructuredFileMap($documents);
        $exportPath = $repoPath.DIRECTORY_SEPARATOR.$this->exportRoot;

        if (is_dir($exportPath)) {
            File::cleanDirectory($exportPath);
        } else {
            mkdir($exportPath, 0755, true);
        }

        foreach ($files as $relativePath => $payload) {
            $absolutePath = $exportPath.DIRECTORY_SEPARATOR.$relativePath;
            $directory = dirname($absolutePath);
            if (! is_dir($directory)) {
                mkdir($directory, 0755, true);
            }

            file_put_contents(
                $absolutePath,
                json_encode($payload, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE)
            );
        }
    }

    private function ensureRepoCloned(GitConfiguration $config, string $repoPath): void
    {
        if (! is_dir($repoPath)) {
            $url = $this->authenticatedUrl($config);
            $result = Process::run(
                sprintf(
                    'git clone --branch %s %s %s',
                    escapeshellarg($config->branch),
                    escapeshellarg($url),
                    escapeshellarg($repoPath)
                )
            );

            if ($result->failed()) {
                throw new RuntimeException('Git clone failed: '.$result->errorOutput());
            }
        } else {
            $result = Process::path($repoPath)->run(
                sprintf('git pull origin %s', escapeshellarg($config->branch))
            );
            if ($result->failed()) {
                throw new RuntimeException('Git pull failed: '.$result->errorOutput());
            }
        }
    }

    private function commitAndPush(GitConfiguration $config, string $repoPath): bool
    {
        $status = Process::path($repoPath)->run('git status --porcelain');

        if (empty(trim($status->output()))) {
            return false;
        }

        Process::path($repoPath)->run(
            sprintf('git add %s', escapeshellarg($this->exportRoot))
        );

        $message = 'Sync knowledge base export - '.now()->format('Y-m-d H:i:s');
        Process::path($repoPath)->run(
            sprintf('git commit -m %s', escapeshellarg($message))
        );

        $url = $this->authenticatedUrl($config);
        $result = Process::path($repoPath)->run(
            sprintf('git push %s %s', escapeshellarg($url), escapeshellarg($config->branch))
        );

        if ($result->failed()) {
            throw new RuntimeException('Git push failed: '.$result->errorOutput());
        }

        return true;
    }

    private function ensureRepoIdentity(string $repoPath): void
    {
        $email = config('knowledgebase.user.email') ?: 'kennisbank@localhost';
        $name = 'Kennisbank Sync';

        Process::path($repoPath)->run(
            sprintf('git config user.name %s', escapeshellarg($name))
        );

        Process::path($repoPath)->run(
            sprintf('git config user.email %s', escapeshellarg($email))
        );
    }

    private function authenticatedUrl(GitConfiguration $config): string
    {
        $parsed = parse_url($config->repo_url);

        $scheme = $parsed['scheme'] ?? 'https';
        $host = $parsed['host'] ?? '';
        $path = $parsed['path'] ?? '';
        $port = isset($parsed['port']) ? ':'.$parsed['port'] : '';
        $token = rawurlencode($config->access_token);

        return sprintf('%s://%s@%s%s%s', $scheme, $token, $host, $port, $path);
    }

    private function repoPathFor(int $userId, string $repoUrl): string
    {
        $slug = Str::slug(parse_url($repoUrl, PHP_URL_HOST) ?? 'repo');
        return $this->basePath.DIRECTORY_SEPARATOR."user-{$userId}-{$slug}";
    }
}
