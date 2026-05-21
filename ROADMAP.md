# Roadmap

*Last updated: 2026-05-15*

The phased plan for Aratea. This file frames the journey; [`STATUS.md`](STATUS.md)
records where we actually are at this moment. Every claim here points
back to a source artifact in this repo.

## How phases map

The protocol-level phasing in [`docs/architecture.md`](docs/architecture.md) — POC, DAO,
parametric mutual, DePIN — is the *outer* timeline. Inside the current
POC slice, two engineering tracks run in parallel:

- **Predictor track** — proves the predictive edge that motivates
  everything downstream. Source of truth: [`predictor/`](predictor/).
- **Contracts settlement track** — ships the on-chain ratification and
  mint mechanism for the labor-value rounds that already run
  off-chain. Source of truth: [`contracts/`](contracts/).

Both tracks must complete before Phase 2 (DAO) can start.

```
Phase 1 (current) ─── Phase 2 ──────── Phase 3 ──────────── Phase 4
─────────────────                     ──────────────────
predictor + contracts                 parametric mutual    DePIN data
settlement layer                      (risk pool, pricing  layer
   │                                   on-chain, oracle    (weather
   ├── predictor: Kalshi POC          settlement)          stations)
   └── contracts: AugPocToken +
       RoundRegistry
       (no on-chain emission cap)
```

---

## Predictor track — Phase 1

**Outcome the track delivers**: a written go / no-go on whether the
meta-ensemble carries an edge worth deploying real capital against.

### Done

Module-level checkpoints, observable in the repo:

- **Kalshi public client** — pagination, retries with backoff, dual
  cents/dollars format handling. See [`predictor/src/kalshi/`](predictor/src/kalshi/).
- **Open-Meteo integration** — 11 mapped cities (NWS-aligned timezone),
  five vendor forecast endpoints (`ecmwf_ifs025`, `ecmwf_aifs025_single`,
  `gfs_graphcast025`, `gfs_global`, `jma_gsm`), ERA5 historical, disk
  cache with `_has_usable_series()` guard against silent empties.
  See [`predictor/src/weather/open_meteo.py`](predictor/src/weather/open_meteo.py).
- **Base predictors** — `climatology` (15-year same-DOY window, Laplace
  smoothing), `forecast_blend` (Open-Meteo `mu` + climatology `sigma`,
  horizon-decayed blend). See [`predictor/src/predictors/`](predictor/src/predictors/).
- **Meta-ensemble predictor (A.1)** — uniform mean of four vendor
  forecasts, quadrature combination of inter-model sigma and climatology
  residual sigma, rounded NWS half-up on bin edges. See
  [`predictor/src/predictors/ensemble.py`](predictor/src/predictors/ensemble.py).
- **Paper simulator + ledger** — Kelly fractional sizing (25 % default,
  5 % bankroll cap), append-only CSV ledger. See [`predictor/src/simulation/`](predictor/src/simulation/).
- **NWS resolution catalog (B-1)** — 18 stations, 40 prefix → station
  mappings, round-half-up arithmetic, Trace = YES convention with
  threshold guard, 9 asserting tests. See [`predictor/src/kalshi/resolution.py`](predictor/src/kalshi/resolution.py).
- **Microstructure audit (B-2)** — bin-distribution extractor, implied
  mean/std, vig-residual + spread-skew + tail-mass metrics, 6 asserting
  tests. Empirical finding: on the 32-event audit, *tail underpricing
  was not present* — 29 / 32 events had tighter extremes than centres.
  See [`predictor/src/microstructure/`](predictor/src/microstructure/).
- **Forward-test pipeline** — `fetch_markets.py` → `forward_predict.py`
  → `score_forward.py`, the only honest backtest path (no time-of-day
  leakage, dedup on first quote). See [`predictor/scripts/`](predictor/scripts/).
