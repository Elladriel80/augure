import type { ReactNode } from "react";

// English dictionary — source of truth for the Dictionary type.
// Keep keys hierarchical: pages.<route>.<section>.<key>
export const en = {
  layout: {
    nav: {
      predictor: "predictor",
      token: "token",
      rounds: "rounds",
      github: "github ↗",
    },
    footer:
      "Read-only view. No wallet, no transactions. Data refreshed on each page load.",
  },

  common: {
    not_deployed_title: "Contracts not yet deployed",
    not_deployed_body: (
      <>
        Set <code>NEXT_PUBLIC_TOKEN_ADDRESS</code> and{" "}
        <code>NEXT_PUBLIC_REGISTRY_ADDRESS</code> in the environment once the M4
        deployment script has run on Arbitrum Sepolia. The dashboard will then
        read the live state on the next refresh.
      </>
    ),
    not_deployed_short: "Contracts not yet deployed.",
  },

  token: {
    metrics: {
      total_supply: "Total supply",
      total_supply_hint: (wei: string) => `${wei} wei`,
      pause_state: "Pause state",
      paused: "PAUSED",
      active: "active",
      paused_hint:
        "User-to-user transfers are blocked. Mint and burn paths still operate.",
      active_hint: "User-to-user transfers are allowed.",
      contract: "Token contract",
      contract_hint: "Verified on the explorer if `forge verify-contract` was run.",
    },
    cap: {
      heading: (month: string) => `Monthly cap — ${month}`,
      supply_at_month_start: "Supply at month start",
      supply_at_month_start_hint_bound:
        "Snapshot taken at the first executeRound of the month.",
      supply_at_month_start_hint_genesis: "Genesis exception — no snapshot yet.",
      minted_this_month: "Minted this month",
      minted_hint_bound: (pct: string) => `${pct} of the 10% cap`,
      minted_hint_unbound: "Cap not binding this month.",
      remaining_margin: "Remaining margin",
      remaining_unconstrained: "unconstrained",
      remaining_hint_bound: (cap: string) => `Cap = ${cap}`,
      remaining_hint_unbound: "Genesis exception",
    },
    rounds: {
      heading: "Rounds",
      intro: (link: ReactNode) => (
        <>Lifecycle of every monthly mint round. See {link} for the full list.</>
      ),
      intro_link: "the rounds page",
      registry_label: "Registry:",
    },
  },

  rounds: {
    title: "Rounds",
    intro:
      "Every round committed to the registry, ordered by proposal date (most recent first).",
    empty: (
      <>
        No rounds proposed yet. The first one will appear here once the founder
        runs <code className="text-text">script/ProposeGenesisRound.s.sol</code>.
      </>
    ),
    table: {
      round: "Round",
      status: "Status",
      proposed: "Proposed",
      window_ends: "Window ends",
      total_amount: "Total amount",
      beneficiaries: "Beneficiaries",
    },
  },

  round_detail: {
    back: "← all rounds",
    title: "Round detail",
    fields: {
      status: "Status",
      status_numeric: "Status (numeric)",
      proposed_at: "Proposed at (UTC)",
      challenge_window: "Challenge window",
      challenge_window_value: (days: number) => `${days} days`,
      challenge_window_hint: (date: string) => `ends ${date}`,
      beneficiaries: "Beneficiaries",
      total_to_mint: "Total to mint",
    },
    window_label: "Window",
    allocation: "Allocation",
    allocation_table: {
      index: "#",
      beneficiary: "Beneficiary",
      amount: "Amount",
    },
    offchain: "Off-chain artefacts",
    ipfs_uri: "IPFS URI:",
    ipfs_none: "(none)",
    ipfs_help: (
      <>
        The IPFS URI points to the pinned <code>valuation_report.md</code>. The
        roundHash is
        <code> keccak256(abi.encode(beneficiaries, amounts, ipfsUri))</code> —
        anyone can re-derive it from these inputs and verify the on-chain
        commitment.
      </>
    ),
  },

  predictor: {
    title: "Predictor — learning loop",
    intro: (
      <>
        Aratea is a weather-factor discovery engine. Every named feature here is
        a hypothesis; every training run measures whether it carries signal. The
        bench is the same row-set <code className="text-text">kalshi_mid</code>{" "}
        Brier — beat the market, on its own ground.
      </>
    ),
    layers: {
      aria: "Choose detail level",
      level_1: { label: "Level 1 · Public", hint: "What Aratea thinks, in plain words" },
      level_2: { label: "Level 2 · Informed", hint: "Named components, simple stats" },
      level_3: { label: "Level 3 · Expert", hint: "Full registry, Brier, raw runs" },
      cta_why: "Why does Aratea think this? →",
      cta_more: "Show me the full registry →",
    },
    public: {
      heading: "What Aratea thinks today",
      no_run: "No live forecast captured yet — come back after the next daily run.",
      question_label: "Today's question",
      probability_caption: "Aratea's chance the answer is YES",
      market_says: "Market is pricing YES at",
      aratea_says: "Aratea estimates YES at",
      side_yes: "Aratea is betting YES",
      side_no: "Aratea is betting NO",
      agrees: "Aratea agrees with the market",
      disagrees_higher: (gap: string) =>
        `Aratea thinks YES is ${gap} more likely than the market does`,
      disagrees_lower: (gap: string) =>
        `Aratea thinks YES is ${gap} less likely than the market does`,
      confidence_label: "Confidence",
      confidence_low: "Low",
      confidence_medium: "Medium",
      confidence_high: "High",
      confidence_low_hint: "The model is close to a coin flip on this one.",
      confidence_medium_hint: "The model has a clear lean, but not extreme.",
      confidence_high_hint: "The model is very sure of the outcome.",
      explainer_title: "How to read this card",
      explainer_body: (
        <>
          The big number is the probability Aratea gives to the answer being{" "}
          <em>yes</em>. The market number is what people on Kalshi are paying
          for the same bet right now. When the two disagree, Aratea takes the
          side it thinks is mispriced. This is paper-money only during Phase 1
          — no real bet is placed.
        </>
      ),
      window_open: "Bet open — outcome not yet resolved",
      window_resolved_won: "Bet resolved — Aratea won",
      window_resolved_lost: "Bet resolved — Aratea lost",
      champion_caption: (name: string) =>
        `Bet placed by the “${name}” model (current champion).`,
      champion_explainer_title: "Why this model and not another?",
      champion_explainer:
        "Aratea runs several models in parallel. Only the champion places real (paper) bets — challengers run in shadow until they beat the champion's track record. Other models may estimate a different probability — see Level 2 to compare.",
      question_template: (variable: string, location: string, date: string, threshold: string) =>
        `Will the ${variable} in ${location} on ${date} fall in the ${threshold} bin?`,
      threshold_unit_temp_f: (n: string) => `${n}°F`,
      threshold_unit_in: (n: string) => `${n} in`,
      threshold_unit_mph: (n: string) => `${n} mph`,
      threshold_unit_count: (n: string) => `${n} count`,
      threshold_unit_raw: (n: string) => n,
      var_lowt: "lowest temperature",
      var_hight: "highest temperature",
      var_temp: "temperature",
      var_rain: "rainfall",
      var_snow: "snowfall",
      var_wind: "wind speed",
      var_hurr: "hurricane count",
    },
    informed: {
      heading: "What goes into Aratea's number",
      intro: (
        <>
          Aratea runs <em>several</em> forecasting models in parallel. Each card
          below is an independent estimate of the same question: &quot;what's
          the probability this happens?&quot;. The numbers do <strong>not</strong>{" "}
          add up to 100% — they're different ways of guessing the same answer.
          Only one of them — the <strong>champion</strong> — actually places the
          bet; the others run in shadow.
        </>
      ),
      components_subheading: "Aratea's parallel estimates",
      market_subheading: "What the market is paying",
      market_subheading_hint:
        "Shown for comparison. This is the benchmark Aratea is trying to beat — not one of its inputs.",
      component_climatology: "Historical base rate",
      component_climatology_desc:
        "How often this happened on the same day-of-year over the past 15 years. The dumb-but-honest prior every forecast must beat.",
      component_forecast_blend: "Short-term weather model",
      component_forecast_blend_desc:
        "Open-Meteo's deterministic forecast around the target date, blended with the historical rate by horizon.",
      component_ensemble: "Multi-model ensemble",
      component_ensemble_desc:
        "The mean of four vendor models (ECMWF, GraphCast, GFS, JMA). Useful as a smoothing baseline.",
      component_learned: "Learned model",
      component_learned_desc:
        "A small regression that learns how much weight to give each component based on past resolutions. This is the one Aratea actually bets with.",
      market_label: "Market (Kalshi mid)",
      market_desc:
        "What the Kalshi order book is implying right now. The yardstick Aratea must beat.",
      no_run: "No training run yet — the components will appear once the model has fit at least once.",
      role_champion: "champion",
      role_challenger: "challenger",
      role_baseline: "baseline",
      role_explainer:
        "Champion = the model whose probability is actually used to place the bet. Challengers run in parallel as shadow forecasts; one only becomes champion after beating the current one on a rolling window of resolved trades. This is why the “champion” probability shown in the public view can differ from the “learned model” probability here.",
      brier_chart_heading: "Track record so far",
      brier_intro: (
        <>
          The chart below shows the <strong>Brier score</strong> of two
          forecasters across every training pass. Brier scores accuracy:
          0 = perfect, 1 = always wrong, lower is better.
          <br />
          <span className="text-[#5fa8d3]">●</span> blue line = Aratea's learned
          model.{" "}
          <span className="text-[#e2b341]">●</span> yellow line = the Kalshi
          market mid on the exact same events. When blue stays under yellow,
          Aratea has signal the order book doesn't.
        </>
      ),
    },
    expert: {
      heading: "Expert view",
      intro:
        "Everything the manifest carries: named factors with their leave-one-out delta, paper-trade ledger, training runs and Brier trajectory. This is the meteorologist / actuary view — no rounding, no sugar-coating.",
    },
    n_eff_section: {
      title: "Hybrid effective sample (N_eff)",
      n_live: "N_live (real paper trades)",
      n_backtest_strict: "N_backtest_strict (replay, point-in-time)",
      n_backtest_naive_excluded: "NAIVE-excluded (informational)",
      decomposition: (
        nLive: number,
        alpha: number,
        nBacktest: number,
        nEff: number,
      ) =>
        `= ${nLive} + ${alpha} × ${nBacktest} = ${nEff.toFixed(1)}`,
      compact_hint: (nLive: number, alpha: number, nBacktest: number) =>
        `= ${nLive} live + ${alpha} × ${nBacktest} backtest. Secondary decisions only — the Phase 1 gate uses live only.`,
      phase_1_gate: (nLive: number, gate: number) =>
        `Phase 1 gate (strict, live only): N_live ≥ ${gate}. Currently ${nLive}/${gate}.`,
      phase_1_reached: "Phase 1 gate reached (live only) ✓",
      methodology_note:
        "N_eff drives secondary decisions only — feature-set selection, reliability plots, complementary promotion check. The Phase 1 go/no-go gate stays strictly on N_live; backtest volume never substitutes for live trades there.",
      convention_link: "Read CONVENTION §6.bis",
    },
    filters: {
      series_label: "Series",
      status_label: "Status",
      clear: "Clear",
      status_open: "open",
      status_resolved: "resolved",
    },
    counters: {
      features_tracked: "Features tracked",
      active: "Active",
      experimental: "Experimental",
      dropped: "Dropped",
      paper_bets: "Paper bets (open / resolved)",
      phase_1_hint: (n: number | string) => `Phase 1: ${n}`,
    },
    manifest_generated: (ts: string, v: number) =>
      `Manifest generated at ${ts} (schema v${v}).`,
    manifest_missing_title: "Predictor manifest not found",
    manifest_missing_body: (
      <>
        The build step that generates{" "}
        <code className="text-text">public/predictor_manifest.json</code> did
        not run. Run <code className="text-text">npm run manifest</code> (or a
        full <code className="text-text">npm run build</code>) and reload.
      </>
    ),
    sections: {
      live_title: "A. Live runs (Kalshi paper trades)",
      live_desc:
        "Each row is a real paper trade on Kalshi. The champion takes the position (real ledger row, real P&L); challengers and baselines run in shadow mode for Brier comparison. ★ marks the best Brier on a given run. The promotion rule (champion swap) needs a rolling-mean Brier dominance over N≥10 resolved trades — single-run wins are anecdotal.",
      factors_title: "B. Named factors",
      factors_desc:
        "Each row is a named hypothesis used by the learned predictor at training time. Brier Δ is the leave-one-out test delta from the most recent training run — sort by it to see what carried the model.",
      latest_title: "C. Latest training run",
      latest_desc: (
        <>
          Snapshot of the most recent sklearn fit of the learned predictor on
          historical resolutions. This is <em>not</em> a paper trade — it&apos;s
          a cross-validation pass to see whether the current feature set has
          edge over kalshi_mid on past Kalshi events.
        </>
      ),
      latest_empty: "No training runs yet.",
      history_title: "D. Training run history",
      history_desc: (
        <>
          Every sklearn training pass, most recent first.{" "}
          <em>This is not the paper-trade history</em> — see section A for that.
          A training run with Brier test below Brier kalshi_mid on the same rows
          means the model has signal beyond the market mid in cross-validation.
        </>
      ),
      brier_title: "E. Training Brier trajectory",
      brier_desc:
        "Learned model (test) vs kalshi_mid (same test rows) across all training runs. Dashed horizontal line is the most recent kalshi_mid Brier as all-time reference; vertical dashed markers flag a feature-set bump (v0 → v1 → v2 …).",
      backtest_title: "F. Backtest replays",
      backtest_desc:
        "Replayed records produced by backtest.py against settled Kalshi events. Only strict point-in-time records count toward N_backtest_strict; NAIVE-mode rows are flagged and excluded from the hybrid sample. Filters above narrow both this table and the live runs section.",
    },
  },

  status: {
    none: "Unknown",
    proposed: "Proposed",
    challenged: "Challenged",
    executed: "Executed",
    cancelled: "Cancelled",
  },

  components: {
    live_table: {
      empty: (
        <>
          No live paper trades captured yet. The first one will be the next run
          of <code className="text-text">daily_auto.py</code>.
        </>
      ),
      header_run: "Run",
      header_when: "When",
      header_event: "Event / Bin",
      header_side: "Side",
      header_champion: "Champion p",
      header_challenger: "Challenger p",
      header_baseline: "Baseline p",
      header_kalshi_mid: "kalshi_mid",
      header_outcome: "Outcome",
      header_pnl: "P&L paper",
      pending: "PENDING",
      win: (outcome: string) => `WIN (${outcome.toUpperCase()})`,
      loss: (outcome: string) => `LOSS (${outcome.toUpperCase()})`,
      footer:
        "★ = best Brier this run · B = Brier score per model · P&L = champion only (challengers and baselines are shadow; no real exposure).",
    },
    history_table: {
      empty: "No training runs yet.",
      header_when: "When (UTC)",
      header_feature_set: "Feature set",
      header_n_test: "n_test",
      header_brier_test: "Brier test",
      header_brier_kalshi_mid: "Brier kalshi_mid",
      header_gap: "Gap",
      header_verdict: "Verdict",
      header_notes: "Notes",
    },
    backtest_table: {
      empty:
        "No backtest replays in the manifest. The aggregate count may still be non-zero — per-record detail is omitted by the manifest builder when the ledger exceeds the inline budget.",
      header_run: "Run",
      header_when: "As-of → target",
      header_event: "Series / Bin",
      header_mode: "Mode",
      header_model: "Model p / Brier",
      header_outcome: "Outcome",
      pending: "PENDING",
      win: "WIN",
      loss: "LOSS",
      footer:
        "★ = best Brier on this replay · B = Brier score · NAIVE = excluded from N_backtest_strict.",
      load_more: "Load 25 more",
      showing: (visible: number, total: number) =>
        `Showing ${visible} of ${total}`,
      naive_label: "NAIVE",
      naive_tooltip: "Excluded from N_backtest_strict (CONVENTION §6.bis)",
    },
    feature_table: {
      header_name: "Name",
      header_hypothesis: "Hypothesis",
      header_source: "Source",
      header_added: "Added",
      header_delta: "Brier Δ",
      header_status: "Status",
      modal_feature: "Feature",
      modal_hypothesis: "Hypothesis",
      modal_status: "Status",
      modal_date_added: "Date added",
      modal_source: "Source",
      modal_current_delta: "Current Brier Δ",
      modal_history: "History",
      modal_history_empty: "Not yet measured in any training run.",
      modal_history_run: "Run",
      modal_history_feature_set: "Feature set",
      modal_close: "close",
      modal_close_aria: "Close",
    },
    // Server-only — built into a ReactNode by the page before passing to the
    // client component, because functions can't cross the RSC boundary.
    feature_table_footer: (carried: ReactNode, noise: ReactNode) => (
      <>
        Click a row for the full hypothesis, source link, and per-run history.
        Brier Δ is the leave-one-out test-Brier delta from the latest run —
        {carried} = feature carried signal,
        {noise} = net noise on this split.
      </>
    ),
    feature_table_footer_carried: " negative (↓) ",
    feature_table_footer_noise: " positive (↑) ",
    latest_card: {
      title: "Latest training run",
      feature_set: "feature set",
      notes: "notes",
    },
    verdict: {
      ensemble: "ENSEMBLE WINS",
      market: "MARKET WINS",
      tie: "TIE",
      tooltip: "Comparison of test-set Brier vs kalshi_mid on the same rows",
    },
    countdown: {
      expired: "window expired",
      remaining: "remaining",
    },
    brier_chart: {
      empty: (
        <>
          No training runs yet. The first{" "}
          <code className="text-text">train_learned.py</code> execution will
          populate this chart.
        </>
      ),
      axis_x: "run (UTC date)",
      axis_y: "Brier score (lower = better)",
      legend_learned: "learned (test)",
      legend_kalshi: "kalshi_mid (test)",
    },
  },

  locale_toggle: {
    en: "EN",
    fr: "FR",
    aria: "Switch language",
  },
};

// Dictionary type derived from the EN file (widened — no `as const` so that
// translations don't have to match the exact literal strings).
// The FR file must satisfy this shape.
export type Dictionary = typeof en;
