"""train_learned.py — train the learned predictor on resolved Kalshi events.

Phase A.3 entry point. Workflow:
  1. Load all forward_*.json captures + fetch resolutions from Kalshi.
  2. Extract features per resolved market for the chosen feature spec.
  3. Time-based split: train on the older 70% of EVENTS, test on the
     newer 30%. Default split key is `target_date` (the day the market
     resolves) — train on markets resolving earlier, test on later.
     This measures genuine forecast skill across distinct events.
     `capture_at` is available for back-compat but typically produces
     a degenerate single-timestamp test set with the current dataset
     builder (which keeps only the earliest snapshot per ticker), since
     batched forward_predict runs collapse many "first captures" onto
     the same instant.
  4. Fit LR L2 on train, score on test.
  5. Compare test-set Brier to kalshi_mid Brier on the same test set.
     This is the only benchmark that matters — beat the market.
  6. Compute per-feature contribution via leave-one-out on the same
     split (LOO Brier delta).
  7. Write a run record to predictor/runs_learning/<timestamp_utc>/run.json.
  8. Patch brier_delta + status columns in src/learning/FEATURES.md.

The bar to clear: test Brier < kalshi_mid Brier on the same rows.
If yes → this feature set has signal; promote.
If no → the current features aren't enough; ADD ONE, re-train, measure.

Promotion gate: a run is `promotable: true` only if the test set spans at
least PROMOTABLE_MIN_CARDINALITY distinct split-key values. Below that,
the test Brier is a point estimate, not generalization, and tooling that
edits CHAMPION.json (manual or automated) MUST refuse to promote from it.

Usage:
    python predictor/scripts/train_learned.py
    python predictor/scripts/train_learned.py --feature-set v2
    python predictor/scripts/train_learned.py --train-frac 0.6
    python predictor/scripts/train_learned.py --split-key capture_at
    python predictor/scripts/train_learned.py --no-update-features-md
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np

# Silence the sklearn 1.8 FutureWarning about LogisticRegression(penalty=)
# — we use the documented current API; migrating to l1_ratio is on the
# follow-up list when sklearn 1.10 drops the old kwarg.
warnings.filterwarnings(
    "ignore",
    message=".*penalty.*was deprecated.*",
    category=FutureWarning,
)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from src.learning.dataset import build  # noqa: E402
from src.learning.features import FEATURE_SETS, FEATURES_V0  # noqa: E402
from src.learning.model import LearnedModel, brier_score, log_loss  # noqa: E402


RUNS_DIR = ROOT / "runs_learning"
FEATURES_MD = ROOT / "src" / "learning" / "FEATURES.md"

# Minimum number of distinct split-key values in the test set required for
# a feature set to be eligible for promotion. Below this threshold the test
# Brier measures a single (or near-single) point in time and is not a
# generalization estimate — promoting on it would lock in noise. Promotion
# tooling (CHAMPION.json edits, future auto-promoter) MUST refuse runs
# where `promotable` is false. See rapport-split-temporel-2026-05-14 §6.
PROMOTABLE_MIN_CARDINALITY = 3


def chronological_split(X, y, meta, train_frac: float,
                        split_key: str = "target_date"):
    """Order rows by `split_key`, then take the first `train_frac` for
    training and the remainder for test, snapping the cut to a group
    boundary so no `split_key` value straddles train and test.

    With `split_key="target_date"`, all markets resolving on the same
    day land on the same side of the split. This eliminates boundary
    leakage and means the test set always measures generalization to
    *unseen event-days* — which is what we care about for forecast skill.

    Missing / null keys are pushed to the end (treated as "latest") so
    they never silently leak into the training set. If your meta lacks
    `split_key` entirely, every row ties; group-snapping then pushes
    everything to one side, which the degenerate-range warning in
    main() will surface.
    """
    def keyfn(i):
        v = meta[i].get(split_key) or ""
        # (True, ...) sorts AFTER (False, ...); flag missing with True
        # so unknown keys sort last.
        return (v == "", v)
    order = sorted(range(len(meta)), key=keyfn)
    X = [X[i] for i in order]
    y = [y[i] for i in order]
    meta = [meta[i] for i in order]

    target = int(len(X) * train_frac)
    target = max(1, min(len(X) - 1, target))  # at least 1 per side

    # Snap the cut to the first index where the key value changes,
    # walking BACK from the target (prefer the slightly smaller train
    # set to a leaky one). Falling back to walking forward if the
    # target is in a group that extends all the way to index 0.
    def _key_at(i):
        return meta[i].get(split_key)

    n_train = target
    if 0 < n_train < len(X) and _key_at(n_train - 1) == _key_at(n_train):
        # Walk back to find the first index where key changes.
        i = n_train
        while i > 1 and _key_at(i - 1) == _key_at(i):
            i -= 1
        backward = i
        # Walk forward as fallback.
        j = n_train
        while j < len(X) - 1 and _key_at(j) == _key_at(j - 1):
            j += 1
        forward = j
        # Pick whichever snap is closer to the target; tie → backward
        # (smaller train) so we never overshoot.
        if (n_train - backward) <= (forward - n_train):
            n_train = backward
        else:
            n_train = forward
    n_train = max(1, min(len(X) - 1, n_train))

    return (X[:n_train], y[:n_train], meta[:n_train],
            X[n_train:], y[n_train:], meta[n_train:])


def _fit_and_test_brier(Xtr, ytr, Xte, yte, feat_names: list[str]) -> float:
    """Train a fresh model on (Xtr restricted to feat_names) and return test Brier."""
    Xtr_r = [{k: r[k] for k in feat_names} for r in Xtr]
    Xte_r = [{k: r[k] for k in feat_names} for r in Xte]
    m = LearnedModel(feature_names=list(feat_names))
    m.fit(Xtr_r, ytr)
    return brier_score(yte, m.predict_proba(Xte_r))


def leave_one_out_brier_deltas(Xtr, ytr, Xte, yte,
                                feat_names: list[str],
                                baseline_brier: float) -> dict[str, float]:
    """For each feature, drop it, refit, score test Brier.

    delta = brier_without_feature - brier_full.
    Positive → feature *helped* (removing it hurt accuracy).
    Negative → feature was net noise.
    """
    deltas: dict[str, float] = {}
    if len(feat_names) <= 1:
        return {n: 0.0 for n in feat_names}
    for held in feat_names:
        remaining = [n for n in feat_names if n != held]
        b_without = _fit_and_test_brier(Xtr, ytr, Xte, yte, remaining)
        deltas[held] = float(b_without - baseline_brier)
    return deltas


def update_features_md(deltas: dict[str, float], status_for: dict[str, str]) -> None:
    """Patch the brier_delta and status columns of FEATURES.md.

    The registry uses Markdown table rows of the form
    | `name` | hypothesis | source | date_added | brier_delta | status |
    We look up each row by the backtick-wrapped feature name in column 1
    and rewrite columns 5 (brier_delta) and 6 (status). Leaves all other
    rows untouched.
    """
    if not FEATURES_MD.exists():
        print(f"  [warn] {FEATURES_MD} missing; skipping registry update.")
        return
    text = FEATURES_MD.read_text(encoding="utf-8")
    lines = text.splitlines()
    out = []
    for line in lines:
        s = line.strip()
        if s.startswith("|") and s.endswith("|") and not s.startswith("|---") and not s.startswith("| name "):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if len(cells) >= 6:
                name_cell = cells[0]
                # Match "`feature_name`"
                if name_cell.startswith("`") and name_cell.endswith("`"):
                    fname = name_cell[1:-1]
                    if fname in deltas:
                        cells[4] = f"{deltas[fname]:+.4f}"
                    if fname in status_for:
                        cells[5] = status_for[fname]
                    line = "| " + " | ".join(cells) + " |"
        out.append(line)
    FEATURES_MD.write_text("\n".join(out) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-set", choices=sorted(FEATURE_SETS.keys()),
                        default="v0",
                        help="Which feature spec to train on. See "
                             "src/learning/features.py.")
    parser.add_argument("--train-frac", type=float, default=0.7)
    parser.add_argument("--split-key",
                        choices=["target_date", "capture_at"],
                        default="target_date",
                        help="Field used to chronologically order rows before "
                             "the train/test split. target_date (default) "
                             "splits by the date each market resolves, "
                             "measuring forecast skill across distinct events. "
                             "capture_at splits by snapshot timestamp; with "
                             "the current dataset builder this typically "
                             "collapses test into a single batch (degenerate).")
    parser.add_argument("--no-update-features-md", action="store_true",
                        help="Skip patching brier_delta into FEATURES.md.")
    parser.add_argument("--no-write-run", action="store_true",
                        help="Skip writing the run record to runs_learning/.")
    parser.add_argument("--notes", default="",
                        help="Free-text note saved alongside the run.")
    args = parser.parse_args()

    spec = FEATURE_SETS.get(args.feature_set, FEATURES_V0)
    feat_names = [name for name, _ in spec]
    print(f">> feature set: {args.feature_set} = {feat_names}")

    print(">> building dataset (this fetches Kalshi resolutions)...")
    X, y, meta = build(spec)
    print(f">> rows after feature extraction + outcome join: {len(X)}")
    if len(X) < 20:
        print("!! sample too small for a meaningful split. need more "
              "resolved events. abort.")
        return 1

    Xtr, ytr, mtr, Xte, yte, mte = chronological_split(X, y, meta,
                                                       args.train_frac,
                                                       split_key=args.split_key)
    print(f">> split key: {args.split_key} (train_frac={args.train_frac})")
    print(f">> train n={len(Xtr)}  test n={len(Xte)}")

    def _range(rows, key):
        vals = [r.get(key) for r in rows if r.get(key)]
        if not vals:
            return "(none)..(none)"
        return f"{min(vals)}..{max(vals)}"

    print(f">> train {args.split_key} range: {_range(mtr, args.split_key)}")
    print(f">> test  {args.split_key} range: {_range(mte, args.split_key)}")

    # Degenerate-split guard: if the test set spans a single value of the
    # split key, we're measuring the model on one snapshot/event-day instead
    # of generalization. Loud warning, but don't abort — caller may want
    # the run for diagnostics.
    test_vals = {r.get(args.split_key) for r in mte if r.get(args.split_key)}
    train_vals = {r.get(args.split_key) for r in mtr if r.get(args.split_key)}
    n_distinct_test = len(test_vals)
    promotable = n_distinct_test >= PROMOTABLE_MIN_CARDINALITY
    if len(test_vals) <= 1:
        print()
        print("!! WARNING: test set spans only "
              f"{len(test_vals)} distinct {args.split_key} value(s).")
        print("   Brier deltas measured here are NOT generalization "
              "estimates — they describe a single point in time.")
        print(f"   Consider --split-key target_date, more captures, "
              "or a wider train_frac.")
    if test_vals & train_vals:
        leaked = sorted(test_vals & train_vals)[:5]
        print()
        print(f"!! WARNING: {len(test_vals & train_vals)} {args.split_key} "
              f"value(s) appear in BOTH train and test: {leaked}")
        print("   Boundary leakage — train and test are not cleanly "
              "separated on the split axis.")

    model = LearnedModel(feature_names=feat_names)
    model.fit(Xtr, ytr)

    p_train = model.predict_proba(Xtr)
    b_train = brier_score(ytr, p_train)
    ll_train = log_loss(ytr, p_train)

    p_test = model.predict_proba(Xte)
    b_test = brier_score(yte, p_test)
    ll_test = log_loss(yte, p_test)

    # Same-rows kalshi_mid benchmark (only meaningful if computed on the
    # EXACT same test set as the learned model).
    mid_test = np.array([m["yes_mid"] for m in mte], dtype=float)
    b_mid_test = brier_score(yte, mid_test)
    ll_mid_test = log_loss(yte, mid_test)

    print()
    print(f"{'metric':<10}  {'train':>10}  {'test':>10}  {'kalshi_mid (test)':>20}")
    print("-" * 60)
    print(f"{'n':<10}  {len(Xtr):>10}  {len(Xte):>10}  {len(mte):>20}")
    print(f"{'Brier':<10}  {b_train:>10.4f}  {b_test:>10.4f}  {b_mid_test:>20.4f}")
    print(f"{'LogLoss':<10}  {ll_train:>10.4f}  {ll_test:>10.4f}  {ll_mid_test:>20.4f}")

    print()
    if b_test < b_mid_test:
        gap = b_mid_test - b_test
        print(f">> learned model BEATS kalshi_mid by {gap:.4f} Brier on test.")
        print(f"   this feature set has signal. consider it the new baseline.")
    else:
        gap = b_test - b_mid_test
        print(f">> learned model LOSES to kalshi_mid by {gap:.4f} Brier on test.")
        print(f"   add a feature, re-train, measure again.")

    print()
    if promotable:
        print(f">> PROMOTABLE: yes (test spans {n_distinct_test} distinct "
              f"{args.split_key} values, threshold "
              f"{PROMOTABLE_MIN_CARDINALITY}).")
    else:
        print(f"!! NOT PROMOTABLE: test spans only {n_distinct_test} "
              f"distinct {args.split_key} value(s); threshold is "
              f"{PROMOTABLE_MIN_CARDINALITY}.")
        print("   Brier on this run measures a point in time, not "
              "generalization. Do NOT update CHAMPION.json from it.")

    importances = sorted(model.feature_importance(),
                         key=lambda kv: abs(kv[1]),
                         reverse=True)
    print()
    print(">> feature importances (standardized LR coefficients):")
    for name, coef in importances:
        bar = "#" * min(40, int(abs(coef) * 20))
        sign = "+" if coef >= 0 else "-"
        print(f"   {name:<22} {sign}{abs(coef):.3f}  {bar}")

    # ---- Leave-one-out per-feature brier delta ----
    # Methodology choice: with N usually under 200 and <10 features, LOO
    # is cheap (one extra LR fit per feature) AND directly measures the
    # quantity we care about — how much each feature actually moves the
    # test Brier. Standardized coefficient magnitude is reported alongside
    # for cross-checking but is not the primary contribution metric.
    print()
    print(">> leave-one-out test Brier deltas (positive = feature added signal):")
    deltas = leave_one_out_brier_deltas(Xtr, ytr, Xte, yte, feat_names, b_test)
    for name, d in sorted(deltas.items(), key=lambda kv: -kv[1]):
        sign = "+" if d >= 0 else "-"
        bar = "#" * min(40, int(abs(d) * 400))  # scale ~0.0025 = 1 char
        print(f"   {name:<22} {sign}{abs(d):.4f}  {bar}")

    # ---- Persist run record ----
    # We serialize the full fitted-model state so that downstream code
    # (e.g. predictor/src/predictors/learned.py for live inference) can
    # reconstruct sigmoid(intercept + Σ coef_i · (x_i − mean_i) / std_i)
    # without re-fitting. Without these three blocks, a run.json only
    # supports analytics, not inference.
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    run_dir = RUNS_DIR / ts
    if not args.no_write_run:
        run_dir.mkdir(parents=True, exist_ok=True)
        intercept = float(model.clf.intercept_[0])
        feature_means = dict(zip(feat_names, model.scaler.mean_.tolist()))
        feature_stds = dict(zip(feat_names, model.scaler.scale_.tolist()))
        record = {
            "schema_version": 3,
            "timestamp_utc": ts,
            "feature_set_used": args.feature_set,
            "feature_names": feat_names,
            "model_class": "sklearn.linear_model.LogisticRegression",
            "model_hyperparams": {
                "penalty": "l2",
                "C": 1.0,
                "solver": "lbfgs",
                "max_iter": 2000,
                "random_state": 42,
            },
            "n_train": len(Xtr),
            "n_test": len(Xte),
            "split_key": args.split_key,
            "train_frac": args.train_frac,
            "train_split_range": [
                min((r.get(args.split_key) for r in mtr if r.get(args.split_key)), default=None),
                max((r.get(args.split_key) for r in mtr if r.get(args.split_key)), default=None),
            ],
            "test_split_range": [
                min((r.get(args.split_key) for r in mte if r.get(args.split_key)), default=None),
                max((r.get(args.split_key) for r in mte if r.get(args.split_key)), default=None),
            ],
            "n_distinct_test_split_values": n_distinct_test,
            "promotable": promotable,
            "promotable_min_cardinality": PROMOTABLE_MIN_CARDINALITY,
            # Legacy fields preserved for back-compat with older run.json
            # readers (dashboard manifest, FEATURES.md patcher, etc.).
            "train_date_range": [
                min((r.get("capture_at") for r in mtr if r.get("capture_at")), default=None),
                max((r.get("capture_at") for r in mtr if r.get("capture_at")), default=None),
            ],
            "test_date_range":  [
                min((r.get("capture_at") for r in mte if r.get("capture_at")), default=None),
                max((r.get("capture_at") for r in mte if r.get("capture_at")), default=None),
            ],
            "brier_train": b_train,
            "brier_test": b_test,
            "brier_kalshi_mid_test": b_mid_test,
            "log_loss_train": ll_train,
            "log_loss_test": ll_test,
            "log_loss_kalshi_mid_test": ll_mid_test,
            "intercept": intercept,
            "feature_means": feature_means,
            "feature_stds": feature_stds,
            "feature_importances": {n: c for n, c in importances},
            "feature_brier_deltas": deltas,
            "kept_features": feat_names,
            "dropped_features": [],
            "methodology": (
                "Leave-one-out Brier delta: for each feature, refit the model "
                "without it on the same train/test split and record "
                "(brier_test_without - brier_test_full). Positive = removing "
                "the feature hurt accuracy = feature carried signal."
            ),
            "inference_formula": (
                "p_yes = sigmoid(intercept + sum_i coef_i * (x_i - mean_i) / std_i) "
                "where coef_i = feature_importances[i], mean_i = feature_means[i], "
                "std_i = feature_stds[i]. sigmoid(z) = 1 / (1 + exp(-z))."
            ),
            "notes": args.notes,
        }
        (run_dir / "run.json").write_text(
            json.dumps(record, indent=2), encoding="utf-8"
        )
        print()
        print(f">> wrote {run_dir/'run.json'}")

    # ---- Patch FEATURES.md ----
    if not args.no_update_features_md:
        # Classify: positive delta = signal, near zero = ambiguous, negative = noise.
        status_for: dict[str, str] = {}
        for n, d in deltas.items():
            if d > 0.001:
                status_for[n] = "active"
            elif d < -0.001:
                status_for[n] = "experimental"  # leave room for a confirming run
            else:
                status_for[n] = "experimental"
        update_features_md(deltas, status_for)
        print(f">> patched brier_delta + status in {FEATURES_MD}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
