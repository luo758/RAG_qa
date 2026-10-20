export interface User {
  id: number
  username: string
  role: 'super_admin' | 'admin' | 'employee'
  created_at: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: User
}

export interface CaptchaResponse {
  captcha_id: string
  image_data: string
  expires_in: number
  debug_code?: string | null
}

export interface KnowledgeBase {
  id: number
  name: string
  description: string
  is_shared: boolean
  is_owner: boolean
  can_manage: boolean
  can_view: boolean
  can_upload: boolean
  created_at: string
  updated_at: string
}

export interface AdminUser extends User {
  is_active: boolean
}

export interface KnowledgePermission {
  user_id: number
  username: string
  can_view: boolean
  can_upload: boolean
}

export interface DocumentItem {
  id: number
  knowledge_base_id: number
  filename: string
  file_type: string
  status: string
  chunk_size: number
  overlap: number
  retrieval_mode: string
  char_count: number
  error_message?: string | null
  can_manage: boolean
  created_at: string
}

export interface Chunk {
  id: number
  document_id: number
  knowledge_base_id: number
  chunk_index: number
  content: string
  metadata_json: Record<string, unknown>
  updated_at: string
}

export interface DocumentDetail extends DocumentItem {
  chunks: Chunk[]
}

export interface ChatSession {
  id: number
  title: string
  model: string
  temperature: number
  top_p: number
  max_tokens: number
  history_turns: number
  created_at: string
  updated_at: string
}

export interface Citation {
  index: number
  chunk_id: number
  document_id: number
  document_name: string
  knowledge_base_id: number
  score: number
  snippet: string
}

export interface ChatMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  citations: Citation[]
  created_at: string
}

export interface ChatSettings {
  model: string
  temperature: number
  top_p: number
  max_tokens: number
  history_turns: number
}
