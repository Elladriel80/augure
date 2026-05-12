/**
 * Types + formatting helpers for `public/predictor_manifest.json`. Pure
 * module — no runtime deps. The build-time loader that touches `node:fs`
 * lives in `manifest.server.ts`; this file is safe to import from client
 * components.
 */

export type FeatureStatus = "experimental" | "active" | "dropped" | "retired";
export type Verdict = "MARKET" | "ENSEMBLE" | "LEARNED" | "TIE";

export interface FeatureHistoryEntry {
  run_ts: string | null;
  feature_set: string | null;
  brier_delta: number | null;
  status: "active" | "dropped" | null;
}

export interface FeatureRecord {
  name: string;
  hypothesis: string;
  source: string;
  date_added: string;
  current_status: FeatureStatus | string;
  current_brier_delta: number | null;
  current_brier_delta_raw: string;
  history: FeatureHistoryEntry[];
}

export interface RunRecord {
  ts: string;
  feature_set: string;
  feature_names: string[];
  n_train: number | null;
  n_test: number | null;
  train_date_range: [string, string] | null;
  test_date_range: [string, string] | null;
  brier_train: number | null;
  brier_test: number | null;
  brier_kalshi_mid_test: number | null;
  log_loss_train: number | null;
  log_loss_test: number | null;
  log_loss_kalshi_mid_test: number | null;
  gap_vs_kalshi_mid: number | null;
  verdict: Verdict | string;
  notes: string;
}

export interface PaperBetsSummary {
  n_open: number;
  n_resolved: number;
  pnl_usd_cumulative: number;
  phase_1_counter: string;
}

export type LiveRunRole = "champion" | "challenger" | "baseline";

export interface LiveRunModel {
  name: string;
  role: LiveRunRole | string | null;
  method: string | null;
  p_yes: number | null;
  brier: number | null;
  won: boolean | null;
  pnl_usd: number | null;
  pnl_type: "actual" | "theoretical" | string | null;
}

export interface LiveRunPosition {
  side: "YES" | "NO" | string | null;
  n_contracts: number | null;
  entry_price: number | null;
  size_usd: number | null;
  entry_price_yes_cents: number | null;
  entry_price_no_cents: number | null;
}

export interface LiveRunResolution {
  status: "open" | "resolved" | string;
  outcome: "yes" | "no" | null;
  observed_range_f: [number, number] | null;
  winning_bin_ticker: string | null;
  ts_utc: string | null;
  champion_pnl_usd: number | null;
  champion_won: boolean | null;
}

export interface LiveRunRecord {
  run_id: string;
  schema_version: number;
  ts_utc: string | null;
  event_ticker: string;
  event_title: string;
  target_market_ticker: string;
  champion_name: string;
  kalshi_mid_at_entry: number | null;
  position: LiveRunPosition;
  models: LiveRunModel[];
  resolution: LiveRunResolution;
}

export interface PredictorManifest {
  generated_at: string;
  schema_version: number;
  features: FeatureRecord[];
  runs: RunRecord[];
  live_runs?: LiveRunRecord[];
  paper_bets_summary: PaperBetsSummary;
  kalshi_mid_reference: number | null;
}

/** Format a `YYYYMMDDTHHMMSSZ` stamp as `2026-05-11 13:08 UTC`. */
export function formatRunTimestamp(ts: string | null | undefined): string {
  if (!ts) return "—";
  const m = ts.match(/^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})Z$/);
  if (!m) return ts;
  const [, y, mo, d, h, mi] = m;
  return `${y}-${mo}-${d} ${h}:${mi} UTC`;
}

/** Format a Brier score (4 fraction digits). */
export function formatBrier(b: number | null | undefined): string {
  if (b === null || b === undefined || Number.isNaN(b)) return "—";
  return b.toFixed(4);
}

/** Format a signed delta with explicit sign. Used for gap vs kalshi_mid. */
export function formatDelta(d: number | null | undefined, digits = 4): string {
  if (d === null || d === undefined || Number.isNaN(d)) return "—";
  const sign = d > 0 ? "+" : d < 0 ? "−" : "±";
  return `${sign}${Math.abs(d).toFixed(digits)}`;
}
