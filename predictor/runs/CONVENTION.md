# predictor/runs/ — convention

Phase 1 of Augure (the Kalshi POC) is about **measuring a predictive
edge** on weather prediction markets before any decentralized
parametric mutual is built. Every paper-trade or live position taken
under that POC must leave a public, verifiable trace. This directory
is the canonical record.

## 1. Naming

```
predictor/runs/NNN/
```

Where `NNN` is a zero-padded integer starting at `001`. Runs are
numbered in the order they are executed, regardless of calendar gap.

A single run = a single market position from open to resolution. If
several markets are entered together, group them under the same `NNN`
and use an array in `report.json` rather than splitting the folder.

## 2. Required content per run

Each `runs/NNN/` directory MUST contain:

| File | Purpose |
|---|---|
| `report.json` | Machine-readable record. Schema below. |
| `REPORT.md` | Builder-log narrative. What we predicted, why, what happened. |

Each run MUST capture, by the time the resolution is in:

- **Market** — platform, ticker, exact question, resolution source, resolution time UTC.
- **Model output** — the meta-ensemble probability `p_yes`, the per-model votes if relevant, the confidence band.
- **Position** — side (`yes` / `no`), notional in USD, paper or live.
- **Resolution** — outcome (`yes` / `no`), Brier score of the model prediction, Brier score of the climatology baseline, P&L in USD.
- **Edge measurement** — `edge_bps.vs_market` at entry, `edge_bps.vs_climatology` at entry. These two are the heart of Phase 1.

No self-declared numbers. Every value comes from a script output, an
exchange API, an oracle, or a NWS/NOAA bulletin. If a value isn't
sourceable, it stays `null` in `report.json` and is flagged as such in
`REPORT.md`.

## 3. Workflow

```
1. Pre-run        — open a markdown draft in runs/NNN/REPORT.md.
                    Fill market + model output + position. Commit.
2. Tag            — git tag run-NNN (annotated, with the maintainer's
                    framing of the run as the tag message).
                    Push → the announce-release CI auto-fires and
                    posts to Discord + X.
3. Manual posts   — optionally use predictor/scripts/post_to_discord.py
                    to push pre-run signal or post-resolution P&L
                    without bumping a tag.
4. Resolution     — once the market resolves, update report.json
                    with outcome, Brier scores, P&L. Append a
                    "Resolution" section to REPORT.md.
5. Commit         — chore(runs/NNN): resolved — outcome <Y/N>, P&L $<X>
```

## 4. `report.json` schema

The same JSON shape applies to every run. Unknown fields stay `null`
until they are observed.

```json
{
  "run_id": "002",
  "market": {
    "platform": "kalshi",
    "ticker": "<TBD>",
    "question": "<TBD>",
    "resolution_source": "NWS",
    "resolution_time_utc": "<TBD>"
  },
  "model": {
    "ensemble": ["ECMWF", "GraphCast", "GFS", "JMA"],
    "p_yes": null,
    "confidence": null
  },
  "market_snapshot_pre": {
    "mid": null, "bid": null, "ask": null, "ts_utc": null
  },
  "edge_bps": {
    "vs_market": null, "vs_climatology": null
  },
  "position": {
    "side": null, "size_usd": null, "paper": true
  },
  "resolution": {
    "outcome": null, "ts_utc": null,
    "brier_model": null, "brier_climatology": null,
    "pnl_usd": null
  }
}
```

Notes on field types:

- `p_yes`, `confidence` ∈ `[0, 1]`.
- `edge_bps.*` is in basis points (1 bp = 0.0001 = 0.01 %). Computed
  as `(p_yes_model − p_yes_market) × 10_000` for `vs_market` and
  `(p_yes_model − p_yes_climatology) × 10_000` for `vs_climatology`.
- `position.side` ∈ `"yes" | "no" | null`.
- `position.paper` is `true` until live trading is explicitly enabled.
- `resolution.outcome` ∈ `"yes" | "no" | null`.
- All timestamps are ISO 8601 with `Z` suffix (UTC).

## 5. Phase 1 go / no-go criterion

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
under this directory.

## 6. Where to look first

- `runs/001/` — backfill of the first executed run.
- `runs/002/` — the first run executed under this logging convention.
- `predictor/scripts/post_to_discord.py` — manual webhook poster for
  out-of-band updates (signal before tag, P&L after resolution).
- `.github/workflows/announce-release.yml` — auto-announce on
  `run-*` tags.