- **Learned predictor framework (A.3)** — `sklearn.LogisticRegression`
  over a feature registry, leave-one-out Brier delta per feature, named
  hypotheses with status (`experimental` / `active` / `dropped` /
  `retired`). See [`predictor/src/learning/`](predictor/src/learning/) + [`predictor/src/learning/FEATURES.md`](predictor/src/learning/FEATURES.md).
- **Champion / Challenger / Baseline registry** — formal promotion rule
  (run promotable + rolling Brier + sign test). See [`predictor/runs_learning/CHAMPION.json`](predictor/runs_learning/CHAMPION.json).
- **Chronological-split methodology fix** — group-aware split on
  `target_date`, schema v3, `promotable: false` gate at
  `n_distinct_test_split_values < 3`, two non-blocking warnings, full
  diagnosis report. See [`predictor/docs/rapport-split-temporel-2026-05-14.md`](predictor/docs/rapport-split-temporel-2026-05-14.md).
- **Daily autonomous routine** — finalize settled runs, capture
  qualifying J+1 events, rebuild dashboard manifest, commit + push.
  Runs in CI at 18:00 UTC. See [`.github/workflows/daily-trading.yml`](.github/workflows/daily-trading.yml) +
  [`predictor/scripts/daily_auto.py`](predictor/scripts/daily_auto.py).

### In flight

- **Grow the resolved-events dataset N.** Current state: 2 resolved
  paper runs (002, 003), 2 in flight (004, 005). The Phase 1 criterion
  is N > 50. Bottleneck is calendar time × Kalshi event density.
- **Lift the `promotable: false` ceiling.** Test set currently spans a
  single `target_date`; the gate needs ≥ 3 distinct days. This will
  resolve on its own once the daily auto-capture has accumulated more
  closed days.
- **Decide what to do with the six geographic features.** Each was
  introduced with a written hypothesis — urban heat island, water
  thermal inertia, canopy effects, altitude amplification, maritime
  damping, latitude-driven insolation. On the latest run, all six have
  `|coef| < 0.04` and Brier deltas in the `1e-5` band. Three options on
  the table:
  1. *Drop* them and ship a leaner v3 feature set (Occam-first).
  2. *Transform* them into interactions
     (`forecast_spread × latitude`, `elevation × days_ahead`, …) so a
     linear learner can capture non-additive structure.
  3. *Keep them* but only as candidates for a non-linear successor
     model (gradient-boosted trees), once we have enough samples to
     justify the parameter budget.
  Decision blocked on having a non-degenerate test set.
- **Multicollinearity audit on the forecast-probability features.** The
  current L2 coefficients show `p_ensemble ≈ +1.07`,
  `p_forecast_blend ≈ -0.87`, `p_climatology ≈ -0.40` — the classic
  compensation pattern. Candidate replacement: collapse the three into
  `p_consensus` (mean or median) + the existing `forecast_spread`. To be
  retested under the fixed split once N grows.
- **Land `p_nws_ndfd` once forward captures accumulate.** The NWS NDFD
  forecast — issued by the agency that *resolves* Kalshi weather
  markets — has no historical archive, so it earns its place only via
  forward-only validation. Wired as `experimental` in the registry.

### Pending

- **Reach N > 50 resolved runs.**
- **Evaluate the Phase 1 go / no-go criterion in writing.** Two
  conditions on the same N: meta-ensemble Brier < best-single-model
  Brier *and* meta-ensemble Brier < climatology Brier. Both must hold.
- **If the criterion holds**: transition plan to small real-money
  positions, sized via Kelly fractional 25 %, capped at 5 % bankroll
  per bet. Custody and structure decisions become live.
- **If the criterion fails**: pivot or wind down the predictor track
  honestly. The criterion is written before the result and cannot move
  afterwards — see [`predictor/runs/CONVENTION.md`](predictor/runs/CONVENTION.md) §6.

---

## Contracts settlement track — Phase 1

**Outcome the track delivers**: an on-chain mint of `AUG-POC` against a
ratified monthly round, fully reproducible end-to-end on Arbitrum
Sepolia.

