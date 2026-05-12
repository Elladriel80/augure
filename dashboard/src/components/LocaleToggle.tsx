"use client";

import { useRouter } from "next/navigation";
import { useTransition } from "react";

import type { Locale } from "@/lib/i18n";

const LOCALE_COOKIE = "aratea-locale";
const ONE_YEAR_SECONDS = 60 * 60 * 24 * 365;

interface Props {
  current: Locale;
  labels: { en: string; fr: string; aria: string };
}

export function LocaleToggle({ current, labels }: Props) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();

  function setLocale(next: Locale) {
    if (next === current) return;
    document.cookie = `${LOCALE_COOKIE}=${next}; path=/; max-age=${ONE_YEAR_SECONDS}; samesite=lax`;
    startTransition(() => router.refresh());
  }

  return (
    <div
      className="inline-flex items-center text-xs font-mono border border-border rounded overflow-hidden"
      aria-label={labels.aria}
    >
      <button
        type="button"
        onClick={() => setLocale("en")}
        disabled={isPending}
        className={`px-2 py-1 transition-colors ${
          current === "en"
            ? "bg-accent/20 text-accent"
            : "text-muted hover:text-accent"
        }`}
      >
        {labels.en}
      </button>
      <button
        type="button"
        onClick={() => setLocale("fr")}
        disabled={isPending}
        className={`px-2 py-1 transition-colors border-l border-border ${
          current === "fr"
            ? "bg-accent/20 text-accent"
            : "text-muted hover:text-accent"
        }`}
      >
        {labels.fr}
      </button>
    </div>
  );
}
