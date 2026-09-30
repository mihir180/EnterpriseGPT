"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { ArrowUp } from "lucide-react";
import ProtectedRoute from "@/components/ProtectedRoute";
import Navbar from "@/components/Navbar";
import ChatMessageBubble from "@/components/ChatMessageBubble";
import { askQuestion, getChatHistory } from "@/lib/api";
import { ApiRequestError } from "@/lib/api";
import type { ChatMessage, ChatQueryRead } from "@/types";

function ChatContent() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isAsking, setIsAsking] = useState(false);
  const [history, setHistory] = useState<ChatQueryRead[]>([]);
  const [isHistoryLoading, setIsHistoryLoading] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);

  async function refreshHistory() {
    setIsHistoryLoading(true);
    try {
      const res = await getChatHistory(0, 50);
      setHistory(res.items);
    } finally {
      setIsHistoryLoading(false);
    }
  }

  useEffect(() => {
    refreshHistory();
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const question = input.trim();
    if (!question || isAsking) return;

    const userMsg: ChatMessage = { id: crypto.randomUUID(), role: "user", content: question };
    const pendingMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "assistant",
      content: "",
      pending: true,
    };
    setMessages((prev) => [...prev, userMsg, pendingMsg]);
    setInput("");
    setIsAsking(true);

    try {
      const res = await askQuestion({ question });
      setMessages((prev) =>
        prev.map((m) =>
          m.id === pendingMsg.id
            ? {
                ...m,
                content: res.answer,
                sources: res.sources,
                contextUsed: res.context_used,
                pending: false,
              }
            : m
        )
      );
      refreshHistory();
    } catch (err) {
      const detail = err instanceof ApiRequestError ? err.message : "Failed to get an answer.";
      setMessages((prev) =>
        prev.map((m) =>
          m.id === pendingMsg.id ? { ...m, content: detail, pending: false, error: true } : m
        )
      );
    } finally {
      setIsAsking(false);
    }
  }

  function handleSelectHistory(item: ChatQueryRead) {
    setMessages([
      { id: `${item.id}-q`, role: "user", content: item.question },
      {
        id: `${item.id}-a`,
        role: "assistant",
        content: item.answer,
        sources: item.sources,
        contextUsed: item.context_used,
      },
    ]);
  }

  return (
    <div className="flex h-screen">
      <Navbar
        chatHistory={history}
        isHistoryLoading={isHistoryLoading}
        onSelectHistory={handleSelectHistory}
        onNewChat={() => setMessages([])}
      />

      <div className="flex flex-1 flex-col bg-paper dark:bg-ink-950">
        <div ref={scrollRef} className="flex-1 overflow-y-auto">
          <div className="mx-auto w-full max-w-3xl space-y-7 px-6 py-8">
            {messages.length === 0 ? (
              <div className="flex h-[70vh] flex-col items-center justify-center text-center">
                <p className="font-display text-2xl font-medium text-ink-900 dark:text-ink-50">
                  Ask EnterpriseGPT anything
                </p>
                <p className="mt-2 max-w-sm text-sm text-ink-400 dark:text-ink-100/40">
                  Answers are generated only from your company&apos;s uploaded
                  documents, with citations back to the source.
                </p>
              </div>
            ) : (
              messages.map((m) => <ChatMessageBubble key={m.id} message={m} />)
            )}
          </div>
        </div>

        <div className="px-6 pb-6 pt-2">
          <form onSubmit={handleSubmit} className="mx-auto max-w-3xl">
            <div className="composer-ring flex items-end gap-2 rounded-3xl border border-ink-100 dark:border-white/10 bg-paper-raised dark:bg-ink-800 px-4 py-2.5 shadow-composer transition-shadow">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSubmit(e as unknown as FormEvent);
                  }
                }}
                rows={1}
                placeholder="Ask a question about your company documents…"
                className="flex-1 resize-none bg-transparent py-1.5 text-[14px] text-ink-900 dark:text-ink-50 placeholder:text-ink-400 dark:placeholder:text-ink-100/40 outline-none"
              />
              <button
                type="submit"
                disabled={isAsking || !input.trim()}
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-600 text-white transition-colors hover:bg-brand-700 disabled:opacity-40"
              >
                <ArrowUp size={16} />
              </button>
            </div>
            <p className="mt-2 text-center text-[11px] text-ink-400 dark:text-ink-100/40">
              EnterpriseGPT can make mistakes. Check important information against
              the cited sources.
            </p>
          </form>
        </div>
      </div>
    </div>
  );
}

export default function ChatPage() {
  return (
    <ProtectedRoute>
      <ChatContent />
    </ProtectedRoute>
  );
}
