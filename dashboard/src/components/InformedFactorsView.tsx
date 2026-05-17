import type { Route } from "next";
import Link from "next/link";

import { getDict } from "@/lib/i18n";
import type { HybridSample, LiveRunRecord, RunRecord } from "@/lib/manifest";

import { BrierChart } from "./BrierChart";
import { NEffSection } from "./NEffSection";

interface Props {
  /** Most recent live paper-trade run, used to surface per-component p_yes. */
  liveRun: LiveRunRecord | null;
  /** All training runs, fed into the Brier trajectory chart. */
  runs: RunRecord[];
  /** Most recent kalshi_mid Brier (chart reference line). */
  kalshiMidReference: number | null;
  /** Hybrid effective sample for the compact N_eff badge at top. */
  hybridSample: HybridSample | undefined;
  /** Href that takes the reader from "components" to "everything". */
  moreHref: string;
}

function fmtPct(p: number | null | undefined, digits = 1): string {
  if (p === null || p === undefined || Number.isNaN(p)) return "—";
  return `${(p * 100).toFixed(digits)}%`;
}

interface ComponentMeta {
  label: string;
  desc: string;
  tone: string;
  /**
   * Substrings to match against the live model name. The first match wins,
   * so order matters: more specific names first.
   */
  match: string[];
}

/** Pick a friendly label for a model name like "learned_v2", "climatology", "ensemble_mean". */
function classifyModel(
  name: string,
  metas: { id: string; meta: ComponentMeta }[],
): { id: string; meta: ComponentMeta } | null {
  const lower = name.toLowerCase();
  for (const entry of metas) {
    if (entry.meta.match.some((needle) => lower.includes(needle))) {
      return entry;
    }
  }
  return null;
}

