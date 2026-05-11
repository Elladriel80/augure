import { formatBrier, formatDelta, formatRunTimestamp } from "@/lib/manifest";
import type { RunRecord } from "@/lib/manifest";
import { VerdictBadge } from "./VerdictBadge";

interface Props {
  run: RunRecord;
}

export function LatestRunCard({ run }: Props) {
  const gapNegative =
    typeof run.gap_vs_kalshi_mid === "number" && run.gap_vs_kalshi_mid < 0;
  const gapToneClass = gapNegative
    ? "text-ok"
    : run.gap_vs_kalshi_mid === 0
      ? "text-warn"
      : "text-err";

  return (
    <div className="rounded-md border border-border bg-panel p-5 flex flex-col gap-4">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div className="text-xs uppercase tracking-wider text-muted">
            Latest training run
          </div>
          <div className="text-lg font-mono mt-1">
            feature set{" "}
            <span className="text-accent">{run.feature_set ?? "—"}</span>
            <span className="text-muted"> · </span>
            <span className="text-muted">{formatRunTimestamp(run.ts)}</span>
          </div>
        </div>
        <VerdictBadge verdict={run.verdict} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 font-mono text-sm">
        <Metric label="n_train" value={run.n_train ?? "—"} />
        <Metric label="n_test" value={run.n_test ?? "—"} />
        <Metric label="Brier train" value={formatBrier(run.brier_train)} />
        <Metric
          label="Brier test"
          value={formatBrier(run.brier_test)}
          accent="accent"
        />
        <Metric
          label="Brier kalshi_mid"
          value={formatBrier(run.brier_kalshi_mid_test)}
          accent="warn"
        />
        <Metric
          label="gap (test − kalshi_mid)"
          value={formatDelta(run.gap_vs_kalshi_mid)}
          className={gapToneClass}
        />
        <Metric label="log-loss test" value={formatBrier(run.log_loss_test)} />
        <Metric
          label="log-loss kalshi_mid"
          value={formatBrier(run.log_loss_kalshi_mid_test)}
        />
      </div>

      {run.notes ? (
        <div className="text-xs text-muted font-mono leading-relaxed border-t border-border pt-3">
          <span className="uppercase tracking-wider text-muted/70">notes</span>
          <p className="mt-1 text-text/80 whitespace-pre-wrap">{run.notes}</p>
        </div>
      ) : null}
    </div>
  );
}

function Metric({
  label,
  value,
  accent,
  className,
}: {
  label: string;
  value: React.ReactNode;
  accent?: "accent" | "warn";
  className?: string;
}) {
  const tone =
    accent === "accent"
      ? "text-accent"
      : accent === "warn"
        ? "text-warn"
        : "text-text";
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-muted">
        {label}
      </div>
      <div className={`font-semibold ${className ?? tone}`}>{value}</div>
    </div>
  );
}
