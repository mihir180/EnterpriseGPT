"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneLight } from "react-syntax-highlighter/dist/esm/styles/prism";
import { FileText, AlertTriangle, User as UserIcon, Sparkles } from "lucide-react";
import clsx from "clsx";
import type { ChatMessage } from "@/types";

export default function ChatMessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";

  return (
    <div className={clsx("flex gap-3", isUser && "flex-row-reverse")}>
      <div
        className={clsx(
          "flex h-7 w-7 shrink-0 items-center justify-center rounded-full",
          isUser ? "bg-ink-900 text-white" : "bg-brand-600 text-white"
        )}
      >
        {isUser ? <UserIcon size={13} /> : <Sparkles size={13} />}
      </div>

      <div className={clsx("max-w-[80%] space-y-2", isUser && "flex flex-col items-end")}>
        <div
          className={clsx(
            "text-[14px] leading-relaxed",
            isUser
              ? "rounded-2xl bg-ink-900 px-4 py-2.5 text-white"
              : message.error
              ? "rounded-2xl border border-red-200 bg-red-50 px-4 py-2.5 text-red-700"
              : "text-ink-900 dark:text-ink-50"
          )}
        >
          {message.error && (
            <div className="mb-1 flex items-center gap-1 text-xs font-medium">
              <AlertTriangle size={13} /> Something went wrong
            </div>
          )}

          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : message.pending ? (
            <TypingIndicator />
          ) : (
            <div className="markdown-body">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  code({ className, children, ...props }) {
                    const match = /language-(\w+)/.exec(className || "");
                    return match ? (
                      <SyntaxHighlighter
                        style={oneLight}
                        language={match[1]}
                        PreTag="div"
                        customStyle={{ fontSize: "0.8rem", margin: 0, borderRadius: "0.75rem" }}
                      >
                        {String(children).replace(/\n$/, "")}
                      </SyntaxHighlighter>
                    ) : (
                      <code className={className} {...props}>
                        {children}
                      </code>
                    );
                  },
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {!isUser && !message.pending && message.sources && message.sources.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {message.sources.map((s) => (
              <div
                key={s.chunk_id}
                title={`Relevance score: ${s.score.toFixed(2)}`}
                className="flex items-center gap-1 rounded-full border border-ink-100 dark:border-white/10 bg-paper-raised dark:bg-ink-800 px-2.5 py-1 text-xs text-ink-500 dark:text-ink-100/50"
              >
                <FileText size={11} className="text-brand-600" />
                {s.filename}
                {s.page_number != null && <span className="text-ink-400 dark:text-ink-100/40">· p.{s.page_number}</span>}
              </div>
            ))}
          </div>
        )}

        {!isUser && !message.pending && !message.error && !message.contextUsed && (
          <p className="text-xs text-ink-400 dark:text-ink-100/40">
            No matching content found in your documents for this answer.
          </p>
        )}
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 py-1">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="h-1.5 w-1.5 animate-bounce rounded-full bg-ink-400"
          style={{ animationDelay: `${i * 0.15}s` }}
        />
      ))}
    </div>
  );
}
