import type { Metadata } from "next";

import { BrierChart } from "@/components/BrierChart";
import { FeatureRegistryTable } from "@/components/FeatureRegistryTable";
import { LatestRunCard } from "@/components/LatestRunCard";
import { LiveRunsTable } from "@/components/LiveRunsTable";
import { RunHistoryTable } from "@/components/RunHistoryTable";
import { getDict } from "@/lib/i18n";
import { loadManifest } from "@/lib/manifest.server";

export const metadata: Metadata = {
  title: "Predictor — aratea",
  description:
    "Predictor learning loop: features under test, per-run Brier vs market, decision history.",
  robots: { index: false, follow: false },
};

// Note: this page used to be `force-static`. Reading the locale cookie via
// getDict() promotes it to dynamic — that's fine, the manifest is loaded from
// disk and there are no per-request chain calls here.
export const dynamic = "force-dynamic";

export default async function PredictorPage() {
  const dict = await getDict();
  const manifest = await loadManifest();

  if (!manifest) {
    return (
      <div className="rounded-md border border-warn/40 bg-warn/10 p-6 font-mono">
        <h1 className="text-xl mb-2 text-warn">
          {dict.predictor.manifest_missing_title}
        </h1>
        <p className="text-sm text-muted">{dict.predictor.manifest_missing_body}</p>
      </div>
    );
  }

  const { features, runs, paper_bets_summary, kalshi_mid_reference } = manifest;
  const liveRuns = manifest.live_runs ?? [];
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
          {dict.predictor.title}
        </h1>
        <p className="text-sm text-muted max-w-3xl">{dict.predictor.intro}</p>
        <div className="mt-4 grid grid-cols-2 md:grid-cols-5 gap-3 text-sm font-mono">
          <Counter
            label={dict.predictor.counters.features_tracked}
            value={features.length}
          />
          <Counter
            label={dict.predictor.counters.active}
            value={activeCount}
            tone="text-ok"
          />
          <Counter
            label={dict.predictor.counters.experimental}
            value={experimentalCount}
            tone="text-accent"
          />
          <Counter
            label={dict.predictor.counters.dropped}
            value={droppedCount}
            tone="text-err"
          />
          <Counter
            label={dict.predictor.counters.paper_bets}
            value={`${paper_bets_summary.n_open} / ${paper_bets_summary.n_resolved}`}
            hint={dict.predictor.counters.phase_1_hint(
              paper_bets_summary.phase_1_counter,
            )}
          />
        </div>
        <p className="mt-3 text-[11px] text-muted/80 font-mono">
          {dict.predictor.manifest_generated(
            manifest.generated_at,
            manifest.schema_version,
          )}
        </p>
      </section>

      <section>
        <h2 className="text-xl font-mono font-semibold mb-3">
          {dict.predictor.sections.live_title}
        </h2>
        <p className="text-sm text-muted mb-3 max-w-3xl">
          {dict.predictor.sections.live_desc}
        </p>
        <LiveRunsTable runs={liveRuns} />
      </section>

      <section>
        <h2 className="text-xl font-mono font-semibold mb-3">
          {dict.predictor.sections.factors_title}
        </h2>
        <p className="text-sm text-muted mb-3 max-w-3xl">
          {dict.predictor.sections.factors_desc}
        </p>
        <FeatureRegistryTable
          features={features}
          labels={dict.components.feature_table}
          footer={dict.components.feature_table_footer(
            <span className="text-ok">
              {dict.components.feature_table_footer_carried}
            </span>,
            <span className="text-err">
              {dict.components.feature_table_footer_noise}
            </span>,
          )}
        />
      </section>

      <section>
        <h2 className="text-xl font-mono font-semibold mb-3">
          {dict.predictor.sections.latest_title}
        </h2>
        <p className="text-sm text-muted mb-3 max-w-3xl">
          {dict.predictor.sections.latest_desc}
        </p>
        {latestRun ? (
          <LatestRunCard run={latestRun} />
        ) : (
          <div className="rounded-md border border-border bg-panel p-4 text-sm text-muted font-mono">
            {dict.predictor.sections.latest_empty}
          </div>
        )}
      </section>

      <section>
        <h2 className="text-xl font-mono font-semibold mb-3">
          {dict.predictor.sections.history_title}
        </h2>
        <p className="text-sm text-muted mb-3 max-w-3xl">
          {dict.predictor.sections.history_desc}
        </p>
        <RunHistoryTable runs={runs} />
      </section>

      <section>
        <h2 className="text-xl font-mono font-semibold mb-3">
          {dict.predictor.sections.brier_title}
        </h2>
        <p className="text-sm text-muted mb-3 max-w-3xl">
          {dict.predictor.sections.brier_desc}
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
