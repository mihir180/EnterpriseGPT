// Mirrors backend/app/schemas/* exactly (Phase 1 + Phase 2 contract).

export type UserRole = "admin" | "employee";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface Token {
  access_token: string;
  token_type: string;
}

export type DocumentStatus = "uploaded" | "processing" | "ready" | "failed";
export type DocumentType = "pdf" | "docx" | "txt" | "csv";

export interface DocumentRead {
  id: string;
  filename: string;
  file_type: DocumentType;
  file_size_bytes: number;
  status: DocumentStatus;
  status_message: string | null;
  page_count: number | null;
  chunk_count: number | null;
  uploaded_by: string;
  created_at: string;
  updated_at: string;
}

export interface DocumentUploadResponse {
  document: DocumentRead;
  message: string;
}

export interface DocumentListResponse {
  total: number;
  items: DocumentRead[];
}

export interface Citation {
  document_id: string;
  chunk_id: string;
  filename: string;
  page_number: number | null;
  score: number;
}

export interface AskRequest {
  question: string;
  top_k?: number | null;
  document_ids?: string[] | null;
}

export interface AskResponse {
  question: string;
  answer: string;
  sources: Citation[];
  context_used: boolean;
}

export interface ChatQueryRead {
  id: string;
  question: string;
  answer: string;
  sources: Citation[];
  context_used: boolean;
  created_at: string;
}

export interface ChatHistoryResponse {
  total: number;
  items: ChatQueryRead[];
}

// Frontend-only: a locally-rendered chat message (before/around persistence)
export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Citation[];
  contextUsed?: boolean;
  pending?: boolean;
  error?: boolean;
}

export interface ApiError {
  detail: string;
}
