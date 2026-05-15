<?php

namespace App\Console\Commands;

use App\Enums\ProcessingStage;
use App\Models\Document;
use App\Services\DocumentProcessingService;
use Illuminate\Console\Command;

class ReprocessDocuments extends Command
{
    protected $signature = 'documents:reprocess
        {document? : Document numeric ID or doc_id slug}
        {--all : Reprocess all formatted documents}';

    protected $description = 'Re-run the document processing pipeline to regenerate sections, chunks, and JSON-LD.';

    public function handle(DocumentProcessingService $processingService): int
    {
        $documentArg = $this->argument('document');
        $reprocessAll = (bool) $this->option('all');

        if (! $documentArg && ! $reprocessAll) {
            $this->error('Specify a document ID/doc_id or use --all.');

            return self::INVALID;
        }

        $documentsQuery = Document::query();

        if ($documentArg) {
            $documentsQuery->where('id', $documentArg)
                ->orWhere('doc_id', $documentArg);
        } else {
            $documentsQuery->where('status', 'formatted');
        }

        $documents = $documentsQuery->get();

        if ($documents->isEmpty()) {
            $this->warn('No matching documents found.');

            return self::SUCCESS;
        }

        foreach ($documents as $document) {
            $this->line(sprintf(
                'Reprocessing document #%d (%s)',
                $document->id,
                $document->title ?? $document->original_filename
            ));

            $options = [];
            if (isset($document->metadata['mapping'])) {
                $options['mapping'] = $document->metadata['mapping'];
            }

            $document->update([
                'status' => 'processing',
                'processing_stage' => ProcessingStage::QUEUED,
                'processing_progress' => 5,
            ]);

            try {
                $processingService->process($document->fresh(), $options);
                $this->info('✓ Completed');
            } catch (\Throwable $e) {
                $this->error('✗ Failed: ' . $e->getMessage());
            }
        }

        return self::SUCCESS;
    }
}
