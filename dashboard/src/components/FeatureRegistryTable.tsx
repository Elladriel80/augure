"use client";

import { useMemo, useState } from "react";
import type { ReactNode } from "react";

import type { FeatureRecord } from "@/lib/manifest";
import { formatDelta, formatRunTimestamp } from "@/lib/manifest";

import { FeatureStatusBadge } from "./FeatureStatusBadge";

type SortKey = "name" | "delta" | "status";
type SortDir = "asc" | "desc";

const URL_RE = /(https?:\/\/[^\s`)]+)/;

function extractUrl(source: string): string | null {
  const m = source.match(URL_RE);
  return m ? m[1].replace(/[.,;]+$/, "") : null;
}

function deltaBarWidth(value: number | null, maxAbs: number): number {
  if (value === null || maxAbs === 0) return 0;
  return Math.min(100, (Math.abs(value) / maxAbs) * 100);
}

export interface FeatureTableLabels {
  header_name: string;
  header_hypothesis: string;
  header_source: string;
  header_added: string;
  header_delta: string;
  header_status: string;
  modal_feature: string;
  modal_hypothesis: string;
  modal_status: string;
  modal_date_added: string;
  modal_source: string;
  modal_current_delta: string;
  modal_history: string;
  modal_history_empty: string;
  modal_history_run: string;
  modal_history_feature_set: string;
  modal_close: string;
  modal_close_aria: string;
}

interface Props {
  features: FeatureRecord[];
  labels: FeatureTableLabels;
  /** Footer prose rendered as a ReactNode — built server-side because the
   *  i18n dictionary stores it as a function and functions can't cross the
   *  RSC → Client Component boundary. */
  footer: ReactNode;
}

export function FeatureRegistryTable({ features, labels, footer }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("delta");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [selected, setSelected] = useState<FeatureRecord | null>(null);

  const maxAbsDelta = useMemo(
    () =>
      features.reduce(
        (acc, f) =>
          typeof f.current_brier_delta === "number"
            ? Math.max(acc, Math.abs(f.current_brier_delta))
            : acc,
        0,
      ),
    [features],
  );

  const sorted = useMemo(() => {
    const copy = [...features];
    copy.sort((a, b) => {
      let cmp = 0;
      if (sortKey === "name") {
        cmp = a.name.localeCompare(b.name);
      } else if (sortKey === "status") {
        cmp = a.current_status.localeCompare(b.current_status);
      } else {
        const av =
          typeof a.current_brier_delta === "number"
            ? a.current_brier_delta
            : Number.NEGATIVE_INFINITY;
        const bv =
          typeof b.current_brier_delta === "number"
            ? b.current_brier_delta
            : Number.NEGATIVE_INFINITY;
        cmp = av - bv;
      }
      return sortDir === "asc" ? cmp : -cmp;
    });
    return copy;
  }, [features, sortKey, sortDir]);

  const onSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir(key === "name" ? "asc" : "desc");
    }
  };

  return (
    <>
      <div className="overflow-x-auto rounded-md border border-border bg-panel">
        <table className="w-full text-sm font-mono">
          <thead>
            <tr className="border-b border-border text-left text-muted">
              <SortHeader
                label={labels.header_name}
                col="name"
                sortKey={sortKey}
                sortDir={sortDir}
                onClick={onSort}
              />
              <th className="px-4 py-3">{labels.header_hypothesis}</th>
              <th className="px-4 py-3">{labels.header_source}</th>
              <th className="px-4 py-3">{labels.header_added}</th>
              <SortHeader
                label={labels.header_delta}
                col="delta"
                sortKey={sortKey}
                sortDir={sortDir}
                onClick={onSort}
                align="right"
              />
              <SortHeader
                label={labels.header_status}
                col="status"
                sortKey={sortKey}
                sortDir={sortDir}
                onClick={onSort}
              />
            </tr>
          </thead>
          <tbody>
            {sorted.map((f) => {
              const delta = f.current_brier_delta;
              const isPositive = typeof delta === "number" && delta > 0;
              const isNegative = typeof delta === "number" && delta < 0;
              const url = extractUrl(f.source);
              return (
                <tr
                  key={f.name}
                  className="border-b border-border/50 last:border-0 align-top cursor-pointer hover:bg-border/20"
                  onClick={() => setSelected(f)}
                >
                  <td className="px-4 py-3 text-accent font-mono">
                    {f.name}
                  </td>
                  <td className="px-4 py-3 text-text/80 text-xs max-w-md">
                    <span className="line-clamp-2" title={f.hypothesis}>
                      {f.hypothesis}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-muted text-xs max-w-[14rem]">
                    {url ? (
                      <a
                        href={url}
                        target="_blank"
                        rel="noreferrer noopener"
                        className="text-accent hover:underline"
                        onClick={(e) => e.stopPropagation()}
                      >
                        {url}
                      </a>
                    ) : (
                      <span className="line-clamp-2" title={f.source}>
                        {f.source}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-muted whitespace-nowrap">
                    {f.date_added}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <span
                        className={
                          isPositive
                            ? "text-err"
                            : isNegative
                              ? "text-ok"
                              : "text-muted"
                        }
                      >
                        {typeof delta === "number"
                          ? `${isPositive ? "↑" : isNegative ? "↓" : "·"} ${formatDelta(
                              delta,
                            )}`
                          : f.current_brier_delta_raw}
                      </span>
                      <div className="hidden md:block w-16 h-1.5 bg-border rounded overflow-hidden">
                        <div
                          className={
                            isPositive
                              ? "h-full bg-err"
                              : isNegative
                                ? "h-full bg-ok"
                                : "h-full bg-muted"
                          }
                          style={{
                            width: `${deltaBarWidth(delta, maxAbsDelta)}%`,
                          }}
                        />
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <FeatureStatusBadge status={f.current_status} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <p className="mt-2 text-xs text-muted font-mono">{footer}</p>

      {selected && (
        <FeatureDetailModal
          feature={selected}
          labels={labels}
          onClose={() => setSelected(null)}
        />
      )}
    </>
  );
}

function SortHeader({
  label,
  col,
  sortKey,
  sortDir,
  onClick,
  align = "left",
}: {
  label: string;
  col: SortKey;
  sortKey: SortKey;
  sortDir: SortDir;
  onClick: (k: SortKey) => void;
  align?: "left" | "right";
}) {
  const active = sortKey === col;
  const arrow = active ? (sortDir === "asc" ? "↑" : "↓") : "";
  return (
    <th
      className={`px-4 py-3 select-none cursor-pointer hover:text-text ${
        align === "right" ? "text-right" : ""
      }`}
      onClick={() => onClick(col)}
    >
      {label} {arrow}
    </th>
  );
}

function FeatureDetailModal({
  feature,
  labels,
  onClose,
}: {
  feature: FeatureRecord;
  labels: FeatureTableLabels;
  onClose: () => void;
}) {
  const url = extractUrl(feature.source);
  return (
    <div
      className="fixed inset-0 z-50 bg-bg/80 backdrop-blur-sm flex items-start justify-center p-4 overflow-y-auto"
      onClick={onClose}
    >
      <div
        className="bg-panel border border-border rounded-md max-w-2xl w-full p-6 my-12 font-mono space-y-5"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="text-xs uppercase tracking-wider text-muted">
              {labels.modal_feature}
            </div>
            <div className="text-xl text-accent mt-1">{feature.name}</div>
          </div>
          <button
            onClick={onClose}
            className="text-muted hover:text-text text-sm border border-border rounded px-2 py-1"
            aria-label={labels.modal_close_aria}
          >
            {labels.modal_close}
          </button>
        </div>

        <div>
          <div className="text-xs uppercase tracking-wider text-muted mb-1">
            {labels.modal_hypothesis}
          </div>
          <p className="text-sm text-text/90 leading-relaxed whitespace-pre-wrap">
            {feature.hypothesis}
          </p>
        </div>

        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <div className="text-xs uppercase tracking-wider text-muted mb-1">
              {labels.modal_status}
            </div>
            <FeatureStatusBadge status={feature.current_status} />
          </div>
          <div>
            <div className="text-xs uppercase tracking-wider text-muted mb-1">
              {labels.modal_date_added}
            </div>
            <div className="text-text/90">{feature.date_added}</div>
          </div>
          <div className="col-span-2">
            <div className="text-xs uppercase tracking-wider text-muted mb-1">
              {labels.modal_source}
            </div>
            {url ? (
              <a
                href={url}
                target="_blank"
                rel="noreferrer noopener"
                className="text-accent hover:underline break-all"
              >
                {feature.source}
              </a>
            ) : (
              <div className="text-text/90 break-words">{feature.source}</div>
            )}
          </div>
          <div className="col-span-2">
            <div className="text-xs uppercase tracking-wider text-muted mb-1">
              {labels.modal_current_delta}
            </div>
            <div className="text-text/90">
              {typeof feature.current_brier_delta === "number"
                ? formatDelta(feature.current_brier_delta)
                : feature.current_brier_delta_raw}
            </div>
          </div>
        </div>

        <div>
          <div className="text-xs uppercase tracking-wider text-muted mb-2">
            {labels.modal_history}
          </div>
          {feature.history.length === 0 ? (
            <p className="text-xs text-muted">{labels.modal_history_empty}</p>
          ) : (
            <div className="overflow-x-auto rounded border border-border">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-left text-muted border-b border-border">
                    <th className="px-3 py-2">{labels.modal_history_run}</th>
                    <th className="px-3 py-2">{labels.modal_history_feature_set}</th>
                    <th className="px-3 py-2 text-right">{labels.header_delta}</th>
                    <th className="px-3 py-2">{labels.modal_status}</th>
                  </tr>
                </thead>
                <tbody>
                  {feature.history.map((h, i) => (
                    <tr
                      key={i}
                      className="border-b border-border/50 last:border-0"
                    >
                      <td className="px-3 py-2 text-muted">
                        {formatRunTimestamp(h.run_ts)}
                      </td>
                      <td className="px-3 py-2 text-accent">
                        {h.feature_set ?? "—"}
                      </td>
                      <td
                        className={`px-3 py-2 text-right ${
                          typeof h.brier_delta === "number" && h.brier_delta < 0
                            ? "text-ok"
                            : typeof h.brier_delta === "number" &&
                                h.brier_delta > 0
                              ? "text-err"
                              : "text-muted"
                        }`}
                      >
                        {formatDelta(h.brier_delta)}
                      </td>
                      <td className="px-3 py-2">
                        {h.status ? (
                          <FeatureStatusBadge status={h.status} />
                        ) : (
                          <span className="text-muted">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
