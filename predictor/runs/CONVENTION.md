# predictor/runs/ — convention

Phase 1 of Aratea (the Kalshi POC) is about **measuring a predictive
edge** on weather prediction markets before any decentralized
parametric mutual is built. Every paper or live position taken under
that POC must leave a public, verifiable trace. This directory is the
canonical record.

## 1. Naming

```
predictor/runs/NNN/
```

Where `NNN` is a zero-padded integer starting at `001`. Runs are
numbered in the order they are executed, regardless of calendar gap.

A run = a single model prediction, which can target **one or several
markets across one or several venues**. The schema keeps `markets[]`
plural for forward compatibility, but Phase 1 has converged to a
single venue (Kalshi).

## 2. Supported platforms

| Platform | Status | Resolution source |
|---|---|---|
| `kalshi` | **Phase 1 primary and only venue.** Daily weather bin markets, real liquidity, NWS-resolved | NWS official station observations |
| `polymarket` | **Dropped on 2026-05-14.** See note below. | (would have been UMA on-chain oracle) |

**Why Polymarket was dropped for Phase 1:**

1. **No recurring daily weather markets.** Polymarket has only ad-hoc
   events (hurricane landfall, seasonal snow accumulation) — no
   per-city per-day bin structure equivalent to Kalshi LOWT/HIGHT.
   Each Polymarket trade would be on a different event class,
   preventing the accumulation of a statistically comparable N for
   the meta-ensemble validation.
2. **Structural pricing biases.** Polymarket's investor base is
   crypto-native and US-geofenced. Implied probabilities reflect that
   subset's beliefs and risk appetite, not a market-truth proxy on
   weather. Using Polymarket-mid as a benchmark would muddy the
   "beat the market on its own ground" criterion.
3. **Settlement friction without methodological gain.** UMA Oracle
   resolves 2–7 days after the event, with a dispute window. Kalshi
   auto-settles on NWS publication. The added operational overhead
   buys nothing for the Phase 1 statistical goal.

The schema below still tolerates `"polymarket"` in `markets[].platform`
to avoid retroactively breaking historical runs that referenced it.
New runs target Kalshi only.

## 3. Required content per run

Each `runs/NNN/` directory MUST contain:

| File | Purpose |
|---|---|
| `report.json` | Machine-readable record. Schema below. |
| `PRE_RUN.md`  | Discord template for the run-open message (FR). |
| `POST_RUN.md` | Discord template for the resolution message (FR). |
| `X_THREAD_EN.md` | X / Twitter thread template (EN). |
| `X_THREAD_FR.md` | X / Twitter thread template (FR). |

A `REPORT.md` builder-log narrative may be added retrospectively when
useful (e.g. for the Run 001 backfill).

By the time the resolution is in, each run MUST have logged:

- **Event** — short description, expected resolution time UTC.
- **Model output** — meta-ensemble probability `p_yes`, confidence,
  feature-set hash for reproducibility.
- **Markets** — for each venue: ticker / market id, URL, resolution
  source, pre-trade snapshot (mid/bid/ask/ts), edge bps vs market and
  vs climatology, position (side, size, paper flag), resolution
  (outcome, ts, P&L).
- **Scoring** — Brier score for the model, Brier for climatology, and
  Brier for the best single model. Computed at the run level (one
  prediction → one Brier triplet), not per market.

Every value comes from a script output, an exchange API, an oracle, or
a NWS/NOAA bulletin. If a value isn't sourceable, it stays `null` in
`report.json` and is flagged as such in the markdown.

## 4. Workflow

