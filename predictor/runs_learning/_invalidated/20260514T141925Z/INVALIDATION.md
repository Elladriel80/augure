# Run 20260514T141925Z — INVALIDATED

**Status:** invalidated 2026-05-14
**Reason:** methodological — degenerate temporal split.

## Why this run is not usable

The `run.json` in this directory was produced before the temporal-split
correctif. Its reported metrics are not a measure of generalization:

- `train_date_range` and `test_date_range` both end at `20260512T144111Z`.
- The 116 test rows share a single `capture_at` value, because
  `keep_earliest_with_quote()` retained one row per ticker and a single
  `forward_predict` batch landed in the cut.
- The reported `brier_kalshi_mid_test = 0.0752` is anomalously low for
  the same reason: at a fixed snapshot, `yes_mid` is near-tautological
  with the outcome distribution. Phase-A.2 historical baseline is in
  the 0.12–0.14 range.
- The leave-one-out per-feature Brier deltas, the feature importances,
  and the train/test Brier gap are all describing one point in time —
  not forecast skill on unseen event-days.

Conclusion: this run's numbers must not be used to compare feature sets,
to update `CHAMPION.json`, or to inform GPU / training-spend decisions.

## Reference documentation

Full diagnosis, root cause, and correctif applied:

[predictor/docs/rapport-split-temporel-2026-05-14.md](../../docs/rapport-split-temporel-2026-05-14.md)

The correctif lives in:

- `predictor/scripts/train_learned.py` — `chronological_split()` is now
  group-aware on `split_key` (defaults to `target_date`), the run.json
  schema is v3, and runs below the cardinality threshold are marked
  `promotable: false`.
- `predictor/scripts/build_dashboard_manifest.py` — surfaces
  `split_key`, `*_split_range`, `n_distinct_test_split_values`, and
  `promotable`.

## Superseding run

The decision-gate re-run under `--split-key target_date` lives at
`predictor/runs_learning/20260514T191934Z/run.json`. It reports a clean
`brier_kalshi_mid_test ≈ 0.1305` (back inside the historical baseline
band) and `promotable: false` (test still spans a single `target_date`,
pending dataset growth — see §6.1 of the report).
