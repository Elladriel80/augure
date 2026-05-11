"""train_learned.py — train the learned predictor on resolved Kalshi events.

Phase A.3 entry point. Workflow:
  1. Load all forward_*.json captures + fetch resolutions from Kalshi.
  2. Extract features per resolved market for the chosen feature spec.
  3. Time-based split: train on the older 70%, test on the newer 30%.
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

Usage:
    python predictor/scripts/train_learned.py
    python predictor/scripts/train_learned.py --feature-set v2
    python predictor/scripts/train_learned.py --train-frac 0.6
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


def chronological_split(X, y, meta, train_frac: float):
    order = sorted(range(len(meta)), key=lambda i: meta[i].get("capture_at", ""))
    X = [X[i] for i in order]
    y = [y[i] for i in order]
    meta = [meta[i] for i in order]
    n_train = int(len(X) * train_frac)
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
                                                       args.train_frac)
    print(f">> train n={len(Xtr)}  test n={len(Xte)}")
    print(f">> train date range: {mtr[0]['capture_at']}..{mtr[-1]['capture_at']}")
    print(f">> test  date range: {mte[0]['capture_at']}..{mte[-1]['capture_at']}")

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
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    run_dir = RUNS_DIR / ts
    if not args.no_write_run:
        run_dir.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp_utc": ts,
            "feature_set_used": args.feature_set,
            "feature_names": feat_names,
            "n_train": len(Xtr),
            "n_test": len(Xte),
            "train_date_range": [mtr[0]["capture_at"], mtr[-1]["capture_at"]],
            "test_date_range":  [mte[0]["capture_at"], mte[-1]["capture_at"]],
            "brier_train": b_train,
            "brier_test": b_test,
            "brier_kalshi_mid_test": b_mid_test,
            "log_loss_train": ll_train,
            "log_loss_test": ll_test,
            "log_loss_kalshi_mid_test": ll_mid_test,
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
