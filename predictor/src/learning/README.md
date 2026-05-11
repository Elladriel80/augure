# `src/learning/` — feature-discovery workflow

This module turns the predictor stack into a **factor discovery engine**.
The Kalshi paper trades are the validation loop; the durable output is
the registry of *named, measured atmospheric / contextual factors* in
[`FEATURES.md`](./FEATURES.md).

## Workflow

```
   write hypothesis           train_learned.py             update FEATURES.md
   ───────────────►   in FEATURES.md    ──►   loop on the      ──►   keep / drop / iterate
   add feature fn                                  feature set
   in features.py
```

### 1 — Add a feature with an explicit hypothesis

Edit `features.py`:

```python
def f_my_new_idea(rec: dict) -> float | None:
    """One-sentence hypothesis: why does this drive market resolution?"""
    ...
```

Register it in `FEATURES_Vk` (or define `FEATURES_V{k+1}` if you need
to keep the previous spec stable for comparison).

Add a row to `FEATURES.md` BEFORE training, with `status: experimental`
and `brier_delta: TBD`. The hypothesis must be written **before** you
look at the measurement — that's how we keep ourselves honest about
post-hoc rationalisation.

### 2 — Train

```bash
python predictor/scripts/train_learned.py --feature-set v2
```

The script:

- Builds (X, y, meta) from `data/predictions/forward_*.json` joined with
  Kalshi resolutions.
- Chronological 70/30 split. Train on older rows, test on newer rows
  (no time leakage).
- Fits sklearn `LogisticRegression(penalty="l2")` on z-scored features.
- Scores test Brier and log-loss vs. `kalshi_mid` on the same test
  rows (the only bench that matters — beat the market).
- Writes the run to `predictor/runs_learning/<timestamp_utc>/run.json`.
- Computes `brier_delta` per active feature (leave-one-out: train and
  test with that feature removed, compare test Brier) and patches the
  corresponding rows in `FEATURES.md`.

### 3 — Read the contribution

Each run.json carries:

- `brier_test`, `brier_kalshi_mid_test` — the comparison.
- `feature_importances` — z-scored LR coefficients, name → coef.
- `feature_brier_deltas` — leave-one-out Brier delta per feature.
- `methodology` — explains how `brier_delta` was computed.

A negative `brier_delta` means **removing** the feature **worsened** the
test Brier, i.e. the feature contributed signal. Positive means the
feature was net noise on this split.

### 4 — Keep, drop, iterate

- `|brier_delta|` near zero on multiple runs → drop. Mark
  `status: dropped` and remove from the spec.
- Reliable negative `brier_delta` across runs → mark `status: active`,
  promote into the next baseline.
- New hypothesis fires → add a row, train, measure. Loop.

## Files

- [`FEATURES.md`](./FEATURES.md) — the registry. Source of truth for
  what we have measured, what we believe, what we dropped.
- `features.py` — each feature is a pure function `rec -> float | None`.
  `None` drops the row from training; no silent imputation.
- `dataset.py` — joins `forward_*.json` captures with live Kalshi
  resolutions to produce `(X, y, meta)`.
- `model.py` — thin sklearn `LogisticRegression` wrapper with Brier,
  log-loss, and standardised feature-importance helpers.
- `geographic.py` — builds `data/geographic/stations.json` once
  (Overpass + USGS + Natural Earth coastline). Provides the V2 static
  context features.

## Why named features, not opaque blobs

A learned model that beats `kalshi_mid` is useful as a trader. A
learned model that names *why* it beats `kalshi_mid` is useful as
domain knowledge. The latter compounds across markets, vendors, and
seasons — the former is just edge that decays. Augure builds the
latter.
