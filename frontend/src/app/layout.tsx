import type { Metadata } from "next";
import { Inter, Fraunces } from "next/font/google";
import { AuthProvider } from "@/lib/auth-context";
import { ThemeProvider } from "@/lib/theme-context";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

// Used sparingly — the wordmark and empty-state heading only.
const fraunces = Fraunces({
  subsets: ["latin"],
  weight: ["500", "600"],
  variable: "--font-fraunces",
  display: "swap",
});

export const metadata: Metadata = {
  title: "EnterpriseGPT",
  description: "Secure Enterprise RAG AI Assistant",
};

// Runs before React hydrates, so the page never flashes light-mode
// colors before switching to a saved dark preference.
const noFlashScript = `
(function () {
  try {
    var theme = localStorage.getItem("theme");
    if (theme === "dark") document.documentElement.classList.add("dark");
  } catch (e) {}
})();
`;

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${inter.variable} ${fraunces.variable}`}>
      <head>
        <script dangerouslySetInnerHTML={{ __html: noFlashScript }} />
      </head>
      <body className="bg-paper font-sans text-ink-900 antialiased dark:bg-ink-950 dark:text-ink-50">
        <ThemeProvider>
          <AuthProvider>{children}</AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
