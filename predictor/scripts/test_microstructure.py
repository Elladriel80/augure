"""Tests rapides du module microstructure — pas de framework, juste des asserts.

Utilisation : python scripts/test_microstructure.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import MARKETS_DIR  # noqa: E402
from src.microstructure.distribution import (  # noqa: E402
    extract_bins,
    sum_yes_mid,
    implied_distribution,
    implied_mean_std,
)
from src.microstructure.biases import event_biases  # noqa: E402


def _load_raw(name: str) -> dict:
    return json.loads((MARKETS_DIR / f"{name}.json").read_text(encoding="utf-8"))


def test_extract_bins_austin() -> None:
    raw = _load_raw("KXHIGHAUS-26MAY08")
    bins = extract_bins(raw)
    assert len(bins) == 6, f"6 bins attendus pour Austin, vu {len(bins)}"
    # ordonnés par midpoint croissant
    midpoints = [b.midpoint for b in bins if b.midpoint is not None]
    assert midpoints == sorted(midpoints), "bins doivent être ordonnés par midpoint"
    print(f"  ✓ extract_bins Austin (6 bins, ordre OK)")


def test_sum_yes_mid_austin() -> None:
    """Les YES mids des 6 bins doivent sommer ~1 (mutuellement exclusifs)."""
    raw = _load_raw("KXHIGHAUS-26MAY08")
    bins = extract_bins(raw)
    s = sum_yes_mid(bins)
    assert s is not None
    # Tolérance large : la somme peut diverger de 1 à cause du vig + spread
    assert 0.7 < s < 1.6, f"sum_mid={s:.3f} hors plage attendue"
    print(f"  ✓ sum_yes_mid Austin = {s:.3f} (vig = {(s-1)*100:+.1f}%)")


def test_implied_distribution_normalized() -> None:
    raw = _load_raw("KXHIGHAUS-26MAY08")
    bins = extract_bins(raw)
    dist = implied_distribution(bins)
    assert dist, "distribution non vide attendue"
    total = sum(p for _, p in dist)
    assert abs(total - 1.0) < 1e-9, f"distribution doit sommer à 1, vu {total}"
    print(f"  ✓ implied_distribution normalisée à 1")


def test_implied_mean_std_austin() -> None:
    raw = _load_raw("KXHIGHAUS-26MAY08")
    bins = extract_bins(raw)
    res = implied_mean_std(bins)
    assert res is not None
    mean, std = res
    # Sanity : Austin début mai, on s'attend à une moyenne dans [70, 90]
    assert 70 <= mean <= 95, f"moyenne implicite {mean:.1f}°F hors plausible"
    assert 0 < std < 15, f"std implicite {std:.2f} hors plausible"
    print(f"  ✓ implied_mean_std Austin: µ={mean:.1f}°F, σ={std:.2f}°F")


def test_event_biases_austin() -> None:
    raw = _load_raw("KXHIGHAUS-26MAY08")
    bins = extract_bins(raw)
    bias = event_biases("KXHIGHAUS-26MAY08", bins)
    assert bias.n_bins == 6
    assert bias.n_quoted == 6
    assert bias.sum_mid is not None
    assert bias.median_spread is not None and bias.median_spread > 0
    # avec 6 bins on a extreme + central
    assert bias.extreme_spread_avg is not None
    assert bias.central_spread_avg is not None
    print(f"  ✓ event_biases Austin: vig={(1-bias.sum_mid)*100:+.1f}%, "
          f"spread médian={bias.median_spread:.3f}, "
          f"skew={bias.spread_skew:+.3f}")


def test_event_biases_rain_nyc_singleton() -> None:
    """Rain NYC n'a qu'un bin (binaire). Les biais agrégés doivent gérer le cas."""
    raw = _load_raw("KXRAINNYC-26MAY08")
    bins = extract_bins(raw)
    bias = event_biases("KXRAINNYC-26MAY08", bins)
    assert bias.n_bins == 1
    # extreme/central indéfinis car n_quoted < 4
    assert bias.extreme_spread_avg is None
    assert bias.central_spread_avg is None
    assert bias.spread_skew is None
    print(f"  ✓ event_biases Rain NYC (singleton): pas de skew calculé, OK")


def main() -> int:
    tests = [
        test_extract_bins_austin,
        test_sum_yes_mid_austin,
        test_implied_distribution_normalized,
        test_implied_mean_std_austin,
        test_event_biases_austin,
        test_event_biases_rain_nyc_singleton,
    ]
    print(f"Running {len(tests)} microstructure tests...\n")
    failed = 0
    for fn in tests:
        try:
            fn()
        except AssertionError as e:
            print(f"  ✗ {fn.__name__} FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ {fn.__name__} ERROR: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
