# Status

*Last updated: 2026-05-15*

Snapshot of where Aratea actually stands across its three live tracks
(predictor, contracts, dashboard) and the infrastructure around them.
Every numeric claim below has a source file in this repo — paths are
quoted inline so anything can be verified without trusting this page.

For the phased plan that frames these tracks, see [`ROADMAP.md`](ROADMAP.md).

---

## Predictor — Phase 1 Kalshi POC

Mode: **paper trading only**. No real-money position has been opened.
The Phase 1 go / no-go criterion is recorded in
[`predictor/runs/CONVENTION.md`](predictor/runs/CONVENTION.md) §6:
on N > 50 resolved runs, the meta-ensemble must beat both the best
individual model and climatology on Brier score.

### Live model lineup

Registry: [`predictor/runs_learning/CHAMPION.json`](predictor/runs_learning/CHAMPION.json).

| Role | Model | Active since | Method |
|---|---|---|---|
| Champion | `vendor_ensemble` | 2026-05-10 | Mean of four vendor probabilities (ECMWF + GraphCast + GFS + JMA), blended with climatology by horizon. No training. |
| Challenger | `learned_v2` | 2026-05-12 | `sklearn.LogisticRegression(L2, C=1.0)` over 11 features (5 forecast-derived + 6 static geographic). |
| Baseline | `kalshi_mid_baseline` | 2026-05-13 | The Kalshi market mid-price as the prediction — the floor a model must beat to claim any edge. |

Promotion of a challenger requires three independent conditions
(encoded in `CHAMPION.json`): its source training run must have
`promotable: true` (`n_distinct_test_split_values >= 3`), its rolling-mean
Brier over the last N ≥ 10 resolved trades must be strictly lower than
the champion's, and a 1-sided binomial sign test on per-trade Brier wins
must yield p < 0.10.

### Resolved paper runs

| Run | Event | Outcome | Champion Brier | Champion paper P&L |
|---|---|---|---|---|
| [`002`](predictor/runs/002/) | NYC LOWT 2026-05-11, bin 50–51°F | NO | 0.0213 | +$56.16 |
| [`003`](predictor/runs/003/) | NYC LOWT 2026-05-13, bin 51–52°F | NO | 0.0196 | +$52.44 |

Run 003 was the first multi-model capture (champion + challenger + baseline
all evaluated on the same event); the champion finished best on Brier.
A single resolved point is directional only — not statistically
significant. See [`predictor/runs/003/report.json`](predictor/runs/003/report.json) §scoring.

Total resolved: **2 / 50** required for the Phase 1 go / no-go.

### Open paper runs

| Run | Event | Captured | Resolution expected |
|---|---|---|---|
| [`004`](predictor/runs/004/) | NYC LOWT 2026-05-14, bin 52–53°F | 2026-05-13 14:29 UTC | NWS daily climate report (~J+1) |
| [`005`](predictor/runs/005/) | NYC LOWT 2026-05-15, bin 49–50°F | 2026-05-14 19:45 UTC | NWS daily climate report (~J+1) |

Both opened automatically by the CI workflow (see *CI* below). Each run
records a champion position with a real `paper_bets.csv` ledger row plus
two shadow positions for the challenger and the baseline (same side, same
size, theoretical P&L only) so Brier scores remain directly comparable.

### Latest training run (decision-gate)

[`predictor/runs_learning/20260514T191934Z/run.json`](predictor/runs_learning/20260514T191934Z/run.json) — feature set v2,
chronological split on `target_date`.

| Metric | learned_v2 (test) | kalshi_mid (test) |
|---|---|---|
| Brier | 0.1323 | **0.1305** |
| Log loss | 0.4222 | **0.4071** |

`kalshi_mid` leads by 0.0018 Brier. The run is marked `promotable: false`
because the test set spans **a single distinct `target_date`**
(2026-05-13). Gate requires ≥ 3 distinct values, so this verdict is not
yet a generalization claim — it describes one point in time. The next
batch of resolved events is the bottleneck.

### Feature signal

Registry: [`predictor/src/learning/FEATURES.md`](predictor/src/learning/FEATURES.md). The latest run's
leave-one-out Brier deltas surface two clean facts:

