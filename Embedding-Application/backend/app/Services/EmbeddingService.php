<?php

namespace App\Services;

use App\Models\Document;
use App\Models\Embedding;
use Illuminate\Support\Facades\Process;
use Illuminate\Support\Facades\Storage;
use RuntimeException;

class EmbeddingService
{
    /**
     * Process a PDF: extract text, chunk, and embed via Python script.
     */
    public function processDocument(Document $document): void
    {
        $document->update(['status' => 'processing']);

        $relativePath = "documents/{$document->filename}";

        if (!Storage::exists($relativePath)) {
            $document->update(['status' => 'failed']);
            throw new RuntimeException("Stored PDF ontbreekt op schijf ({$relativePath}). Upload het document opnieuw.");
        }

        $pdfPath = Storage::path($relativePath);
        $scriptPath = base_path('scripts/embed_pdf.py');

        $result = Process::timeout(300)->run(
            "python3 {$scriptPath} {$pdfPath}"
        );

        if ($result->failed()) {
            $document->update(['status' => 'failed']);
            throw new RuntimeException("Embedding failed: " . $result->errorOutput());
        }

        $output = json_decode($result->output(), true);

        if (!is_array($output) || isset($output['error'])) {
            $document->update(['status' => 'failed']);
            throw new RuntimeException("Embedding error: " . ($output['error'] ?? 'Invalid output'));
        }

        // Store embeddings
        foreach ($output as $item) {
            Embedding::create([
                'document_id' => $document->id,
                'chunk_index' => $item['chunk_index'],
                'text_content' => $item['text'],
                'vector' => $item['vector'],
            ]);
        }

        $document->update([
            'status' => 'embedded',
            'chunk_count' => count($output),
        ]);
    }
}