```
1. Pre-run        — fill PRE_RUN.md with the post copy + report.json
                    pre-fields (event, model, markets[*].snapshot_pre,
                    edge_bps, position). Commit.
2. Tag            — git tag run-NNN (annotated, with the maintainer's
                    framing as the tag message). Push → the
                    announce-release CI auto-fires and posts to
                    Discord + X.
3. Manual posts   — optionally use predictor/scripts/post_to_discord.py
                    to push the PRE_RUN.md / POST_RUN.md content to a
                    specific channel via webhook (when the auto-announce
                    voice or timing isn't right).
4. Resolution     — once the markets settle, fill the resolution fields
                    in report.json (per market) and the run-level
                    scoring fields (Brier triplet). Update POST_RUN.md
                    and X_THREAD_*.md from the resolved values.
5. Commit         — chore(runs/NNN): resolved — outcome <Y/N>, P&L $<X>
```

## 5. `report.json` schema

The same JSON shape applies to every run. Unknown fields stay `null`
until they are observed.

```json
{
  "run_id": "002",
  "ts_utc": null,
  "model": {
    "ensemble": ["ECMWF", "GraphCast", "GFS", "JMA"],
    "p_yes": null,
    "confidence": null,
    "feature_set_hash": null
  },
  "event": {
    "description": "<TBD>",
    "resolution_time_utc": null
  },
  "markets": [
    {
      "platform": "kalshi",
      "ticker": "<TBD>",
      "url": null,
      "resolution_source": "NWS",
      "snapshot_pre": {
        "mid": null, "bid": null, "ask": null, "ts_utc": null
      },
      "edge_bps": {
        "vs_market": null, "vs_climatology": null
      },
      "position": {
        "side": null, "size_usd": null, "paper": true
      },
      "resolution": {
        "outcome": null, "ts_utc": null, "pnl_usd": null
      }
    }
  ],
  "scoring": {
    "brier_model": null,
    "brier_climatology": null,
    "brier_best_single_model": null
  },
  "notes": ""
}
```

Notes on field types:

- `model.p_yes`, `model.confidence` ∈ `[0, 1]`.
- `model.feature_set_hash` is a stable hash of the input features the
  ensemble saw, so a future replay can verify the prediction was not
  retroactively edited.
- `markets[].platform` ∈ `"kalshi" | "polymarket"`.
- `markets[].edge_bps.*` is in basis points (1 bp = 0.0001 = 0.01 %).
  `vs_market` = `(p_yes_model − p_yes_market_implied) × 10_000`.
  `vs_climatology` = `(p_yes_model − p_yes_climatology) × 10_000`.
- `markets[].position.side` ∈ `"yes" | "no" | null`.
- `markets[].position.paper` is `true` until live trading is
  explicitly enabled.
- `markets[].resolution.outcome` ∈ `"yes" | "no" | null`. The same
  outcome value should appear in every market entry of the same run
  (same event → same truth), but the `pnl_usd` differs per venue.
- `scoring.*` is run-level. Brier scores compare the meta-ensemble's
  `p_yes` to the realised outcome (0 or 1), against the same outcome
  for climatology and for the best individual model.
- All timestamps are ISO 8601 with `Z` suffix (UTC).

## 6. Phase 1 go / no-go criterion

Phase 1 is considered validated **if and only if**, on a sample of
**N > 50 resolved runs**:

1. The meta-ensemble's mean Brier score is strictly lower than the
   best individual model's Brier score on the same N events.
2. The meta-ensemble's mean Brier score is strictly lower than
   climatology's Brier score on the same N events.

Both conditions must hold. Failing either, Phase 1 is declared a
no-go and the project pivots or stops, per the white paper.

The criterion is honest by construction: it is written before the
results, and it cannot be moved after the fact. The data needed to
evaluate it is fully encoded in the union of `report.json` files
under this directory — specifically in each run's `scoring` block.

## 7. Where to look first

- `runs/001/` — backfill of the first executed run (pipeline
  dry-run, no position).
- `runs/002/` — the first run executed under this logging
  convention.
- `predictor/scripts/post_to_discord.py` — manual webhook poster
  for out-of-band updates.
- `.github/workflows/announce-release.yml` — auto-announce on
  `run-*` tags.
