<?php

namespace App\Http\Controllers\Api\V1;

use App\Enums\ProcessingStage;
use App\Http\Controllers\Controller;
use App\Models\Document;
use App\Services\DocumentProcessingService;
use Carbon\Carbon;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;

class DocumentController extends Controller
{
    private const ALLOWED_MIMES = [
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/msword',
        'text/csv',
        'application/csv',
        'text/xml',
        'application/xml',
        'text/plain',
        'text/markdown',
    ];

    private const MAX_FILE_SIZE = 51200; // 50MB in KB

    public function __construct(
        private DocumentProcessingService $processingService
    ) {}

    /**
     * List all documents for the authenticated user.
     */
    public function index(Request $request): JsonResponse
    {
        $documents = Document::where('user_id', $request->user()->id)
            ->orderBy('position')
            ->orderBy('created_at', 'desc')
            ->get();

        return response()->json(['documents' => $documents]);
    }

    /**
     * Upload a document (multi-format support).
     */
    public function store(Request $request): JsonResponse
    {
        $request->validate([
            'file' => 'required|file|max:' . self::MAX_FILE_SIZE,
            'title' => 'nullable|string|max:255',
            'category' => 'nullable|string|max:100',
            'version_tag' => 'nullable|string|max:50',
            'content_date' => 'nullable|date',
            'language' => 'nullable|string|max:10',
            'description' => 'nullable|string|max:1000',
        ]);

        $file = $request->file('file');
        $mimeType = $file->getMimeType();

        // Validate mime type
        if (!in_array($mimeType, self::ALLOWED_MIMES)) {
            return response()->json([
                'message' => 'Bestandstype niet ondersteund',
                'allowed_types' => ['PDF', 'DOCX', 'CSV', 'XML', 'TXT', 'MD'],
            ], 422);
        }

        $extension = $file->getClientOriginalExtension();
        $filename = uniqid() . '_' . time() . '.' . $extension;
        Storage::putFileAs('documents', $file, $filename);

        $originalName = pathinfo($file->getClientOriginalName(), PATHINFO_FILENAME);
        $docId = Str::slug($request->input('title', $originalName));

        // Ensure unique doc_id
        $baseDocId = $docId;
        $counter = 1;
        while (Document::where('doc_id', $docId)->exists()) {
            $docId = $baseDocId . '-' . $counter++;
        }

        $contentDateInput = $request->input('content_date');
        $contentDate = $contentDateInput
            ? Carbon::parse($contentDateInput)->toDateString()
            : now()->toDateString();

        $document = Document::create([
            'user_id' => $request->user()->id,
            'doc_id' => $docId,
            'title' => $request->input('title', $originalName),
            'category' => $request->input('category'),
            'version_tag' => $request->input('version_tag'),
            'content_date' => $contentDate,
            'language' => $request->input('language'),
            'description' => $request->input('description'),
            'filename' => $filename,
            'original_filename' => $file->getClientOriginalName(),
            'mime_type' => $mimeType,
            'file_size' => $file->getSize(),
            'status' => 'uploaded',
            'processing_stage' => ProcessingStage::UPLOADED,
            'processing_progress' => 0,
        ]);

        // Check if mapping is required
        $requiresMapping = $this->processingService->requiresMapping($document);
        $mappableFields = $requiresMapping
            ? $this->processingService->getMappableFields($document)
            : [];

        return response()->json([
            'document' => $document,
            'requires_mapping' => $requiresMapping,
            'mappable_fields' => $mappableFields,
        ], 201);
    }

    /**
     * Get document details.
     */
    public function show(Request $request, Document $document): JsonResponse
    {
        if ($document->user_id !== $request->user()->id) {
            return response()->json(['message' => 'Unauthorized'], 403);
        }

        $document->load(['sections.chunks']);

        return response()->json(['document' => $document]);
    }

    /**
     * Update document metadata.
     */
    public function update(Request $request, Document $document): JsonResponse
    {
        if ($document->user_id !== $request->user()->id) {
            return response()->json(['message' => 'Unauthorized'], 403);
        }

        $request->validate([
            'title' => 'nullable|string|max:255',
            'category' => 'nullable|string|max:100',
            'version_tag' => 'nullable|string|max:50',
            'content_date' => 'nullable|date',
            'language' => 'nullable|string|max:10',
            'description' => 'nullable|string|max:1000',
        ]);

        $updates = $request->only(['title', 'category', 'version_tag', 'language', 'description']);

        if ($request->filled('content_date')) {
            $updates['content_date'] = Carbon::parse($request->input('content_date'))->toDateString();
        }

        $document->update($updates);

        return response()->json(['document' => $document->fresh()]);
    }

    /**
     * Save column/field mapping for CSV/XML.
     */
    public function saveMapping(Request $request, Document $document): JsonResponse
    {
        if ($document->user_id !== $request->user()->id) {
            return response()->json(['message' => 'Unauthorized'], 403);
        }

        $request->validate([
            'mapping' => 'required|array',
        ]);

        $document->update([
            'metadata' => array_merge($document->metadata ?? [], [
                'mapping' => $request->input('mapping'),
            ]),
        ]);

        return response()->json(['document' => $document->fresh()]);
    }

    /**
     * Start processing a document.
     */
    public function process(Request $request, Document $document): JsonResponse
    {
        if ($document->user_id !== $request->user()->id) {
            return response()->json(['message' => 'Unauthorized'], 403);
        }

        if ($document->status === 'formatted') {
            return response()->json(['message' => 'Document is al verwerkt']);
        }

        if ($document->isProcessing()) {
            return response()->json(['message' => 'Document wordt al verwerkt']);
        }

        // Get mapping options if present
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
            // Process synchronously (no queue worker needed)
            $this->processingService->process($document, $options);

            return response()->json([
                'message' => 'Document succesvol verwerkt',
                'document' => $document->fresh(),
            ]);
        } catch (\Throwable $e) {
            return response()->json([
                'message' => 'Verwerking mislukt',
                'error' => $e->getMessage(),
            ], 500);
        }
    }

    /**
     * Get processing status.
     */
    public function status(Request $request, Document $document): JsonResponse
    {
        if ($document->user_id !== $request->user()->id) {
            return response()->json(['message' => 'Unauthorized'], 403);
        }

        return response()->json([
            'status' => $document->status,
            'processing_stage' => $document->processing_stage?->value,
            'processing_stage_label' => $document->processing_stage?->label(),
            'processing_progress' => $document->processing_progress,
            'is_processing' => $document->isProcessing(),
            'is_ready' => $document->isReady(),
            'has_failed' => $document->hasFailed(),
            'error' => $document->metadata['error'] ?? null,
        ]);
    }

    /**
     * Delete a document.
     */
    public function destroy(Request $request, Document $document): JsonResponse
    {
        if ($document->user_id !== $request->user()->id) {
            return response()->json(['message' => 'Unauthorized'], 403);
        }

        $relativePath = "documents/{$document->filename}";
        if (Storage::exists($relativePath)) {
            Storage::delete($relativePath);
        }

        $document->delete();

        return response()->json(['message' => 'Document verwijderd']);
    }
}
