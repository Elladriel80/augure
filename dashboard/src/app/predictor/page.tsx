import type { Metadata } from "next";

import { BrierChart } from "@/components/BrierChart";
import { FeatureRegistryTable } from "@/components/FeatureRegistryTable";
import { LatestRunCard } from "@/components/LatestRunCard";
import { RunHistoryTable } from "@/components/RunHistoryTable";
import { loadManifest } from "@/lib/manifest.server";

export const metadata: Metadata = {
  title: "Predictor — augure",
  description:
    "Predictor learning loop: features under test, per-run Brier vs market, decision history.",
  robots: { index: false, follow: false },
};

export const dynamic = "force-static";

export default async function PredictorPage() {
  const manifest = await loadManifest();

  if (!manifest) {
    return (
      <div className="rounded-md border border-warn/40 bg-warn/10 p-6 font-mono">
        <h1 className="text-xl mb-2 text-warn">Predictor manifest not found</h1>
        <p className="text-sm text-muted">
          The build step that generates{" "}
          <code className="text-text">public/predictor_manifest.json</code> did
          not run. Run <code className="text-text">npm run manifest</code> (or a
          full <code className="text-text">npm run build</code>) and reload.
        </p>
      </div>
    );
  }

  const { features, runs, paper_bets_summary, kalshi_mid_reference } = manifest;
  const latestRun = runs.length > 0 ? [...runs].sort((a, b) => b.ts.localeCompare(a.ts))[0] : null;
  const activeCount = features.filter((f) => f.current_status === "active").length;
  const experimentalCount = features.filter(
    (f) => f.current_status === "experimental",
  ).length;
  const droppedCount = features.filter((f) => f.current_status === "dropped").length;

  return (
    <div className="space-y-10">
      <section>
        <h1 className="text-2xl font-mono font-semibold mb-2">
          Predictor — learning loop
        </h1>
        <p className="text-sm text-muted max-w-3xl">
          Augure is a weather-factor discovery engine. Every named feature here
          is a hypothesis; every training run measures whether it carries
          signal. The bench is the same row-set <code className="text-text">
          kalshi_mid</code> Brier — beat the market, on its own ground.
        </p>
        <div className="mt-4 grid grid-cols-2 md:grid-cols-5 gap-3 text-sm font-mono">
          <Counter label="Features tracked" value={features.length} />
          <Counter label="Active" value={activeCount} tone="text-ok" />
          <Counter
            label="Experimental"
            value={experimentalCount}
            tone="text-accent"
          />
          <Counter label="Dropped" value={droppedCount} tone="text-err" />
          <Counter
            label="Paper bets (open / resolved)"
            value={`${paper_bets_summary.n_open} / ${paper_bets_summary.n_resolved}`}
            hint={`Phase 1: ${paper_bets_summary.phase_1_counter}`}
          />
        </div>
        <p className="mt-3 text-[11px] text-muted/80 font-mono">
          Manifest generated at {manifest.generated_at} (schema v
          {manifest.schema_version}).
        </p>
      </section>

      <section>
        <h2 className="text-xl font-mono font-semibold mb-3">
          A. Latest training run
        </h2>
        {latestRun ? (
          <LatestRunCard run={latestRun} />
        ) : (
          <div className="rounded-md border border-border bg-panel p-4 text-sm text-muted font-mono">
            No training runs yet.
          </div>
        )}
      </section>

      <section>
        <h2 className="text-xl font-mono font-semibold mb-3">
          B. Named factors
        </h2>
        <p className="text-sm text-muted mb-3 max-w-3xl">
          Each row is a named hypothesis. Brier Δ is the leave-one-out test
          delta from the most recent run — sort by it to see what carried the
          model. Click a row for the full hypothesis, source, and per-run
          history.
        </p>
        <FeatureRegistryTable features={features} />
      </section>

      <section>
        <h2 className="text-xl font-mono font-semibold mb-3">
          C. Run history
        </h2>
        <p className="text-sm text-muted mb-3 max-w-3xl">
          Every training run, most recent first. A run with Brier test below
          Brier kalshi_mid on the same rows means the model has signal beyond
          the market mid.
        </p>
        <RunHistoryTable runs={runs} />
      </section>

      <section>
        <h2 className="text-xl font-mono font-semibold mb-3">
          D. Brier trajectory
        </h2>
        <p className="text-sm text-muted mb-3 max-w-3xl">
          Learned model (test) vs kalshi_mid (same test rows) across all
          runs. Dashed horizontal line is the most recent kalshi_mid Brier as
          all-time reference; vertical dashed markers flag a feature-set bump
          (v0 → v1 → v2 …).
        </p>
        <BrierChart runs={runs} kalshiReference={kalshi_mid_reference} />
      </section>
    </div>
  );
}

function Counter({
  label,
  value,
  tone,
  hint,
}: {
  label: string;
  value: React.ReactNode;
  tone?: string;
  hint?: string;
}) {
  return (
    <div className="rounded-md border border-border bg-panel p-3">
      <div className="text-[10px] uppercase tracking-wider text-muted">
        {label}
      </div>
      <div className={`text-lg font-semibold ${tone ?? "text-text"}`}>
        {value}
      </div>
      {hint ? <div className="text-[10px] text-muted mt-0.5">{hint}</div> : null}
    </div>
  );
}
