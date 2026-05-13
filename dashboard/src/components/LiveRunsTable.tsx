import { getDict } from "@/lib/i18n";
import type { LiveRunRecord, LiveRunModel } from "@/lib/manifest";
import { formatBrier } from "@/lib/manifest";

/** Format a probability as 0.140 → "14.0%". */
function fmtPct(p: number | null | undefined): string {
  if (p === null || p === undefined || Number.isNaN(p)) return "—";
  return `${(p * 100).toFixed(1)}%`;
}

/** Format a P&L in dollars with explicit sign and color choice. */
function fmtPnL(p: number | null | undefined): {
  text: string;
  tone: string;
} {
  if (p === null || p === undefined || Number.isNaN(p)) {
    return { text: "—", tone: "text-muted" };
  }
  const sign = p > 0 ? "+" : p < 0 ? "−" : "±";
  const tone = p > 0 ? "text-ok" : p < 0 ? "text-err" : "text-muted";
  return { text: `${sign}$${Math.abs(p).toFixed(2)}`, tone };
}

/** Map a Kalshi event ticker to a short label. KXLOWTNYC-26MAY11 → "NYC LOWT 11/5". */
function shortEvent(eventTicker: string, _ttl: string): string {
  const m = eventTicker.match(/^KX(\w+?)-(\d{2})([A-Z]{3})(\d{2})$/);
  if (!m) return eventTicker;
  const [, kind, _yr, mon, day] = m;
  const monNum: Record<string, string> = {
    JAN: "1", FEB: "2", MAR: "3", APR: "4", MAY: "5", JUN: "6",
    JUL: "7", AUG: "8", SEP: "9", OCT: "10", NOV: "11", DEC: "12",
  };
  const monShort = monNum[mon] ?? mon;
  return `${kind} ${parseInt(day, 10)}/${monShort}`;
}

/** Find the best (lowest) Brier among models that have one. */
function bestBrierName(models: LiveRunModel[]): string | null {
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

function ModelCell({ model, isBest }: { model: LiveRunModel | undefined; isBest: boolean }) {
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

function OutcomeBadge({
  status,
  outcome,
  won,
  labels,
}: {
  status: string;
  outcome: string | null;
  won: boolean | null;
  labels: {
    pending: string;
    win: (outcome: string) => string;
    loss: (outcome: string) => string;
  };
}) {
  if (status === "open" || outcome === null) {
    return (
      <span className="inline-block rounded-md border border-warn/40 bg-warn/10 px-2 py-0.5 text-[11px] font-mono text-warn">
        {labels.pending}
      </span>
    );
  }
  const tone = won
    ? "border-ok/40 bg-ok/10 text-ok"
    : "border-err/40 bg-err/10 text-err";
  const label = won ? labels.win(outcome) : labels.loss(outcome);
  return (
    <span className={`inline-block rounded-md border px-2 py-0.5 text-[11px] font-mono ${tone}`}>
      {label}
    </span>
  );
}

export async function LiveRunsTable({ runs }: { runs: LiveRunRecord[] }) {
  const dict = await getDict();
  const t = dict.components.live_table;

  if (runs.length === 0) {
    return (
      <div className="rounded-md border border-border bg-panel p-4 text-sm text-muted font-mono">
        {t.empty}
      </div>
    );
  }
  // Newest run first
  const sorted = [...runs].sort((a, b) => b.run_id.localeCompare(a.run_id));
  return (
    <div className="overflow-x-auto rounded-md border border-border bg-panel">
      <table className="w-full text-sm font-mono">
        <thead>
          <tr className="border-b border-border text-left text-muted">
            <th className="px-3 py-3">{t.header_run}</th>
            <th className="px-3 py-3">{t.header_when}</th>
            <th className="px-3 py-3">{t.header_event}</th>
            <th className="px-3 py-3">{t.header_side}</th>
            <th className="px-3 py-3 text-right">{t.header_champion}</th>
            <th className="px-3 py-3 text-right">{t.header_challenger}</th>
            <th className="px-3 py-3 text-right">{t.header_baseline}</th>
            <th className="px-3 py-3 text-right">{t.header_kalshi_mid}</th>
            <th className="px-3 py-3">{t.header_outcome}</th>
            <th className="px-3 py-3 text-right">{t.header_pnl}</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((r) => {
            const champion = r.models.find((m) => m.role === "champion");
            const challengers = r.models.filter((m) => m.role === "challenger");
            const baselines = r.models.filter((m) => m.role === "baseline");
            const challenger = challengers[0];
            const baseline = baselines[0];

            const bestName = bestBrierName(r.models);

            const pnl = fmtPnL(r.resolution.champion_pnl_usd);
            const dateShort = r.ts_utc
              ? r.ts_utc.slice(0, 10) // YYYY-MM-DD
              : "—";
            const bin = r.target_market_ticker.split("-").pop() ?? "—";
            const eventShort = shortEvent(r.event_ticker, r.event_title);

            return (
              <tr
                key={r.run_id}
                className="border-b border-border/50 last:border-0 align-top"
              >
                <td className="px-3 py-3 text-accent font-semibold">{r.run_id}</td>
                <td className="px-3 py-3 text-muted whitespace-nowrap">
                  {dateShort}
                </td>
                <td className="px-3 py-3 text-text">
                  <span className="block">{eventShort}</span>
                  <span className="block text-[10px] text-muted" title={r.event_title}>
                    {bin}
                  </span>
                </td>
                <td className="px-3 py-3 text-text">{r.position.side ?? "—"}</td>
                <td className="px-3 py-3 text-right">
                  <ModelCell
                    model={champion}
                    isBest={!!champion && bestName === champion.name}
                  />
                </td>
                <td className="px-3 py-3 text-right">
                  <ModelCell
                    model={challenger}
                    isBest={!!challenger && bestName === challenger.name}
                  />
                </td>
                <td className="px-3 py-3 text-right">
                  <ModelCell
                    model={baseline}
                    isBest={!!baseline && bestName === baseline.name}
                  />
                </td>
                <td className="px-3 py-3 text-right text-warn">
                  {fmtPct(r.kalshi_mid_at_entry)}
                </td>
                <td className="px-3 py-3">
                  <OutcomeBadge
                    status={r.resolution.status}
                    outcome={r.resolution.outcome}
                    won={r.resolution.champion_won}
                    labels={{
                      pending: t.pending,
                      win: t.win,
                      loss: t.loss,
                    }}
                  />
                </td>
                <td className={`px-3 py-3 text-right ${pnl.tone}`}>
                  {pnl.text}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <div className="border-t border-border/50 px-3 py-2 text-[10px] text-muted font-mono">
        {t.footer}
      </div>
    </div>
  );
}