Roadmap mirrored from [`contracts/README.md`](contracts/README.md):

| Milestone | Scope | Status |
|---|---|---|
| **M0** | Foundry scaffold, CI, threat model, bilingual docs | ✅ done |
| **M1** | `AugPocToken` (ERC-20 + Permit + AccessControl + Pausable + 4 roles) | ✅ done |
| **M2** | ~~`MonthlyMintCap` library~~ — removed 2026-05-17 (no on-chain emission cap; quality gated off-chain — white paper §7.7) | — |
| **M3** | `RoundRegistry` (propose / challenge / execute / cancel) | ✅ done |
| **M4** | Deployment scripts on Arbitrum Sepolia + Safe calldata helpers | ✅ done |
| **M5** | Read-only dashboard (Next.js + viem) | 🟡 in progress |

After M5, the on-track-but-out-of-Phase-1 work:

- **First Arbitrum Sepolia deployment.** Genesis-round execution is the
  acceptance test — see [`rounds/archives/2026-05-genesis/`](rounds/archives/2026-05-genesis/) for the pinned
  valuation report this first round will commit.
- **Community audit.** Mainnet is blocked until ≥ 1 audit completes
  (Code4rena Arena-X, Sherlock Watson, or documented peer review). See
  [`contracts/README.md`](contracts/README.md) §Target chain.

---

## Phase 2 — DAO Aratea

Triggered once the Phase 1 predictor go-criterion is met and the
contracts settlement layer is audited. Scope from
[`docs/architecture.md`](docs/architecture.md):

- Deploy the on-chain governance token (the future `ARA`) and convert
  `AUG-POC` holders via the `BURNER_ROLE` slot reserved on
  `AugPocToken`. Conversion ratio set by ≥ 67 % token vote at launch.
- Activate the mint module on Arbitrum mainnet, having already run on
  Sepolia.
- Set up the panel-of-Top-X governance for challenge-window decisions.

### Open decisions

Recorded in [`docs/architecture.md`](docs/architecture.md) §"Décisions ouvertes":

- **Deployment chain.** Arbitrum is the current target; Base and
  Optimism remain alternatives. Criteria: gas economics, DeFi /
  risk-pool ecosystem, custody options.
- **Bankroll stablecoin.** USDC, EURC, or multi-stable. Impact: Kalshi
  is USD-only, so conversion friction matters.
- **Kalshi custody for the POC.** Personal account, US LLC, or
  foundation. Determines the upstream legal structure.
- **Smart-contract toolchain.** Foundry retained for Phase 1; Hardhat
  parity not maintained.
- **Wallet registry.** Signed file [`rounds/WALLETS.md`](rounds/WALLETS.md) in Phase 1; an
  on-chain registry starts in Phase 2.

---

## Phase 3 — Parametric mutual

Triggered once the DAO is operational and the predictor has demonstrated
the edge in live conditions. Scope:

- **Mutualization pool.** Members deposit USDC / BTC, accrue value
  through NAV appreciation as the pool collects premiums on issued
  contracts.
- **Pricing engine.** The off-chain predictor signs contract prices and
  posts them on-chain.
- **Resolution.** Chainlink Custom feed over NOAA / NWS observations,
  plus proprietary DePIN stations when Phase 4 lands.
- **Initial contract categories.** Extreme-temperature, accumulated
  precipitation, wind events.

Reminder of the legal frame: Aratea is not insurance under the French
*Code des assurances* or Solvency II. It is a **decentralized
discretionary mutual**: pooled capital, parametric execution, oracle-
driven indemnification, token-holder governance. See the white paper §4.

---

## Phase 4 — DePIN data layer

Long-horizon. Physical weather stations rewarded in `ARA` based on
uptime, data quality (neighbour-coherence checks, model validation,
outlier filtering), and geographic density (bonus for under-covered
areas). Open question: WeatherXM partnership vs. proprietary network.

The labor-value mint mechanism handles this naturally — a station
operator's contribution is valued in BTC-equivalent like any other Git-
observable artifact (signed uptime digest committed to the repo).

