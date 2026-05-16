// components/roadmap/Hero.tsx
import Link from "next/link";
import type { Content, Locale } from "./content";

interface Props {
  content: Content;
  locale: Locale;
}

export function Hero({ content, locale }: Props) {
  const other: Locale = locale === "fr" ? "en" : "fr";

  return (
    <header className="relative overflow-hidden border-b border-border bg-bg">
      {/* Subtle dot grid — astronomical hint without being literal */}
      <div
        aria-hidden="true"
        className="absolute inset-0 opacity-[0.04]"
        style={{
          backgroundImage:
            "radial-gradient(circle at 1px 1px, white 1px, transparent 0)",
          backgroundSize: "32px 32px",
        }}
      />

      <div className="relative mx-auto max-w-5xl px-6 pb-16 pt-20 sm:px-8 sm:pt-28">
        {/* Top meta bar */}
        <div className="mb-12 flex items-center justify-between text-xs font-mono text-muted">
          <span className="uppercase tracking-widest">Aratea</span>
          <span>{content.version} · {content.date}</span>
          <Link
            href={`?lang=${other}`}
            scroll={false}
            className="border border-border rounded px-2 py-1 text-muted hover:text-accent hover:border-accent/50 transition-colors"
            aria-label={`Switch to ${other.toUpperCase()}`}
          >
            {content.switchLabel}
          </Link>
        </div>

        {/* Title */}
        <h1 className="font-mono text-5xl font-normal tracking-tight text-text sm:text-6xl md:text-7xl">
          {content.hero.title}
        </h1>

        <p className="mt-4 max-w-2xl text-base text-muted sm:text-lg">
          {content.hero.subtitle}
        </p>

        {/* Preamble — left rule in accent */}
        <p className="mt-10 max-w-3xl border-l-2 border-accent/50 pl-6 text-sm leading-relaxed text-text">
          {content.hero.preamble}
        </p>

        {/* Antique quote */}
        <figure className="mt-14 max-w-2xl">
          <blockquote className="font-mono text-sm italic text-text sm:text-base">
            {content.hero.quote}
          </blockquote>
          <figcaption className="mt-2 text-xs font-mono text-muted">
            — {content.hero.quoteAttribution}
          </figcaption>
        </figure>
      </div>
    </header>
  );
}
