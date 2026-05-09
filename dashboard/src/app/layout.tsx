import type { Metadata } from "next";
import Link from "next/link";

import "./globals.css";

export const metadata: Metadata = {
  title: "Augure dashboard",
  description: "On-chain state of the Augure Phase 1 settlement layer",
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-bg text-text antialiased">
        <header className="border-b border-border">
          <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
            <Link href="/" className="font-mono text-lg font-semibold tracking-tight">
              augure
              <span className="text-muted">.</span>
              <span className="text-accent">dashboard</span>
            </Link>
            <nav className="flex gap-6 text-sm font-mono">
              <Link href="/" className="hover:text-accent">
                token
              </Link>
              <Link href="/rounds" className="hover:text-accent">
                rounds
              </Link>
              <a
                href="https://github.com/Elladriel80/augure"
                target="_blank"
                rel="noreferrer noopener"
                className="hover:text-accent text-muted"
              >
                github ↗
              </a>
            </nav>
          </div>
        </header>
        <main className="max-w-5xl mx-auto px-4 py-8">{children}</main>
        <footer className="border-t border-border mt-12">
          <div className="max-w-5xl mx-auto px-4 py-4 text-xs text-muted font-mono">
            Read-only view. No wallet, no transactions. Data refreshed on each page load.
          </div>
        </footer>
      </body>
    </html>
  );
}
