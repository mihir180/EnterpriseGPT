import type {
  AskRequest,
  AskResponse,
  ChatHistoryResponse,
  DocumentListResponse,
  DocumentUploadResponse,
  Token,
  User,
} from "@/types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const TOKEN_KEY = "enterprisegpt_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  window.localStorage.removeItem(TOKEN_KEY);
}

export class ApiRequestError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiRequestError";
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  { auth = true }: { auth?: boolean } = {}
): Promise<T> {
  const headers = new Headers(options.headers);
  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (auth) {
    const token = getToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
  }

  const res = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      // ignore — no JSON body
    }
    if (res.status === 401 && auth) {
      clearToken();
    }
    throw new ApiRequestError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

// ---- Auth ----

export async function registerUser(payload: {
  email: string;
  password: string;
  full_name: string;
}): Promise<User> {
  return request<User>(
    "/api/v1/auth/register",
    { method: "POST", body: JSON.stringify(payload) },
    { auth: false }
  );
}

export async function login(email: string, password: string): Promise<Token> {
  // Backend uses OAuth2PasswordRequestForm -> x-www-form-urlencoded, "username" field.
  const form = new URLSearchParams();
  form.set("username", email);
  form.set("password", password);

  return request<Token>(
    "/api/v1/auth/login",
    {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: form.toString(),
    },
    { auth: false }
  );
}

export async function getCurrentUser(): Promise<User> {
  return request<User>("/api/v1/auth/me");
}

// ---- Documents ----

export async function uploadDocument(file: File): Promise<DocumentUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return request<DocumentUploadResponse>("/api/v1/documents/upload", {
    method: "POST",
    body: formData,
  });
}

export async function listDocuments(
  offset = 0,
  limit = 50
): Promise<DocumentListResponse> {
  return request<DocumentListResponse>(
    `/api/v1/documents?offset=${offset}&limit=${limit}`
  );
}

export async function getDocument(id: string) {
  return request(`/api/v1/documents/${id}`);
}

export async function deleteDocument(id: string): Promise<void> {
  await request<void>(`/api/v1/documents/${id}`, { method: "DELETE" });
}

// ---- Chat ----

export async function askQuestion(payload: AskRequest): Promise<AskResponse> {
  return request<AskResponse>("/api/v1/chat/ask", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getChatHistory(
  offset = 0,
  limit = 50
): Promise<ChatHistoryResponse> {
  return request<ChatHistoryResponse>(
    `/api/v1/chat/history?offset=${offset}&limit=${limit}`
  );
}
