import { getDict } from "@/lib/i18n";
import type { HybridSample } from "@/lib/manifest";

const CONVENTION_URL =
  "https://github.com/Elladriel80/Aratea/blob/main/predictor/runs/CONVENTION.md#6bis-hybrid-effective-sample-for-secondary-decisions";

interface Props {
  sample: HybridSample | undefined;
  /** Compact rendering for Layer 2 (big number + one-line hint, no
   *  methodology note and no convention link). */
  compact?: boolean;
}

/**
 * Hybrid effective sample size dashboard (CONVENTION §6.bis).
 *
 * `N_effective = N_live + α · N_backtest_strict` — used for secondary
 * decisions only. The Phase 1 go/no-go gate stays strictly on N_live; this
 * widget reports both numbers so the reader can keep them separate.
 */
export async function NEffSection({ sample, compact }: Props) {
  const dict = await getDict();
  const t = dict.predictor.n_eff_section;

  if (!sample) {
    return null;
  }

  const reached = sample.n_live >= sample.phase_1_target;

  if (compact) {
    return (
      <section className="rounded-md border border-border bg-panel p-4">
        <div className="flex items-baseline justify-between gap-4 flex-wrap">
          <div>
            <div className="text-[10px] uppercase tracking-wider text-muted font-mono">
              {t.title}
            </div>
            <div className="text-3xl font-mono font-semibold text-accent mt-1">
              {sample.n_effective.toFixed(1)}
            </div>
          </div>
          <div className="text-xs text-muted font-mono leading-relaxed max-w-md">
            {t.compact_hint(
              sample.n_live,
              sample.alpha_backtest,
              sample.n_backtest_strict,
            )}
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="rounded-md border border-accent/30 bg-accent/5 p-5">
      <div className="flex items-baseline justify-between gap-4 flex-wrap mb-3">
        <h2 className="text-sm uppercase tracking-wider text-muted font-mono">
          {t.title}
        </h2>
        <span className="text-[10px] font-mono text-muted/80">
          α = {sample.alpha_backtest}
        </span>
      </div>

      <div className="flex items-baseline gap-3 flex-wrap mb-3">
        <span className="text-4xl font-mono font-semibold text-accent">
          {sample.n_effective.toFixed(1)}
        </span>
        <span className="text-sm font-mono text-muted">
          {t.decomposition(
            sample.n_live,
            sample.alpha_backtest,
            sample.n_backtest_strict,
            sample.n_effective,
          )}
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs font-mono mb-4">
        <Metric label={t.n_live} value={sample.n_live} tone="text-text" />
        <Metric
          label={t.n_backtest_strict}
          value={sample.n_backtest_strict}
          tone="text-text"
        />
        <Metric
          label={t.n_backtest_naive_excluded}
          value={sample.n_backtest_naive_excluded}
          tone="text-muted"
        />
      </div>

      <div
        className={`rounded border px-3 py-2 text-xs font-mono mb-3 ${
          reached
            ? "border-ok/40 bg-ok/10 text-ok"
            : "border-border bg-bg/40 text-muted"
        }`}
      >
        {reached
          ? t.phase_1_reached
          : t.phase_1_gate(sample.n_live, sample.phase_1_target)}
      </div>

      <p className="text-[11px] text-muted/80 font-mono leading-relaxed">
        {t.methodology_note}
      </p>

      <a
        href={CONVENTION_URL}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-block mt-3 text-[11px] font-mono text-accent hover:underline"
      >
        {t.convention_link} <span aria-hidden>↗</span>
      </a>
    </section>
  );
}

function Metric({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: string;
}) {
  return (
    <div className="rounded border border-border/60 bg-bg/30 p-2">
      <div className="text-[10px] uppercase tracking-wider text-muted">
        {label}
      </div>
      <div className={`text-base font-semibold ${tone}`}>{value}</div>
    </div>
  );
}
