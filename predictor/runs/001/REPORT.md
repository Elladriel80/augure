# Run 001 — pipeline dry-run on 2026-05-08

*Builder log. Backfilled from local artifacts on 2026-05-10. Honest
about the gap: this run was executed but never logged publicly at
the time, which is precisely the failure that motivated the present
logging convention.*

## What actually happened on 2026-05-08

The full predictor pipeline was exercised end-to-end on Kalshi
weather-temperature markets:

1. **Markets fetched** — 60 contracts across 6 US cities (Austin,
   Chicago, Denver, Miami, Philadelphia, San Antonio), high/low
   temperature contracts of the `KXHIGH*` / `KXLOWT*` series, target
   date 2026-05-08.
2. **Forecasts pulled** — multi-model raw output for each city
   (ECMWF AIFS, ECMWF IFS 0.25°, GFS, GraphCast, JMA GSM) plus
   single-model forecasts. Stored under
   `predictor/data/forecasts/forecast_multi__multi_*_2026-05-08_*.json`.
3. **Predictors run** — three predictors produced a `p_yes` per
   contract: `climatology`, `forecast_blend`, `ensemble`. Output:
   `predictor/data/predictions/forward_20260508T104500Z.json`
   (60 records, 3 predictors each).
4. **Microstructure audit** — orderbook structure scanned across
   40 events:
   `predictor/data/audits/microstructure_20260508T094135Z.json`.
5. **Resolution audit** — NWS station mapping verified:
   `predictor/data/audits/resolution_audit_20260508T094135Z.json`.
6. **Climatology backtest** — historical baseline computed:
   `predictor/data/backtests/backtest_climatology_20260508T072310Z.json`.

## What did NOT happen

- **No paper position was opened.**
  `predictor/data/ledger/paper_bets.csv` contains a header row and
  zero data rows. The pipeline produced predictions but no market
  was selected for entry.
- **No public log was posted** at the time. Discord and X were
  silent. There is no `run-001` Git tag.
- **No edge measurement was published** — neither vs market nor vs
  climatology, even though the data needed to compute both is on
  disk.

## Why this matters

Run 001 is best read as a **methodology validation**, not a trade:
the daily routine ran cleanly, all six steps produced output, the
artifacts are reproducible from `predictor/scripts/daily_run.py`.
That is useful, but it does not produce evidence toward the Phase 1
go/no-go criterion (N>50 resolved positions, meta-ensemble beating
best single model AND climatology). Until a position is taken and
resolved, the criterion's denominator stays at zero.

The present logging convention (`predictor/runs/CONVENTION.md`)
exists so that no future run is invisible the way Run 001 was.

## Reproducibility pointers

To replay this run from a fresh checkout:

```bash
cd predictor
python scripts/daily_run.py
```

The artifacts above will be regenerated under `predictor/data/`
with fresh timestamps, modulo any change in the live Kalshi
orderbook and weather forecasts since 2026-05-08.

## TODO carried into the PR

- [ ] **Re-run** as Run 002 with at least one paper position opened
      and tagged `run-002`, so the ledger and the report.json
      `position` and `resolution` fields are non-null and the
      Phase 1 sample size N becomes 1.

## Trace

- Tag — none. Backfill, no `run-001` tag created.
- Auto-announce — none.
- Manual posts — none.
- Commits documenting Run 001 — added under
  `feat/run-002-logging` branch on 2026-05-10.
