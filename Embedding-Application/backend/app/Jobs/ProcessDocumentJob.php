<?php

namespace App\Jobs;

use App\Enums\ProcessingStage;
use App\Models\Document;
use App\Services\DocumentProcessingService;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\SerializesModels;
use Illuminate\Support\Facades\Log;

class ProcessDocumentJob implements ShouldQueue
{
    use Dispatchable, InteractsWithQueue, Queueable, SerializesModels;

    /**
     * The number of times the job may be attempted.
     */
    public int $tries = 3;

    /**
     * The maximum number of seconds the job can run.
     */
    public int $timeout = 600;

    /**
     * Create a new job instance.
     */
    public function __construct(
        public Document $document,
        public array $options = []
    ) {}

    /**
     * Execute the job.
     */
    public function handle(DocumentProcessingService $processingService): void
    {
        Log::info("Starting document processing job", [
            'document_id' => $this->document->id,
            'filename' => $this->document->original_filename,
        ]);

        // Mark as queued
        $this->document->update([
            'processing_stage' => ProcessingStage::QUEUED,
            'processing_progress' => 10,
        ]);

        // Process the document
        $processingService->process($this->document, $this->options);

        Log::info("Document processing job completed", [
            'document_id' => $this->document->id,
        ]);
    }

    /**
     * Handle a job failure.
     */
    public function failed(?\Throwable $exception): void
    {
        Log::error("Document processing job failed", [
            'document_id' => $this->document->id,
            'error' => $exception?->getMessage(),
        ]);

        $this->document->update([
            'status' => 'failed',
            'processing_stage' => ProcessingStage::FAILED,
            'processing_progress' => 0,
            'metadata' => array_merge($this->document->metadata ?? [], [
                'error' => $exception?->getMessage(),
                'failed_at' => now()->toIso8601String(),
            ]),
        ]);
    }

    /**
     * Get the tags that should be assigned to the job.
     */
    public function tags(): array
    {
        return [
            'document-processing',
            'document:' . $this->document->id,
        ];
    }
}
