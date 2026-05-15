// Processing stages
export type ProcessingStage =
  | 'uploaded'
  | 'queued'
  | 'parsing'
  | 'chunking'
  | 'generating_jsonld'
  | 'ready'
  | 'failed';

// Document
export interface Document {
  id: number;
  user_id: number;
  position: number;
  priority: number;
  doc_id: string;
  title: string;
  category: string | null;
  version_tag: string | null;
  source_url: string | null;
  description: string | null;
  filename: string;
  original_filename: string;
  mime_type: string;
  file_size: number;
  status: 'uploaded' | 'processing' | 'formatted' | 'failed';
  chunk_count: number;
  parsed_at: string | null;
  metadata: Record<string, any> | null;
  json_ld: Record<string, any> | null;
  processing_stage: ProcessingStage | null;
  processing_progress: number;
  created_at: string;
  updated_at: string;
  sections?: DocumentSection[];
}

// Section
export interface DocumentSection {
  id: number;
  document_id: number;
  title: string;
  slug: string;
  order_index: number;
  text: string;
  metadata: Record<string, any> | null;
  created_at: string;
  updated_at: string;
  chunks?: DocumentChunk[];
}

// Chunk
export interface DocumentChunk {
  id: number;
  document_id: number;
  section_id: number | null;
  chunk_id: string;
  chunk_index: number;
  text: string;
  token_count: number;
  content_hash: string;
  metadata: Record<string, any> | null;
  created_at: string;
  updated_at: string;
}

// Priority management
export interface PriorityCategoriesResponse {
  categories: Record<string, Document[]>;
}

export interface PriorityUpdate {
  id: number;
  priority: number;
}

// Tree node (for library view)
export interface TreeNode {
  id: number;
  doc_id?: string;
  title: string;
  slug?: string;
  category?: string | null;
  status?: string;
  position?: number;
  type: 'document' | 'section';
  document_id?: number;
  children?: TreeNode[];
}

// Stats
export interface KennisbankStats {
  total_documents: number;
  processed_documents: number;
  failed_documents: number;
  processing_documents: number;
  total_sections: number;
  total_chunks: number;
  estimated_words: number;
}

// Export
export interface Export {
  id: number;
  version: string;
  document_count: number;
  chunk_count: number;
  metadata: Record<string, any>;
  created_at: string;
}

// API Responses
export interface DocumentsResponse {
  documents: Document[];
}

export interface DocumentResponse {
  document: Document;
  requires_mapping?: boolean;
  mappable_fields?: Record<string, string>;
  json_ld?: Record<string, any>;
  message?: string;
}

export interface TreeResponse {
  tree: TreeNode[];
}

export interface SectionResponse {
  section: DocumentSection;
  json_ld: Record<string, any>;
}

export interface StatsResponse {
  stats: KennisbankStats;
  categories: Record<string, number>;
  recent_documents: Document[];
}

export interface StatusResponse {
  status: string;
  processing_stage: ProcessingStage | null;
  processing_stage_label: string | null;
  processing_progress: number;
  is_processing: boolean;
  is_ready: boolean;
  has_failed: boolean;
  error: string | null;
}

export interface ExportsResponse {
  exports: Export[];
}

export interface CategoriesResponse {
  categories: Array<{
    category: string;
    document_count: number;
    section_count: number;
    chunk_count: number;
  }>;
}
