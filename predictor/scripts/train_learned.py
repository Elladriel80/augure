"""train_learned.py — train the learned predictor on resolved Kalshi events.

Phase A.3 entry point. Workflow:
  1. Load all forward_*.json captures + fetch resolutions from Kalshi.
  2. Extract features (FEATURES_V0 by default) per resolved market.
  3. Time-based split: train on the older 70%, test on the newer 30%.
  4. Fit LR L2 on train, score on test.
  5. Compare test-set Brier to kalshi_mid Brier on the same test set
     (this is the only benchmark that matters — beat the market).
  6. Print feature importances (standardized coefficients).

The bar to clear: test Brier < kalshi_mid Brier on the same rows.
If yes → this feature set has signal, commit and iterate by adding
features. If no → the current features aren't enough, ADD ONE and
re-train.

Usage:
    python predictor/scripts/train_learned.py
    python predictor/scripts/train_learned.py --train-frac 0.6
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from src.learning.dataset import build  # noqa: E402
from src.learning.features import FEATURES_V0  # noqa: E402
from src.learning.model import LearnedModel, brier_score, log_loss  # noqa: E402


def chronological_split(X, y, meta, train_frac: float):
    """Sort by capture timestamp, split into train (older) / test (newer)."""
    order = sorted(range(len(meta)), key=lambda i: meta[i].get("capture_at", ""))
    X = [X[i] for i in order]
    y = [y[i] for i in order]
    meta = [meta[i] for i in order]
    n_train = int(len(X) * train_frac)
    return (X[:n_train], y[:n_train], meta[:n_train],
            X[n_train:], y[n_train:], meta[n_train:])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-frac", type=float, default=0.7,
                        help="Fraction of rows used for training (older "
                             "chronologically). Rest = test set.")
    args = parser.parse_args()

    spec = FEATURES_V0
    feat_names = [name for name, _ in spec]
    print(f">> feature set: {feat_names}")

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

    # Train metrics (sanity)
    p_train = model.predict_proba(Xtr)
    b_train = brier_score(ytr, p_train)
    ll_train = log_loss(ytr, p_train)

    # Test metrics
    p_test = model.predict_proba(Xte)
    b_test = brier_score(yte, p_test)
    ll_test = log_loss(yte, p_test)

    # Same-rows kalshi_mid benchmark
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
        print(f">> ✓ learned model BEATS kalshi_mid by {gap:.4f} Brier on test.")
        print(f"   this feature set has signal. consider it the new baseline.")
    else:
        gap = b_test - b_mid_test
        print(f">> ✗ learned model loses to kalshi_mid by {gap:.4f} Brier on test.")
        print(f"   add a feature, re-train, measure again.")

    print()
    print(">> feature importances (standardized LR coefficients):")
    importances = sorted(model.feature_importance(),
                         key=lambda kv: abs(kv[1]),
                         reverse=True)
    for name, coef in importances:
        bar = "█" * min(40, int(abs(coef) * 20))
        sign = "+" if coef >= 0 else "−"
        print(f"   {name:<22} {sign}{abs(coef):.3f}  {bar}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
