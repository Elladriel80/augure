import type { Metadata } from "next";
import Link from "next/link";

import { LocaleToggle } from "@/components/LocaleToggle";
import { getDictAndLocale } from "@/lib/i18n";

import "./globals.css";

export const metadata: Metadata = {
  title: "Aratea dashboard",
  description: "On-chain state of the Aratea Phase 1 settlement layer",
  robots: { index: false, follow: false },
};

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { dict, locale } = await getDictAndLocale();

  return (
    <html lang={locale}>
      <body className="min-h-screen bg-bg text-text antialiased">
        <header className="border-b border-border">
          <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between gap-4">
            <Link
              href="/"
              className="font-mono text-lg font-semibold tracking-tight"
            >
              aratea
              <span className="text-muted">.</span>
              <span className="text-accent">dashboard</span>
            </Link>
            <nav className="flex items-center gap-6 text-sm font-mono">
              <Link href="/predictor" className="hover:text-accent">
                {dict.layout.nav.predictor}
              </Link>
              <Link href="/token" className="hover:text-accent">
                {dict.layout.nav.token}
              </Link>
              <Link href="/rounds" className="hover:text-accent">
                {dict.layout.nav.rounds}
              </Link>
              <a
                href="https://github.com/Elladriel80/aratea"
                target="_blank"
                rel="noreferrer noopener"
                className="hover:text-accent text-muted"
              >
                {dict.layout.nav.github}
              </a>
              <LocaleToggle current={locale} labels={dict.locale_toggle} />
            </nav>
          </div>
        </header>
        <main className="max-w-5xl mx-auto px-4 py-8">{children}</main>
        <footer className="border-t border-border mt-12">
          <div className="max-w-5xl mx-auto px-4 py-4 text-xs text-muted font-mono">
            {dict.layout.footer}
          </div>
        </footer>
      </body>
    </html>
  );
}
