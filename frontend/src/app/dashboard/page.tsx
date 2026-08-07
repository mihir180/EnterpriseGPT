"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { FileText, MessageSquare, CheckCircle2, Clock, AlertCircle } from "lucide-react";
import ProtectedRoute from "@/components/ProtectedRoute";
import Navbar from "@/components/Navbar";
import { getChatHistory, listDocuments } from "@/lib/api";
import type { ChatQueryRead, DocumentRead } from "@/types";
import { useAuth } from "@/lib/auth-context";

function StatCard({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: number | string;
  icon: React.ElementType;
}) {
  return (
    <div className="rounded-2xl border border-ink-100 dark:border-white/10 bg-paper-raised dark:bg-ink-800 p-4">
      <div className="mb-2 flex items-center gap-2 text-ink-400 dark:text-ink-100/40">
        <Icon size={16} />
        <span className="text-xs font-medium uppercase tracking-wide">{label}</span>
      </div>
      <p className="text-2xl font-semibold text-ink-900 dark:text-ink-50">{value}</p>
    </div>
  );
}

const STATUS_STYLES: Record<DocumentRead["status"], string> = {
  ready: "text-emerald-700 bg-emerald-50",
  processing: "text-amber-700 bg-amber-50",
  uploaded: "text-ink-500 dark:text-ink-100/50 bg-ink-50",
  failed: "text-red-700 bg-red-50",
};

function DashboardContent() {
  const { user } = useAuth();
  const [documents, setDocuments] = useState<DocumentRead[]>([]);
  const [totalDocs, setTotalDocs] = useState(0);
  const [chatHistory, setChatHistory] = useState<ChatQueryRead[]>([]);
  const [totalChats, setTotalChats] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const [docsRes, chatRes] = await Promise.all([
          listDocuments(0, 5),
          getChatHistory(0, 5),
        ]);
        setDocuments(docsRes.items);
        setTotalDocs(docsRes.total);
        setChatHistory(chatRes.items);
        setTotalChats(chatRes.total);
      } finally {
        setIsLoading(false);
      }
    })();
  }, []);

  const readyCount = documents.filter((d) => d.status === "ready").length;

  return (
    <div className="flex-1 overflow-y-auto bg-paper dark:bg-ink-950 p-8">
      <h1 className="font-display text-2xl font-medium text-ink-900 dark:text-ink-50">
        Welcome back, {user?.full_name?.split(" ")[0]}
      </h1>
      <p className="mt-1 text-sm text-ink-400 dark:text-ink-100/40">
        Here&apos;s what&apos;s happening across your knowledge base.
      </p>

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard label="Documents" value={totalDocs} icon={FileText} />
        <StatCard label="Questions asked" value={totalChats} icon={MessageSquare} />
        <StatCard label="Ready to search" value={readyCount} icon={CheckCircle2} />
      </div>

      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-2xl border border-ink-100 dark:border-white/10 bg-paper-raised dark:bg-ink-800 p-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-ink-800 dark:text-ink-50">Recent documents</h2>
            <Link href="/documents" className="text-xs font-medium text-brand-600 hover:underline">
              View all
            </Link>
          </div>
          {isLoading ? (
            <p className="text-sm text-ink-400 dark:text-ink-100/40">Loading…</p>
          ) : documents.length === 0 ? (
            <p className="text-sm text-ink-400 dark:text-ink-100/40">No documents uploaded yet.</p>
          ) : (
            <ul className="space-y-2">
              {documents.map((doc) => (
                <li key={doc.id} className="flex items-center justify-between gap-3 text-sm">
                  <span className="truncate text-ink-700 dark:text-ink-100/80">{doc.filename}</span>
                  <span
                    className={`flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[doc.status]}`}
                  >
                    {doc.status === "processing" && <Clock size={12} />}
                    {doc.status === "failed" && <AlertCircle size={12} />}
                    {doc.status === "ready" && <CheckCircle2 size={12} />}
                    {doc.status}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="rounded-2xl border border-ink-100 dark:border-white/10 bg-paper-raised dark:bg-ink-800 p-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-ink-800 dark:text-ink-50">Recent questions</h2>
            <Link href="/chat" className="text-xs font-medium text-brand-600 hover:underline">
              Ask something
            </Link>
          </div>
          {isLoading ? (
            <p className="text-sm text-ink-400 dark:text-ink-100/40">Loading…</p>
          ) : chatHistory.length === 0 ? (
            <p className="text-sm text-ink-400 dark:text-ink-100/40">No questions asked yet.</p>
          ) : (
            <ul className="space-y-3">
              {chatHistory.map((item) => (
                <li key={item.id} className="text-sm">
                  <p className="truncate font-medium text-ink-700 dark:text-ink-100/80">{item.question}</p>
                  <p className="mt-0.5 line-clamp-1 text-xs text-ink-400 dark:text-ink-100/40">{item.answer}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <div className="flex h-screen">
        <Navbar />
        <DashboardContent />
      </div>
    </ProtectedRoute>
  );
}
