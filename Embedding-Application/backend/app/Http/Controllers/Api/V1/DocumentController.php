<?php

namespace App\Http\Controllers\Api\V1;

use App\Http\Controllers\Controller;
use App\Models\Document;
use App\Services\EmbeddingService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Storage;

class DocumentController extends Controller
{
    public function __construct(
        private EmbeddingService $embeddingService
    ) {}

    /**
     * List all documents for the authenticated user.
     */
    public function index(Request $request): JsonResponse
    {
        $documents = Document::where('user_id', $request->user()->id)
            ->orderBy('created_at', 'desc')
            ->get();

        return response()->json(['documents' => $documents]);
    }

    /**
     * Upload a PDF document.
     */
    public function store(Request $request): JsonResponse
    {
        $request->validate([
            'file' => 'required|file|mimes:pdf|max:51200', // max 50MB
        ]);

        $file = $request->file('file');
        $filename = uniqid() . '_' . time() . '.pdf';
        Storage::putFileAs('documents', $file, $filename);

        $document = Document::create([
            'user_id' => $request->user()->id,
            'filename' => $filename,
            'original_filename' => $file->getClientOriginalName(),
            'mime_type' => $file->getMimeType(),
            'file_size' => $file->getSize(),
            'status' => 'uploaded',
        ]);

        return response()->json(['document' => $document], 201);
    }

    /**
     * Process (embed) a document.
     */
    public function process(Request $request, Document $document): JsonResponse
    {
        if ($document->user_id !== $request->user()->id) {
            return response()->json(['message' => 'Unauthorized'], 403);
        }

        if ($document->status === 'embedded') {
            return response()->json(['message' => 'Document already embedded']);
        }

        try {
            $this->embeddingService->processDocument($document);

            return response()->json([
                'message' => 'Document embedded successfully',
                'document' => $document->fresh(),
            ]);
        } catch (\Exception $e) {
            Log::error('Document embedding failed', [
                'document_id' => $document->id,
                'filename' => $document->filename,
                'message' => $e->getMessage(),
            ]);
            return response()->json([
                'message' => 'Embedding failed',
                'error' => $e->getMessage(),
            ], 500);
        }
    }

    /**
     * Delete a document and its embeddings.
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

        return response()->json(['message' => 'Document deleted']);
    }
}
