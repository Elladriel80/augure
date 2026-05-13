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