export async function InformedFactorsView({
  liveRun,
  runs,
  kalshiMidReference,
  hybridSample,
  moreHref,
}: Props) {
  const dict = await getDict();
  const t = dict.predictor.informed;
  const layers = dict.predictor.layers;

  const componentMetas: { id: string; meta: ComponentMeta }[] = [
    {
      id: "climatology",
      meta: {
        label: t.component_climatology,
        desc: t.component_climatology_desc,
        tone: "border-border bg-bg/40",
        match: ["climatology", "climato"],
      },
    },
    {
      id: "forecast_blend",
      meta: {
        label: t.component_forecast_blend,
        desc: t.component_forecast_blend_desc,
        tone: "border-border bg-bg/40",
        match: ["forecast_blend", "forecast", "blend", "ndfd"],
      },
    },
    {
      id: "ensemble",
      meta: {
        label: t.component_ensemble,
        desc: t.component_ensemble_desc,
        tone: "border-border bg-bg/40",
        match: ["ensemble"],
      },
    },
    {
      id: "learned",
      meta: {
        label: t.component_learned,
        desc: t.component_learned_desc,
        tone: "border-accent/40 bg-accent/10",
        match: ["learned", "learn"],
      },
    },
  ];

  // Build the component rows shown in the "four estimates" block.
  // Drop any model whose name signals it's a re-statement of the Kalshi mid
  // (e.g. `kalshi_mid_baseline`) — that's the market, shown separately below
  // as the benchmark, not one of Aratea's own estimates.
  type ComponentRow = {
    label: string;
    desc: string;
    pct: number | null;
    tone: string;
    rawName: string;
    role: string | null;
  };

  const componentRows: ComponentRow[] = [];
  if (liveRun) {
    for (const model of liveRun.models) {
      const lower = model.name.toLowerCase();
      // Skip kalshi_mid restated as a model — already in the market block.
      if (lower.includes("kalshi") && lower.includes("mid")) continue;

      const classified = classifyModel(model.name, componentMetas);
      const isChampion = (model.role ?? "").toLowerCase() === "champion";
      componentRows.push({
        label: classified?.meta.label ?? model.name,
        desc: classified?.meta.desc ?? "",
        pct: model.p_yes,
        // Highlight the actual champion (the one that places the bet), not
        // the learned model — they're often different during Phase A.
        tone: isChampion
          ? "border-accent/50 bg-accent/15"
          : classified?.meta.tone ?? "border-border bg-bg/40",
        rawName: model.name,
        role: model.role ?? null,
      });
    }
  }

  function roleLabel(role: string | null): string | null {
    const r = (role ?? "").toLowerCase();
    if (r === "champion") return t.role_champion;
    if (r === "challenger") return t.role_challenger;
    if (r === "baseline") return t.role_baseline;
    return null;
  }

  function roleTone(role: string | null): string {
    const r = (role ?? "").toLowerCase();
    if (r === "champion")
      return "border-accent/50 bg-accent/15 text-accent";
    if (r === "challenger")
      return "border-border bg-bg text-muted";
    if (r === "baseline")
      return "border-border bg-bg text-muted";
    return "border-border bg-bg text-muted";
  }

  const marketPct = liveRun?.kalshi_mid_at_entry ?? null;

  return (
    <div className="space-y-10">
      <section>
        <h2 className="text-xl font-mono font-semibold mb-2">{t.heading}</h2>
        <p className="text-sm text-muted max-w-3xl">{t.intro}</p>
      </section>

      <NEffSection sample={hybridSample} compact />


      {componentRows.length === 0 ? (
        <div className="rounded-md border border-border bg-panel p-4 text-sm text-muted font-mono">
          {t.no_run}
        </div>
      ) : (
        <section>
          <h3 className="text-sm uppercase tracking-wider text-muted font-mono mb-3">
            {t.components_subheading}
          </h3>
          <p className="text-[11px] text-muted/80 font-mono mb-3 max-w-3xl leading-relaxed">
            {t.role_explainer}
          </p>
          <ul className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {componentRows.map((row, idx) => (
              <li
                key={`${row.label}-${idx}`}
                className={`rounded-md border p-4 relative ${row.tone}`}
              >
                <div className="flex items-baseline justify-between gap-3">
                  <div className="font-semibold text-text">
                    {row.label}
                    {roleLabel(row.role) ? (
                      <span
                        className={`ml-2 align-middle inline-block rounded border px-1.5 py-0.5 text-[9px] font-mono uppercase tracking-wider ${roleTone(
                          row.role,
                        )}`}
                      >
                        {roleLabel(row.role)}
                      </span>
                    ) : null}
                  </div>
                  <div className="font-mono text-lg text-accent">
                    {fmtPct(row.pct)}
                  </div>
                </div>
                {row.desc ? (
                  <p className="text-xs text-muted mt-1 leading-relaxed">
                    {row.desc}
                  </p>
                ) : null}
                <p className="text-[10px] text-muted/60 font-mono mt-2">
                  <code>{row.rawName}</code>
                </p>
              </li>
            ))}
          </ul>
        </section>
      )}

      {marketPct !== null ? (
        <section>
          <h3 className="text-sm uppercase tracking-wider text-muted font-mono mb-3">
            {t.market_subheading}
          </h3>
          <div className="rounded-md border border-warn/40 bg-warn/10 p-4">
            <div className="flex items-baseline justify-between gap-3">
              <div className="font-semibold text-text">{t.market_label}</div>
              <div className="font-mono text-lg text-warn">
                {fmtPct(marketPct)}
              </div>
            </div>
            <p className="text-xs text-muted mt-1 leading-relaxed">
              {t.market_desc}
            </p>
          </div>
          <p className="text-[11px] text-muted/70 font-mono mt-2 max-w-2xl">
            {t.market_subheading_hint}
          </p>
        </section>
      ) : null}

      <section>
        <h3 className="text-sm uppercase tracking-wider text-muted font-mono mb-3">
          {t.brier_chart_heading}
        </h3>
        <p className="text-sm text-muted max-w-3xl mb-3">{t.brier_intro}</p>
        <BrierChart runs={runs} kalshiReference={kalshiMidReference} />
      </section>

      <div>
        <Link
          href={moreHref as Route}
          className="inline-block rounded-md border border-accent/40 bg-accent/10 px-3 py-2 text-xs font-mono text-accent hover:bg-accent/20"
        >
          {layers.cta_more}
        </Link>
      </div>
    </div>
  );
}
