export interface Document {
  id: number
  user_id: number
  filename: string
  original_filename: string
  mime_type: string
  file_size: number
  status: 'uploaded' | 'processing' | 'embedded' | 'failed'
  chunk_count: number
  created_at: string
  updated_at: string
}

export interface DocumentsResponse {
  documents: Document[]
}

export interface DocumentResponse {
  document: Document
  message?: string
}

export interface GitConfig {
  id: number
  repo_url: string
  branch: string
  last_pushed_at: string | null
}

export interface GitConfigResponse {
  config: GitConfig | null
}
