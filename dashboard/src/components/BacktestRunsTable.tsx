"use client";

import { useState } from "react";

import type { BacktestRunRecord, BacktestModel } from "@/lib/manifest";
import { formatBrier, isBacktestRunNaive } from "@/lib/manifest";

const PAGE_SIZE = 25;

function fmtPct(p: number | null | undefined): string {
  if (p === null || p === undefined || Number.isNaN(p)) return "—";
  return `${(p * 100).toFixed(1)}%`;
}

function bestBrierName(models: BacktestModel[]): string | null {
  let best: { name: string; brier: number } | null = null;
  for (const m of models) {
    if (typeof m.brier === "number" && !Number.isNaN(m.brier)) {
      if (!best || m.brier < best.brier) {
        best = { name: m.name, brier: m.brier };
      }
    }
  }
  return best?.name ?? null;
}

function ModelCell({
  model,
  isBest,
}: {
  model: BacktestModel | undefined;
  isBest: boolean;
}) {
  if (!model) return <span className="text-muted">—</span>;
  const p = fmtPct(model.p_yes);
  const b = typeof model.brier === "number" ? formatBrier(model.brier) : null;
  return (
    <span className="block">
      <span className="text-text">{p}</span>
      {b ? (
        <span className={`block text-[10px] ${isBest ? "text-ok" : "text-muted"}`}>
          B={b}
          {isBest ? " ★" : ""}
        </span>
      ) : null}
    </span>
  );
}

interface Labels {
  empty: string;
  header_run: string;
  header_when: string;
  header_event: string;
  header_mode: string;
  header_model: string;
  header_outcome: string;
  pending: string;
  win: string;
  loss: string;
  footer: string;
  load_more: string;
  showing: (visible: number, total: number) => string;
  naive_label: string;
  naive_tooltip: string;
}

interface Props {
  runs: BacktestRunRecord[];
  /** Total count from manifest top-level — may exceed `runs.length` when the
   *  backend truncates the per-record list. Displayed in the footer. */
  total: number;
  labels: Labels;
}

export function BacktestRunsTable({ runs, total, labels: t }: Props) {
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);

  if (runs.length === 0) {
    return (
      <div className="rounded-md border border-border bg-panel p-4 text-sm text-muted font-mono">
        {t.empty}
      </div>
    );
  }

  const sorted = [...runs].sort((a, b) => b.run_id.localeCompare(a.run_id));
  const shown = sorted.slice(0, visibleCount);
  const canLoadMore = visibleCount < sorted.length;
  const effectiveTotal = Math.max(total, sorted.length);

  return (
    <div className="rounded-md border border-border bg-panel">
      <div className="overflow-x-auto">
        <table className="w-full text-sm font-mono">
          <thead>
            <tr className="border-b border-border text-left text-muted">
              <th className="px-3 py-3">{t.header_run}</th>
              <th className="px-3 py-3">{t.header_when}</th>
              <th className="px-3 py-3">{t.header_event}</th>
              <th className="px-3 py-3">{t.header_mode}</th>
              <th className="px-3 py-3 text-right">{t.header_model}</th>
              <th className="px-3 py-3">{t.header_outcome}</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((r) => {
              const naive = isBacktestRunNaive(r);
              const bestName = bestBrierName(r.models);
              const firstModel = r.models[0];
              const bin = r.target_market_ticker.split("-").pop() ?? "—";
              const isResolved = r.resolution.status === "resolved";
              const won =
                isResolved && firstModel ? firstModel.won === true : null;

              return (
                <tr
                  key={r.run_id}
                  className="border-b border-border/50 last:border-0 align-top"
                >
                  <td className="px-3 py-3 text-accent font-semibold whitespace-nowrap">
                    {r.run_id}
                  </td>
                  <td className="px-3 py-3 text-muted whitespace-nowrap">
                    <span className="block">{r.as_of_date}</span>
                    <span className="block text-[10px] text-muted/70">
                      → {r.target_date}
                    </span>
                  </td>
                  <td className="px-3 py-3 text-text">
                    <span className="block">{r.series}</span>
                    <span
                      className="block text-[10px] text-muted"
                      title={r.event_title}
                    >
                      {bin}
                    </span>
                  </td>
                  <td className="px-3 py-3 text-muted">
                    <span className="block">{r.mode}</span>
                    {naive ? (
                      <span
                        title={t.naive_tooltip}
                        className="inline-flex items-center rounded border border-warn/40 bg-warn/10 px-1.5 py-0.5 mt-1 text-[10px] font-mono text-warn uppercase tracking-wider"
                      >
                        {t.naive_label}
                      </span>
                    ) : null}
                  </td>
                  <td className="px-3 py-3 text-right">
                    <ModelCell
                      model={firstModel}
                      isBest={!!firstModel && bestName === firstModel.name}
                    />
                  </td>
                  <td className="px-3 py-3">
                    <OutcomeBadge
                      status={r.resolution.status}
                      outcome={r.resolution.outcome}
                      won={won}
                      labels={t}
                    />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="border-t border-border/50 px-3 py-2 flex items-center justify-between flex-wrap gap-2">
        <span className="text-[10px] text-muted font-mono">
          {t.showing(shown.length, effectiveTotal)}
        </span>
        <div className="flex items-center gap-3">
          <span className="text-[10px] text-muted/80 font-mono">{t.footer}</span>
          {canLoadMore ? (
            <button
              type="button"
              onClick={() => setVisibleCount((c) => c + PAGE_SIZE)}
              className="rounded border border-accent/40 bg-accent/10 px-2 py-1 text-[11px] font-mono text-accent hover:bg-accent/20"
            >
              {t.load_more}
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function OutcomeBadge({
  status,
  outcome,
  won,
  labels,
}: {
  status: string;
  outcome: string | null;
  won: boolean | null;
  labels: Pick<Labels, "pending" | "win" | "loss">;
}) {
  if (status !== "resolved" || outcome === null) {
    return (
      <span className="inline-block rounded-md border border-warn/40 bg-warn/10 px-2 py-0.5 text-[11px] font-mono text-warn">
        {labels.pending}
      </span>
    );
  }
  const tone =
    won === true
      ? "border-ok/40 bg-ok/10 text-ok"
      : "border-err/40 bg-err/10 text-err";
  const label =
    won === true
      ? `${labels.win} (${outcome.toUpperCase()})`
      : `${labels.loss} (${outcome.toUpperCase()})`;
  return (
    <span
      className={`inline-block rounded-md border px-2 py-0.5 text-[11px] font-mono ${tone}`}
    >
      {label}
    </span>
  );
}
