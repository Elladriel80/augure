# predictor/runs/

Public, append-only record of every Phase 1 prediction-market run.
Aratea Phase 1 is about measuring a predictive edge before any
decentralized parametric mutual is built — every paper or live
position has to leave a trace here.

## Supported platforms

- **Kalshi** — Phase 1 primary and only venue. Mature daily weather
  bin markets, real liquidity, NWS-tied automatic resolution.
- **Polymarket** — *Evaluated and dropped for Phase 1 on 2026-05-14*.
  Three blocking reasons: (i) no recurring daily weather markets
  (only ad-hoc events like hurricane / seasonal snow), which prevents
  building a statistically comparable N over time; (ii) crypto-native
  and US-geofenced investor base introduces structural pricing biases
  that disqualify the Polymarket mid as a market-truth benchmark for
  weather; (iii) UMA oracle settlement (2–7 days, disputable) adds
  operational friction with no methodological gain over NWS auto-
  settlement.

  The log schema below still tolerates multiple venues in `markets[]`
  for forward compatibility, but the predictor and `daily_auto.py`
  currently target Kalshi only. If a future phase brings markets that
  Kalshi doesn't list, we'll revisit per-venue, not as a blanket
  re-onboarding.

## Layout

```
predictor/runs/
├── CONVENTION.md            naming, schema, workflow, go/no-go
├── 001/
│   ├── REPORT.md            builder log
│   └── report.json          machine-readable record
└── NNN/                     one folder per run
    ├── PRE_RUN.md           Discord #predictions, posted at open
    ├── POST_RUN.md          Discord #pnl-tracker, posted at resolution
    ├── X_THREAD_EN.md       X / Twitter — pre + post tweets, EN
    ├── X_THREAD_FR.md       X / Twitter — pre + post tweets, FR
    └── report.json          machine-readable record
```

## Workflow at a glance

```
   open       tag           announce CI                 resolve         update
  ──────►  run-NNN  ──────►  Discord+X    ──────►   wait market   ──────► report.json
                              auto fires             resolution            +REPORT.md
                                                                           commit
```

Ordered:

1. **Open** — fill the pre-run sections of `runs/NNN/REPORT.md` and
   `report.json`. Commit.
2. **Tag** — annotated `git tag run-NNN`. Push.
   `.github/workflows/announce-release.yml` auto-posts to Discord and X
   from the tag's annotated message.
3. **Manual posts** *(optional)* — `predictor/scripts/post_to_discord.py`
   sends a markdown file to any channel via webhook, for updates that
   don't warrant a tag (signal, P&L, mid-run note).
4. **Resolve** — once the market settles, fill the resolution fields
   in `report.json`, append a Resolution section to `REPORT.md`.
   Commit.

## Phase 1 success criterion

Validated *only* if, on N > 50 resolved runs, the meta-ensemble's
Brier score is strictly lower than **both** the best single model
**and** climatology, on the same N events. Failing either condition
is a no-go: the project pivots or stops.

The criterion is encoded in the union of `report.json` files — no
separate scoreboard needed.

## See also

- [`CONVENTION.md`](./CONVENTION.md) — full convention.
- [`../scripts/post_to_discord.py`](../scripts/post_to_discord.py) — manual webhook poster.
- [`../../.github/workflows/announce-release.yml`](../../.github/workflows/announce-release.yml) — tag-driven announce CI.
