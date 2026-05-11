# `predictor/runs_learning/` — training run ledger

One subdirectory per training run, named with a UTC timestamp
(`YYYYMMDDTHHMMSSZ`). Inside, `run.json` carries the canonical record:

```json
{
  "timestamp_utc": "20260511T123456Z",
  "feature_set_used": "v2",
  "feature_names": ["p_climatology", "...", "latitude"],
  "n_train": 96,
  "n_test": 42,
  "train_date_range": ["...", "..."],
  "test_date_range":  ["...", "..."],
  "brier_train": 0.0xxx,
  "brier_test":  0.0xxx,
  "brier_kalshi_mid_test": 0.0xxx,
  "log_loss_train": 0.xxx,
  "log_loss_test":  0.xxx,
  "log_loss_kalshi_mid_test": 0.xxx,
  "feature_importances": { "name": coef_std, ... },
  "feature_brier_deltas": { "name": delta, ... },
  "kept_features": ["..."],
  "dropped_features": [],
  "methodology": "leave-one-out Brier delta on the same test split; positive = feature added noise, negative = feature added signal",
  "notes": "..."
}
```

## How to read a run

1. **Did we beat `kalshi_mid`?** Compare `brier_test` to
   `brier_kalshi_mid_test` on the same rows. If `brier_test <
   brier_kalshi_mid_test`, the feature set has signal. If not, the
   set isn't enough yet — add a feature.
2. **Which features carried it?** Sort `feature_brier_deltas` ascending
   (more-negative = larger contribution). Cross-check with
   `feature_importances` (magnitude of z-scored coefficient). A feature
   strong on *both* is robust signal; strong on one but flat on the
   other is a single-run artifact.
3. **What was the regime?** `train_date_range` and `test_date_range`
   tell you the climate window. A model that wins on cool-spring test
   rows may lose on hot-summer rows — log such caveats in `notes`.

## Discipline

- A run.json is **immutable**. To re-train with a different split, write
  a new directory.
- `brier_kalshi_mid_test` is the **same row set** as `brier_test`. The
  comparison is meaningless otherwise — never aggregate across runs.
- Every `feature_set_used` value must be one of the registered specs in
  `src/learning/features.py` (`v0`, `v1`, `v2`, ...).

`FEATURES.md` is updated automatically by `train_learned.py` after each
run, using the measurements stored here.