- The forecast-derived features carry the signal:
  `p_ensemble` coefficient ≈ +1.07, `p_forecast_blend` ≈ -0.87,
  `p_climatology` ≈ -0.40, `forecast_spread` ≈ -0.13. The signs on the
  three probability features are a classic L2 compensation pattern under
  multicollinearity — flagged for a possible feature set v3 that
  collapses them into `p_consensus + forecast_spread`.
- The six static geographic features (`urban_density_5km`,
  `water_pct_10km`, `forest_pct_5km`, `elevation_m`,
  `distance_to_coast_km`, `latitude`) are **noise as additive features**
  in this configuration: `|coef| < 0.04` for all six and Brier deltas in
  the `1e-5` band. They do not earn their place in a linear model —
  either drop them or test them as interactions.

### Methodology gate (2026-05-14 fix)

A prior training run ([`predictor/runs_learning/_invalidated/20260514T141925Z/`](predictor/runs_learning/_invalidated/20260514T141925Z/)) was
explicitly invalidated because its test set collapsed to a single
`capture_at` value, inflating the `kalshi_mid` baseline to an artificial
0.0752 (vs. the historical ~0.12–0.14 band). The correctif rewrote
`chronological_split` to be group-aware on `target_date`, bumped
`run.json` to schema v3, surfaced `split_key` / `n_distinct_test_split_values`
in the dashboard manifest, and added a hard gate: any run with
`n_distinct_test_split_values < 3` is marked `promotable: false`.

Full report: [`predictor/docs/rapport-split-temporel-2026-05-14.md`](predictor/docs/rapport-split-temporel-2026-05-14.md) (French).

---

## Contracts — Phase 1 settlement layer

The on-chain ratification and execution layer for the labor-value mint
mechanism described in [`docs/token_model.md`](docs/token_model.md).
Detail and threat model in [`contracts/README.md`](contracts/README.md) and
[`contracts/docs/SECURITY.md`](contracts/docs/SECURITY.md).

### Milestones

| Milestone | Scope | Status |
|---|---|---|
| **M0** | Foundry scaffold, CI, threat model, bilingual docs | ✅ done |
| **M1** | `AugPocToken` — ERC-20 + Permit + AccessControl + Pausable + 4 roles | ✅ done |
| **M2** | ~~`MonthlyMintCap` library~~ — removed 2026-05-17 (no on-chain emission cap; quality gated off-chain — see `contracts/docs/ROUND-LIFECYCLE.md` §5 and white paper §7.7) | — |
| **M3** | `RoundRegistry` — propose / challenge / execute / cancel lifecycle | ✅ done |
| **M4** | Deployment scripts on Arbitrum Sepolia + Safe calldata helpers | ✅ done |
| **M5** | Read-only dashboard (Next.js + viem) | 🟡 in progress |

### Test coverage discipline

Unit tests target ≥ 95 % line coverage on business logic, fuzz tests run
10 000 iterations by default, and invariant tests cover the two
properties that must never break: no mint before the challenge window
expires, and `MINTER_ROLE` held only by the `RoundRegistry` (granted to
the Safe multisig at the admin level). No on-chain emission cap is
enforced — quality is guaranteed off-chain (white paper §7.7). Toolchain: Foundry, Solidity 0.8.24, OpenZeppelin v5.1.0,
`forge-std` v1.9.4, Slither 0.10.4 (CI fails on `medium`).

### Deployment state

- **Target chain:** Arbitrum Sepolia (testnet).
- **Live testnet deploy:** not yet executed (M4 ships the scripts;
  the genesis-round execution is the M5 acceptance test).
- **Mainnet:** blocked until at least one community audit
  (Code4rena Arena-X, Sherlock Watson, or documented peer review).

---

## Dashboard

