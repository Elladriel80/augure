import type { Metadata } from "next";

import { BacktestRunsTable } from "@/components/BacktestRunsTable";
import { BrierChart } from "@/components/BrierChart";
import { FeatureRegistryTable } from "@/components/FeatureRegistryTable";
import { FilterBar } from "@/components/FilterBar";
import { InformedFactorsView } from "@/components/InformedFactorsView";
import { LatestRunCard } from "@/components/LatestRunCard";
import { LayerToggle, type Level } from "@/components/LayerToggle";
import { LiveRunsTable } from "@/components/LiveRunsTable";
import { NEffSection } from "@/components/NEffSection";
import { PublicWeatherCard } from "@/components/PublicWeatherCard";
import { RunHistoryTable } from "@/components/RunHistoryTable";
import { getDict } from "@/lib/i18n";
import type {
  BacktestRunRecord,
  FeatureRecord,
  HybridSample,
  LiveRunRecord,
  PaperBetsSummary,
  RunRecord,
} from "@/lib/manifest";
import { seriesFromEventTicker } from "@/lib/manifest";
import { loadManifest } from "@/lib/manifest.server";

export const metadata: Metadata = {
  title: "Predictor — aratea",
  description:
    "Predictor learning loop, presented in three layers: public, informed, expert.",
  robots: { index: false, follow: false },
};

// Reading searchParams + the locale cookie via getDict() promotes this page to
// dynamic. That's intended — the layer toggle is a query param, not a build
// constant.
export const dynamic = "force-dynamic";

interface PredictorPageProps {
  searchParams: Promise<{
    level?: string;
    series?: string;
    status?: string;
  }>;
}

function parseLevel(raw: string | undefined): Level {
  if (raw === "2") return 2;
  if (raw === "3") return 3;
  return 1; // default: meet the quidam first
}

function hrefForLevel(level: Level): string {
  return `/predictor?level=${level}`;
}

function parseCsvParam(raw: string | undefined): string[] {
  if (!raw) return [];
  return raw.split(",").filter(Boolean);
}

function filterLiveRuns(
  runs: LiveRunRecord[],
  series: string[],
  status: string[],
): LiveRunRecord[] {
  return runs.filter((r) => {
    if (
      series.length > 0 &&
      !series.includes(seriesFromEventTicker(r.event_ticker))
    ) {
      return false;
    }
    if (status.length > 0 && !status.includes(r.resolution.status)) {
      return false;
    }
    return true;
  });
}

function filterBacktestRuns(
  runs: BacktestRunRecord[],
  series: string[],
  status: string[],
): BacktestRunRecord[] {
  return runs.filter((r) => {
    if (series.length > 0 && !series.includes(r.series)) return false;
    if (status.length > 0 && !status.includes(r.resolution.status)) return false;
    return true;
  });
}

function distinctSeries(
  liveRuns: LiveRunRecord[],
  backtestRuns: BacktestRunRecord[],
): string[] {
  const acc = new Set<string>();
  for (const r of liveRuns) acc.add(seriesFromEventTicker(r.event_ticker));
  for (const r of backtestRuns) acc.add(r.series);
  return [...acc].sort();
}

