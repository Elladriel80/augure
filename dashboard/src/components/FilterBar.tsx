"use client";

import type { Route } from "next";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

interface Props {
  seriesOptions: string[];
  statusOptions: string[];
  labels: {
    series_label: string;
    status_label: string;
    clear: string;
  };
}

/**
 * Sticky filter bar for Layer 3. Chip-style multi-select bound to URL params
 * `?series=KXLOWTNYC,KXHIGHCHI&status=resolved,open`. Server-rendered tables
 * read the same params and filter their rows before render — no client-side
 * state, the URL is the source of truth.
 */
export function FilterBar({ seriesOptions, statusOptions, labels }: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const search = useSearchParams();

  function activeValues(key: string): Set<string> {
    const raw = search?.get(key);
    if (!raw) return new Set();
    return new Set(raw.split(",").filter(Boolean));
  }

  function setValues(key: string, next: Set<string>) {
    const params = new URLSearchParams(search?.toString() ?? "");
    if (next.size === 0) params.delete(key);
    else params.set(key, [...next].join(","));
    const qs = params.toString();
    const href = (qs ? `${pathname}?${qs}` : pathname) as Route;
    router.replace(href, { scroll: false });
  }

  function toggle(key: string, value: string) {
    const current = activeValues(key);
    if (current.has(value)) current.delete(value);
    else current.add(value);
    setValues(key, current);
  }

  function clear(key: string) {
    setValues(key, new Set());
  }

  function group(key: string, label: string, options: string[]) {
    const active = activeValues(key);
    return (
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-[10px] uppercase tracking-wider text-muted font-mono shrink-0">
          {label}
        </span>
        {options.map((opt) => {
          const on = active.has(opt);
          return (
            <button
              key={opt}
              type="button"
              onClick={() => toggle(key, opt)}
              aria-pressed={on}
              className={`px-2 py-0.5 rounded border text-[11px] font-mono transition-colors ${
                on
                  ? "border-accent/50 bg-accent/15 text-accent"
                  : "border-border bg-bg/40 text-muted hover:text-text"
              }`}
            >
              {opt}
            </button>
          );
        })}
        {active.size > 0 ? (
          <button
            type="button"
            onClick={() => clear(key)}
            className="text-[10px] font-mono text-muted hover:text-accent underline-offset-2 hover:underline"
          >
            {labels.clear}
          </button>
        ) : null}
      </div>
    );
  }

  return (
    <div className="sticky top-0 z-20 -mx-4 px-4 py-3 backdrop-blur bg-bg/85 border-b border-border flex flex-col gap-2">
      {seriesOptions.length > 0
        ? group("series", labels.series_label, seriesOptions)
        : null}
      {group("status", labels.status_label, statusOptions)}
    </div>
  );
}