Live: **[aratea-app.vercel.app](https://aratea-app.vercel.app/)**.
Source: [`dashboard/`](dashboard/).

Read-only by design — the dashboard never asks for a signature, never
broadcasts a transaction, never holds a key. Operations on the contracts
(`proposeRound`, `executeRound`, `cancelRound`) go through Foundry
scripts in [`contracts/script/`](contracts/script/), not this UI.

### Surfaces

| Page | What it shows |
|---|---|
| `/` (Token) | Name, symbol, decimals, total supply, pause state, emission-policy note (no on-chain cap — quality gated off-chain per white paper §7.7), Arbiscan links. |
| `/rounds` | Every round committed to the registry, ordered by proposal date. Status pill + challenge-window end + total amount + beneficiary count. |
| `/round/[hash]` | Full per-round metadata, live countdown to challenge-window end, IPFS link to the pinned `valuation_report.md`, per-beneficiary allocation breakdown. |
| `/predictor` | Latest training run summary card with Brier vs `kalshi_mid`, feature registry with per-run Brier deltas, run history table, Brier trajectory chart. |

### Stack

Next.js 15 (App Router) + React 19, TypeScript strict, viem 2.x for chain
reads, Tailwind for styling. No wagmi, no UI kit, no backend, no database,
no analytics. Every page server-renders against a public RPC; the
predictor page reads a static manifest (`public/predictor_manifest.json`)
regenerated at every build via `npm run manifest` →
`predictor/scripts/build_dashboard_manifest.py`.

---

## CI

Workflows live in [`.github/workflows/`](.github/workflows/).

| Workflow | Trigger | Purpose |
|---|---|---|
| `daily-trading.yml` | cron `0 18 * * *` UTC + manual dispatch | Run `daily_auto.py`: auto-finalize settled runs, auto-capture J+1 if `|edge| ≥ 0.10` and `spread ≤ 0.05`, rebuild manifest, commit + push so Vercel redeploys. |
| `contracts-ci.yml` | push / PR on `contracts/**` | Forge build + test + coverage + Slither. |
| `dashboard-ci.yml` | push / PR on `dashboard/**` | Typecheck + Next.js build + manifest shim test. |
| `announce-release.yml` | `run-*` annotated tags | Auto-announce paper-run open / close to Discord. |
| `weekly-recap.yml` | weekly cron | Generates a weekly summary. |
| `codeql.yml` | push / PR + schedule | GitHub-hosted security scanning. |
| `stale.yml` | scheduled | Auto-management of inactive issues. |

The daily-trading job uses a fine-grained PAT (`BOT_PAT` secret) so the
final push respects the main-branch ruleset. Fork PRs cannot trigger
that workflow (schedule + workflow_dispatch only).

---

## Recent infrastructure

- **2026-05-11** — Rename Augure → Aratea after diligence flagged a
  conflict with Augur (Ethereum prediction-markets protocol). White
  papers (FR + EN) updated on Notion; root `README.md` / `CONTRIBUTING.md`
  / module READMEs migrated. Token symbol `AUG-POC` and the contract name
  `AugPocToken` are preserved through Phase 1 — the convert step to
  `ARA` happens at Phase 2 DAO launch via the `BURNER_ROLE` reserved for
  a future `AraConverter`.
- **2026-05-11** — Security audit pass: PR #18 merged, email scrub +
  history rewrite over 102 commits, push protection rules enabled.
- **2026-05-11** — Branch protection enabled on `main`. Solo development
  now goes through a PR flow with self-approval, even single-author.
- **2026-05-12** — Secret rotations: Pinata + four Discord webhooks +
  Etherscan API key. Paper trail in [`docs/SECURITY-rotation-log.md`](docs/SECURITY-rotation-log.md).
  Next routine rotation: 2026-08-12.
- **2026-05-14** — Polymarket dropped as a Phase 1 secondary venue.
  Rationale recorded in [`predictor/runs/CONVENTION.md`](predictor/runs/CONVENTION.md) §2.
- **2026-05-14** — Chronological-split methodology fix (see *Methodology
  gate* above).
- **2026-05-14** — Dependabot major-version PRs (#35, #36, #38) closed
  for `next`, `typescript`, `@types/node`. Major bumps are handled as
  dedicated migration sessions, not in the weekly dependency batch.

---

## Where to read next

- **Vision & phasing**: [`docs/architecture.md`](docs/architecture.md), [`ROADMAP.md`](ROADMAP.md).
- **Token economic model**: [`docs/token_model.md`](docs/token_model.md), [`docs/value_engine.md`](docs/value_engine.md).
- **Contracts threat model**: [`contracts/docs/SECURITY.md`](contracts/docs/SECURITY.md), [`contracts/docs/ARCHITECTURE.md`](contracts/docs/ARCHITECTURE.md).
- **Run convention** (paper-trade logging schema): [`predictor/runs/CONVENTION.md`](predictor/runs/CONVENTION.md).
- **Genesis round decomposition**: [`rounds/archives/2026-05-genesis/phases.md`](rounds/archives/2026-05-genesis/phases.md).
