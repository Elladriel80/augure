import { getDict } from "@/lib/i18n";
import {
  formatBrier,
  formatDelta,
  formatRunTimestamp,
} from "@/lib/manifest";
import type { RunRecord } from "@/lib/manifest";
import { VerdictBadge } from "./VerdictBadge";

export async function RunHistoryTable({ runs }: { runs: RunRecord[] }) {
  const dict = await getDict();
  const t = dict.components.history_table;

  if (runs.length === 0) {
    return (
      <div className="rounded-md border border-border bg-panel p-4 text-sm text-muted font-mono">
        {t.empty}
      </div>
    );
  }
  const sorted = [...runs].sort((a, b) => b.ts.localeCompare(a.ts));
  return (
    <div className="overflow-x-auto rounded-md border border-border bg-panel">
      <table className="w-full text-sm font-mono">
        <thead>
          <tr className="border-b border-border text-left text-muted">
            <th className="px-4 py-3">{t.header_when}</th>
            <th className="px-4 py-3">{t.header_feature_set}</th>
            <th className="px-4 py-3 text-right">{t.header_n_test}</th>
            <th className="px-4 py-3 text-right">{t.header_brier_test}</th>
            <th className="px-4 py-3 text-right">{t.header_brier_kalshi_mid}</th>
            <th className="px-4 py-3 text-right">{t.header_gap}</th>
            <th className="px-4 py-3">{t.header_verdict}</th>
            <th className="px-4 py-3">{t.header_notes}</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((r) => {
            const gapNegative =
              typeof r.gap_vs_kalshi_mid === "number" &&
              r.gap_vs_kalshi_mid < 0;
            const gapTone = gapNegative
              ? "text-ok"
              : r.gap_vs_kalshi_mid === 0
                ? "text-warn"
                : "text-err";
            return (
              <tr
                key={r.ts}
                className="border-b border-border/50 last:border-0 align-top"
              >
                <td className="px-4 py-3 text-muted whitespace-nowrap">
                  {formatRunTimestamp(r.ts)}
                </td>
                <td className="px-4 py-3 text-accent">{r.feature_set}</td>
                <td className="px-4 py-3 text-right">{r.n_test ?? "—"}</td>
                <td className="px-4 py-3 text-right">
                  {formatBrier(r.brier_test)}
                </td>
                <td className="px-4 py-3 text-right text-warn">
                  {formatBrier(r.brier_kalshi_mid_test)}
                </td>
                <td className={`px-4 py-3 text-right ${gapTone}`}>
                  {formatDelta(r.gap_vs_kalshi_mid)}
                </td>
                <td className="px-4 py-3">
                  <VerdictBadge verdict={r.verdict} />
                </td>
                <td className="px-4 py-3 text-muted text-xs max-w-md">
                  <span className="line-clamp-2" title={r.notes}>
                    {r.notes || "—"}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