---

## Decision log

Time-stamped record of decisions that shaped the current trajectory.
Each one points to its source artifact when possible.

| Date | Decision | Source |
|---|---|---|
| 2026-05-08 | Project architecture v0.1 ratified — four-pillar vision (predictor / DAO / mutual / DePIN) | [`docs/architecture.md`](docs/architecture.md) |
| 2026-05-08 | Token model v0.3 — unified labor-value mint, no pre-allocation, refusability symmetry, 1 sat = 1 token initial NAV | [`docs/token_model.md`](docs/token_model.md) |
| 2026-05-09 | `AUG-POC` token target: ERC-20 on Arbitrum Sepolia (testnet), 18 decimals, BTC-denominated NAV | [`contracts/README.md`](contracts/README.md) |
| 2026-05-09 | Monorepo open-sourced under Apache 2.0 | [`LICENSE`](LICENSE) |
| 2026-05-10 | First champion: `vendor_ensemble`. Run 002 NYC LOWT B50.5 paper +$56.16 | [`predictor/runs_learning/CHAMPION.json`](predictor/runs_learning/CHAMPION.json), [`predictor/runs/002/`](predictor/runs/002/) |
| 2026-05-11 | Renamed Augure → Aratea after diligence flagged conflict with the Augur Ethereum protocol. Token symbol `AUG-POC` preserved through Phase 1, `ARA` reserved for Phase 2 conversion via `BURNER_ROLE` | [`docs/architecture.md`](docs/architecture.md), [`contracts/README.md`](contracts/README.md) |
| 2026-05-11 | Security audit closure: PR #18 merged, email scrub + history rewrite over 102 commits, push protection enabled | [`docs/SECURITY-audit-2026-05-11-handoff.md`](docs/SECURITY-audit-2026-05-11-handoff.md) |
| 2026-05-11 | Branch protection on `main`, solo development goes through a PR flow with self-approval | repo settings |
| 2026-05-12 | Secret rotation routine completed — Pinata + four Discord webhooks + Etherscan. Next routine: 2026-08-12 | [`docs/SECURITY-rotation-log.md`](docs/SECURITY-rotation-log.md) |
| 2026-05-12 | First `learned_v2` training, formal Champion / Challenger / Baseline registry | [`predictor/runs_learning/CHAMPION.json`](predictor/runs_learning/CHAMPION.json) |
| 2026-05-13 | Run 003 — first multi-model live capture. Champion best Brier on the single point (0.0196 vs 0.0326 challenger vs 0.1190 baseline) | [`predictor/runs/003/`](predictor/runs/003/) |
| 2026-05-14 | Polymarket dropped from Phase 1 venues: no recurring daily weather markets, structural pricing bias, UMA-settlement friction with no methodological gain | [`predictor/runs/CONVENTION.md`](predictor/runs/CONVENTION.md) §2 |
| 2026-05-14 | Chronological-split fix — `train_learned.py` is now group-aware on `target_date`, schema v3, `promotable` gate at `n_distinct_test_split_values ≥ 3` | [`predictor/docs/rapport-split-temporel-2026-05-14.md`](predictor/docs/rapport-split-temporel-2026-05-14.md) |
| 2026-05-14 | Dependabot major-version PRs (#35, #36, #38 — `next`, `typescript`, `@types/node`) closed. Majors are handled as dedicated migration sessions, not weekly batches | repo PR history |

---

## Sequencing summary

```
Predictor track ─┐
                 ├─► Phase 1 go/no-go ─► Phase 2 (DAO) ─► Phase 3 (mutual) ─► Phase 4 (DePIN)
Contracts track ─┘
                  audit gate
```

Phase 2 cannot start while either of the two Phase 1 tracks is open.
Phase 3 needs the DAO live and the predictor proven in real-money
conditions. Phase 4 needs the DAO live to mint operator rewards — but
its discovery work (partnership scoping, station prototyping) can run in
parallel.
