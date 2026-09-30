"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  MessageSquare,
  FileText,
  LogOut,
  ShieldCheck,
  MessageSquarePlus,
  Sun,
  Moon,
} from "lucide-react";
import clsx from "clsx";
import { useAuth } from "@/lib/auth-context";
import { useTheme } from "@/lib/theme-context";
import type { ChatQueryRead } from "@/types";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/chat", label: "Chat", icon: MessageSquare },
  { href: "/documents", label: "Documents", icon: FileText },
];

interface NavbarProps {
  // Optional — only passed on the chat page. When present, the chat history
  // renders inline in this same sidebar instead of as a separate panel.
  chatHistory?: ChatQueryRead[];
  isHistoryLoading?: boolean;
  onSelectHistory?: (item: ChatQueryRead) => void;
  onNewChat?: () => void;
}

export default function Navbar({
  chatHistory,
  isHistoryLoading,
  onSelectHistory,
  onNewChat,
}: NavbarProps) {
  const pathname = usePathname();
  const { user, logout, isAdmin } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const showHistory = chatHistory !== undefined;

  return (
    <aside className="flex h-screen w-72 shrink-0 flex-col bg-ink-950 text-ink-100">
      <div className="flex items-center gap-2 px-4 pt-5 pb-4">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-brand-600 text-xs font-bold text-white">
          EG
        </div>
        <span className="font-display text-[15px] font-medium tracking-tight text-white">
          EnterpriseGPT
        </span>
      </div>

      <nav className="flex flex-col gap-0.5 px-3">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={clsx(
              "flex items-center gap-2.5 rounded-lg px-3 py-2 text-[13px] font-medium transition-colors",
              pathname === href
                ? "bg-ink-800 text-white"
                : "text-ink-100/70 hover:bg-ink-800/60 hover:text-white"
            )}
          >
            <Icon size={15} />
            {label}
          </Link>
        ))}
      </nav>

      {showHistory && (
        <>
          <div className="px-3 pt-4">
            <button
              onClick={onNewChat}
              className="flex w-full items-center justify-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-2 text-[13px] font-medium text-white/90 transition-colors hover:bg-white/10"
            >
              <MessageSquarePlus size={14} />
              New question
            </button>
          </div>

          <div className="mt-3 flex-1 overflow-y-auto px-3 pb-2">
            <p className="px-2 py-1.5 text-[11px] font-semibold uppercase tracking-wide text-ink-100/35">
              Recent
            </p>
            {isHistoryLoading ? (
              <p className="px-2 py-2 text-[13px] text-ink-100/40">Loading…</p>
            ) : !chatHistory || chatHistory.length === 0 ? (
              <p className="px-2 py-2 text-[13px] text-ink-100/40">
                No questions yet.
              </p>
            ) : (
              <ul className="space-y-0.5">
                {chatHistory.map((item) => (
                  <li key={item.id}>
                    <button
                      onClick={() => onSelectHistory?.(item)}
                      className="w-full truncate rounded-lg px-2 py-2 text-left text-[13px] text-ink-100/70 transition-colors hover:bg-ink-800/60 hover:text-white"
                      title={item.question}
                    >
                      {item.question}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </>
      )}

      {!showHistory && <div className="flex-1" />}

      <div className="border-t border-white/10 px-3 py-3">
        <button
          onClick={toggleTheme}
          className="mb-1.5 flex w-full items-center gap-2.5 rounded-lg px-2 py-2 text-[13px] font-medium text-ink-100/70 transition-colors hover:bg-ink-800/60 hover:text-white"
        >
          {theme === "dark" ? <Sun size={15} /> : <Moon size={15} />}
          {theme === "dark" ? "Light mode" : "Dark mode"}
        </button>
        <div className="mb-1.5 flex items-center gap-2.5 px-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-white/10 text-xs font-semibold text-white">
            {user?.full_name?.slice(0, 1).toUpperCase() ?? "?"}
          </div>
          <div className="min-w-0">
            <p className="truncate text-[13px] font-medium text-white">
              {user?.full_name}
            </p>
            <p className="flex items-center gap-1 truncate text-[11px] text-ink-100/40">
              {isAdmin && <ShieldCheck size={11} className="text-brand-400" />}
              {user?.role}
            </p>
          </div>
        </div>
        <button
          onClick={logout}
          className="flex w-full items-center gap-2.5 rounded-lg px-2 py-2 text-[13px] font-medium text-ink-100/70 transition-colors hover:bg-ink-800/60 hover:text-white"
        >
          <LogOut size={15} />
          Log out
        </button>
      </div>
    </aside>
  );
}