export default async function PredictorPage({
  searchParams,
}: PredictorPageProps) {
  const dict = await getDict();
  const manifest = await loadManifest();
  const params = await searchParams;
  const level: Level = parseLevel(params.level);

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

  const { features, runs, kalshi_mid_reference } = manifest;
  const liveRuns = manifest.live_runs ?? [];
  const backtestRuns = manifest.backtest_runs ?? [];
  const hybridSample = manifest.hybrid_sample;
  const seriesFilter = parseCsvParam(params.series);
  const statusFilter = parseCsvParam(params.status);
  const filteredLiveRuns = filterLiveRuns(liveRuns, seriesFilter, statusFilter);
  const filteredBacktestRuns = filterBacktestRuns(
    backtestRuns,
    seriesFilter,
    statusFilter,
  );
  const seriesOptions = distinctSeries(liveRuns, backtestRuns);
  // Latest run pickers ignore the filters — they're "the most recent record"
  // not "the most recent record matching this view". Same in Layer 1 / Layer 2.
  const latestRun =
    runs.length > 0 ? [...runs].sort((a, b) => b.ts.localeCompare(a.ts))[0] : null;
  const latestLiveRun =
    liveRuns.length > 0
      ? [...liveRuns].sort((a, b) => b.run_id.localeCompare(a.run_id))[0]
      : null;

  const layers = dict.predictor.layers;
  const toggle = (
    <LayerToggle
      current={level}
      labels={{
        aria: layers.aria,
        levels: [
          { value: 1, label: layers.level_1.label, hint: layers.level_1.hint },
          { value: 2, label: layers.level_2.label, hint: layers.level_2.hint },
          { value: 3, label: layers.level_3.label, hint: layers.level_3.hint },
        ],
      }}
    />
  );

  return (
    <div className="space-y-8">
      {/* PAGE HEADER — common to all three layers */}
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-2xl font-mono font-semibold mb-2">
            {dict.predictor.title}
          </h1>
          <p className="text-sm text-muted max-w-3xl">{dict.predictor.intro}</p>
        </div>
        {toggle}
      </header>

      {level === 1 ? (
        <Layer1 latestLiveRun={latestLiveRun} whyHref={hrefForLevel(2)} />
      ) : null}

      {level === 2 ? (
        <Layer2
          latestLiveRun={latestLiveRun}
          runs={runs}
          kalshiMidReference={kalshi_mid_reference}
          hybridSample={hybridSample}
          moreHref={hrefForLevel(3)}
        />
      ) : null}

      {level === 3 ? (
        <Layer3
          dict={dict}
          features={features}
          runs={runs}
          liveRuns={filteredLiveRuns}
          backtestRuns={filteredBacktestRuns}
          backtestRunsTotal={manifest.backtest_runs_total ?? backtestRuns.length}
          hybridSample={hybridSample}
          seriesOptions={seriesOptions}
          latestRun={latestRun}
          kalshiMidReference={kalshi_mid_reference}
          paperBetsSummary={manifest.paper_bets_summary}
          generatedAt={manifest.generated_at}
          schemaVersion={manifest.schema_version}
        />
      ) : null}
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/*  Layer 1 — Public weather card                                             */
/* -------------------------------------------------------------------------- */

function Layer1({
  latestLiveRun,
  whyHref,
}: {
  latestLiveRun: LiveRunRecord | null;
  whyHref: string;
}) {
  return <PublicWeatherCard run={latestLiveRun} whyHref={whyHref} />;
}

/* -------------------------------------------------------------------------- */
/*  Layer 2 — Informed view                                                   */
/* -------------------------------------------------------------------------- */

function Layer2({
  latestLiveRun,
  runs,
  kalshiMidReference,
  hybridSample,
  moreHref,
}: {
  latestLiveRun: LiveRunRecord | null;
  runs: RunRecord[];
  kalshiMidReference: number | null;
  hybridSample: HybridSample | undefined;
  moreHref: string;
}) {
  return (
    <InformedFactorsView
      liveRun={latestLiveRun}
      runs={runs}
      kalshiMidReference={kalshiMidReference}
      hybridSample={hybridSample}
      moreHref={moreHref}
    />
  );
}

/* -------------------------------------------------------------------------- */
/*  Layer 3 — Expert view (the original page, intact)                         */
/* -------------------------------------------------------------------------- */

interface Layer3Props {
  dict: Awaited<ReturnType<typeof getDict>>;
  features: FeatureRecord[];
  runs: RunRecord[];
  liveRuns: LiveRunRecord[];
  backtestRuns: BacktestRunRecord[];
  backtestRunsTotal: number;
  hybridSample: HybridSample | undefined;
  seriesOptions: string[];
  latestRun: RunRecord | null;
  kalshiMidReference: number | null;
  paperBetsSummary: PaperBetsSummary;
  generatedAt: string;
  schemaVersion: number;
}

function Layer3({
  dict,
  features,
  runs,
  liveRuns,
  backtestRuns,
  backtestRunsTotal,
  hybridSample,
  seriesOptions,
  latestRun,
  kalshiMidReference,
  paperBetsSummary,
  generatedAt,
  schemaVersion,
}: Layer3Props) {
  const activeCount = features.filter((f) => f.current_status === "active").length;
  const experimentalCount = features.filter(
    (f) => f.current_status === "experimental",
  ).length;
  const droppedCount = features.filter((f) => f.current_status === "dropped").length;

  const statusOptions = [
    dict.predictor.filters.status_open,
    dict.predictor.filters.status_resolved,
  ];

  return (
    <div className="space-y-10">
      <section>
        <p className="text-sm text-muted max-w-3xl">{dict.predictor.expert.intro}</p>
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
            value={`${paperBetsSummary.n_open} / ${paperBetsSummary.n_resolved}`}
            hint={dict.predictor.counters.phase_1_hint(
              paperBetsSummary.phase_1_counter,
            )}
          />
        </div>
        <p className="mt-3 text-[11px] text-muted/80 font-mono">
          {dict.predictor.manifest_generated(generatedAt, schemaVersion)}
        </p>
      </section>

      <NEffSection sample={hybridSample} />

      <FilterBar
        seriesOptions={seriesOptions}
        statusOptions={statusOptions}
        labels={{
          series_label: dict.predictor.filters.series_label,
          status_label: dict.predictor.filters.status_label,
          clear: dict.predictor.filters.clear,
        }}
      />

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
        <BrierChart runs={runs} kalshiReference={kalshiMidReference} />
      </section>

      <section>
        <h2 className="text-xl font-mono font-semibold mb-3">
          {dict.predictor.sections.backtest_title}
        </h2>
        <p className="text-sm text-muted mb-3 max-w-3xl">
          {dict.predictor.sections.backtest_desc}
        </p>
        <BacktestRunsTable
          runs={backtestRuns}
          total={backtestRunsTotal}
          labels={dict.components.backtest_table}
        />
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
