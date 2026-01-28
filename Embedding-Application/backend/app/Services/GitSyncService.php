<?php

namespace App\Services;

use App\Models\Embedding;
use App\Models\GitConfiguration;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Process;
use RuntimeException;

class GitSyncService
{
    private string $repoPath;
    private string $sqliteFile = 'kennisbank.db';

    public function __construct()
    {
        $this->repoPath = storage_path('app/git-repo');
    }

    /**
     * Export embeddings to SQLite, commit, and push to remote.
     */
    public function syncToGit(): array
    {
        $config = GitConfiguration::firstOrFail();

        $this->ensureRepoCloned($config);
        $this->exportToSqlite();
        $pushed = $this->commitAndPush($config);

        if ($pushed) {
            $config->update(['last_pushed_at' => now()]);
        }

        return [
            'pushed' => $pushed,
            'last_pushed_at' => $config->fresh()->last_pushed_at,
        ];
    }

    /**
     * Export all embeddings to a SQLite file in the git repo.
     */
    private function exportToSqlite(): void
    {
        $dbPath = "{$this->repoPath}/{$this->sqliteFile}";

        // Remove old file
        if (file_exists($dbPath)) {
            unlink($dbPath);
        }

        // Create SQLite database
        $pdo = new \PDO("sqlite:{$dbPath}");
        $pdo->setAttribute(\PDO::ATTR_ERRMODE, \PDO::ERRMODE_EXCEPTION);

        $pdo->exec("
            CREATE TABLE documents (
                id INTEGER PRIMARY KEY,
                original_filename TEXT NOT NULL,
                chunk_count INTEGER DEFAULT 0,
                created_at TEXT
            )
        ");

        $pdo->exec("
            CREATE TABLE embeddings (
                id INTEGER PRIMARY KEY,
                document_id INTEGER NOT NULL,
                chunk_index INTEGER NOT NULL,
                text_content TEXT NOT NULL,
                vector TEXT NOT NULL,
                FOREIGN KEY (document_id) REFERENCES documents(id)
            )
        ");

        // Export documents that have embeddings
        $documents = DB::table('documents')
            ->where('status', 'embedded')
            ->get();

        $docStmt = $pdo->prepare(
            "INSERT INTO documents (id, original_filename, chunk_count, created_at) VALUES (?, ?, ?, ?)"
        );

        $embStmt = $pdo->prepare(
            "INSERT INTO embeddings (id, document_id, chunk_index, text_content, vector) VALUES (?, ?, ?, ?, ?)"
        );

        $pdo->beginTransaction();

        foreach ($documents as $doc) {
            $docStmt->execute([
                $doc->id,
                $doc->original_filename,
                $doc->chunk_count,
                $doc->created_at,
            ]);

            $embeddings = DB::table('embeddings')
                ->where('document_id', $doc->id)
                ->orderBy('chunk_index')
                ->get();

            foreach ($embeddings as $emb) {
                $embStmt->execute([
                    $emb->id,
                    $emb->document_id,
                    $emb->chunk_index,
                    $emb->text_content,
                    $emb->vector, // Already JSON string from DB
                ]);
            }
        }

        $pdo->commit();
    }

    /**
     * Ensure the git repo is cloned locally.
     */
    private function ensureRepoCloned(GitConfiguration $config): void
    {
        if (!is_dir($this->repoPath)) {
            $url = $this->authenticatedUrl($config);
            $result = Process::run(
                "git clone --branch {$config->branch} {$url} {$this->repoPath}"
            );

            if ($result->failed()) {
                throw new RuntimeException("Git clone failed: " . $result->errorOutput());
            }
        } else {
            // Pull latest
            $result = Process::path($this->repoPath)->run("git pull origin {$config->branch}");
            if ($result->failed()) {
                throw new RuntimeException("Git pull failed: " . $result->errorOutput());
            }
        }
    }

    /**
     * Commit the SQLite file and push.
     */
    private function commitAndPush(GitConfiguration $config): bool
    {
        $result = Process::path($this->repoPath)->run("git status --porcelain");

        if (empty(trim($result->output()))) {
            return false; // Nothing to commit
        }

        Process::path($this->repoPath)->run("git add {$this->sqliteFile}");

        $message = "Update kennisbank embeddings - " . now()->format('Y-m-d H:i:s');
        Process::path($this->repoPath)->run("git commit -m \"{$message}\"");

        $url = $this->authenticatedUrl($config);
        $result = Process::path($this->repoPath)->run(
            "git push {$url} {$config->branch}"
        );

        if ($result->failed()) {
            throw new RuntimeException("Git push failed: " . $result->errorOutput());
        }

        return true;
    }

    /**
     * Build authenticated git URL with token.
     */
    private function authenticatedUrl(GitConfiguration $config): string
    {
        $parsed = parse_url($config->repo_url);
        return sprintf(
            '%s://%s@%s%s',
            $parsed['scheme'] ?? 'https',
            $config->access_token,
            $parsed['host'],
            $parsed['path']
        );
    }
}
