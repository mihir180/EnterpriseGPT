"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  UploadCloud,
  FileText,
  Trash2,
  CheckCircle2,
  Clock,
  AlertCircle,
  Loader2,
} from "lucide-react";
import ProtectedRoute from "@/components/ProtectedRoute";
import Navbar from "@/components/Navbar";
import { useAuth } from "@/lib/auth-context";
import { deleteDocument, listDocuments, uploadDocument, ApiRequestError } from "@/lib/api";
import type { DocumentRead } from "@/types";

const STATUS_META: Record<
  DocumentRead["status"],
  { label: string; className: string; icon: React.ElementType }
> = {
  ready: { label: "Ready", className: "text-emerald-700 bg-emerald-50", icon: CheckCircle2 },
  processing: { label: "Processing", className: "text-amber-700 bg-amber-50", icon: Loader2 },
  uploaded: { label: "Queued", className: "text-ink-500 dark:text-ink-100/50 bg-ink-50", icon: Clock },
  failed: { label: "Failed", className: "text-red-700 bg-red-50", icon: AlertCircle },
};

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function DocumentsContent() {
  const { isAdmin } = useAuth();
  const [documents, setDocuments] = useState<DocumentRead[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refresh = useCallback(async () => {
    const res = await listDocuments(0, 100);
    setDocuments(res.items);
    return res.items;
  }, []);

  useEffect(() => {
    (async () => {
      try {
        await refresh();
      } finally {
        setIsLoading(false);
      }
    })();
  }, [refresh]);

  // Poll while any document is still uploaded/processing, so status
  // updates without a manual refresh (Phase 1 pipeline runs in the
  // background; a websocket/push channel would replace this in Phase 5).
  useEffect(() => {
    const hasPending = documents.some(
      (d) => d.status === "uploaded" || d.status === "processing"
    );
    if (hasPending && !pollRef.current) {
      pollRef.current = setInterval(refresh, 3000);
    } else if (!hasPending && pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [documents, refresh]);

  async function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return;
    setError(null);
    setIsUploading(true);
    try {
      for (const file of Array.from(files)) {
        await uploadDocument(file);
      }
      await refresh();
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "Upload failed.");
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this document and its indexed content?")) return;
    await deleteDocument(id);
    await refresh();
  }

  return (
    <div className="flex-1 overflow-y-auto bg-paper dark:bg-ink-950 p-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-medium text-ink-900 dark:text-ink-50">Documents</h1>
          <p className="mt-1 text-sm text-ink-400 dark:text-ink-100/40">
            {isAdmin
              ? "Upload company documents to make them searchable."
              : "Documents available for Q&A across your organization."}
          </p>
        </div>
      </div>

      {isAdmin && (
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setIsDragging(false);
            handleFiles(e.dataTransfer.files);
          }}
          onClick={() => fileInputRef.current?.click()}
          className={`mb-6 flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 py-10 text-center transition-colors ${
            isDragging ? "border-brand-500 bg-brand-50" : "border-ink-100 dark:border-white/10 bg-paper-raised dark:bg-ink-800"
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.docx,.txt,.csv"
            className="hidden"
            onChange={(e) => handleFiles(e.target.files)}
          />
          <UploadCloud className="mb-2 text-brand-600" size={28} />
          <p className="text-sm font-medium text-ink-700 dark:text-ink-100/80">
            {isUploading ? "Uploading…" : "Drag & drop files, or click to browse"}
          </p>
          <p className="mt-1 text-xs text-ink-400 dark:text-ink-100/40">PDF, DOCX, TXT, CSV — up to 25 MB each</p>
        </div>
      )}

      {error && (
        <p className="mb-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>
      )}

      <div className="overflow-hidden rounded-2xl border border-ink-100 dark:border-white/10 bg-paper-raised dark:bg-ink-800">
        <table className="w-full text-sm">
          <thead className="border-b border-ink-100 dark:border-white/10 bg-paper dark:bg-ink-950 text-left text-xs uppercase tracking-wide text-ink-400 dark:text-ink-100/40">
            <tr>
              <th className="px-4 py-3 font-medium">Document</th>
              <th className="px-4 py-3 font-medium">Type</th>
              <th className="px-4 py-3 font-medium">Size</th>
              <th className="px-4 py-3 font-medium">Chunks</th>
              <th className="px-4 py-3 font-medium">Status</th>
              {isAdmin && <th className="px-4 py-3 font-medium text-right">Actions</th>}
            </tr>
          </thead>
          <tbody className="divide-y divide-ink-100/70">
            {isLoading ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-ink-400 dark:text-ink-100/40">
                  Loading documents…
                </td>
              </tr>
            ) : documents.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-ink-400 dark:text-ink-100/40">
                  No documents uploaded yet.
                </td>
              </tr>
            ) : (
              documents.map((doc) => {
                const meta = STATUS_META[doc.status];
                const Icon = meta.icon;
                return (
                  <tr key={doc.id} className="hover:bg-paper dark:hover:bg-ink-900">
                    <td className="flex items-center gap-2 px-4 py-3 text-ink-700 dark:text-ink-100/80">
                      <FileText size={15} className="shrink-0 text-ink-400 dark:text-ink-100/40" />
                      <span className="truncate">{doc.filename}</span>
                    </td>
                    <td className="px-4 py-3 uppercase text-ink-500 dark:text-ink-100/50">{doc.file_type}</td>
                    <td className="px-4 py-3 text-ink-500 dark:text-ink-100/50">{formatBytes(doc.file_size_bytes)}</td>
                    <td className="px-4 py-3 text-ink-500 dark:text-ink-100/50">{doc.chunk_count ?? "—"}</td>
                    <td className="px-4 py-3">
                      <span
                        title={doc.status_message ?? undefined}
                        className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${meta.className}`}
                      >
                        <Icon size={12} className={doc.status === "processing" ? "animate-spin" : ""} />
                        {meta.label}
                      </span>
                    </td>
                    {isAdmin && (
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={() => handleDelete(doc.id)}
                          className="rounded-lg p-1.5 text-ink-400 dark:text-ink-100/40 hover:bg-red-50 hover:text-red-600"
                          title="Delete document"
                        >
                          <Trash2 size={15} />
                        </button>
                      </td>
                    )}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function DocumentsPage() {
  return (
    <ProtectedRoute>
      <div className="flex h-screen">
        <Navbar />
        <DocumentsContent />
      </div>
    </ProtectedRoute>
  );
}
