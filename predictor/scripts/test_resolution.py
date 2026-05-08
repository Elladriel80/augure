"""Tests rapides du module de résolution NWS — pas de framework, juste des asserts.

Utilisation : python scripts/test_resolution.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import MARKETS_DIR  # noqa: E402
from src.kalshi.models import Event  # noqa: E402
from src.kalshi.resolution import (   # noqa: E402
    apply_nws_rounding,
    extract_resolution_rule,
    extract_station,
    infer_variable,
    would_resolve_yes,
)


def _load_event(name: str) -> Event:
    path = MARKETS_DIR / f"{name}.json"
    return Event.from_api(json.loads(path.read_text(encoding="utf-8")))


def test_rounding_temp() -> None:
    # NWS round half up
    assert apply_nws_rounding(75.4, "nearest_int") == 75
    assert apply_nws_rounding(75.5, "nearest_int") == 76
    assert apply_nws_rounding(75.6, "nearest_int") == 76
    assert apply_nws_rounding(76.5, "nearest_int") == 77   # diffère de Python round()
    assert apply_nws_rounding(-10.5, "nearest_int") == -10
    assert apply_nws_rounding(-10.6, "nearest_int") == -11
    print("  ✓ rounding temp (round half up)")


def test_rounding_precip() -> None:
    assert apply_nws_rounding(0.014, "nearest_0.01") == 0.01
    assert apply_nws_rounding(0.015, "nearest_0.01") == 0.02
    assert apply_nws_rounding(1.234, "nearest_0.01") == 1.23
    print("  ✓ rounding precip (0.01\")")


def test_infer_variable() -> None:
    assert infer_variable("KXHIGHAUS") == "temp_max"
    assert infer_variable("KXLOWTSEA") == "temp_min"
    assert infer_variable("KXRAINNYC") == "precip_in"
    assert infer_variable("KXSNOWBOS") == "snow_in"
    print("  ✓ infer_variable")


def test_extract_station_text() -> None:
    s = extract_station(
        "If the highest temperature recorded in Austin Bergstrom for May 08, 2026 ...",
        series_ticker="KXHIGHAUS-26MAY08-T76",
    )
    assert s is not None and s.cli_code == "CLIAUS"

    s = extract_station(
        "If the number of inches of precipitation recorded at Central Park, "
        "New York on May 08, 2026 is strictly greater than 0...",
        series_ticker="KXRAINNYC-26MAY08-T0",
    )
    assert s is not None and s.cli_code == "CLINYC"

    s = extract_station(
        "If the total precipitation at CLIMDW in Chicago in May 2026 is strictly "
        "greater than 1 inches...",
        series_ticker="KXRAINCHIM-26MAY-1",
    )
    assert s is not None and s.cli_code == "CLIMDW"
    print("  ✓ extract_station (Austin / NYC / Midway)")


def test_resolve_austin_high_T76() -> None:
    """KXHIGHAUS-26MAY08-T76 : strike less, cap=76. NWS arrondit à l'entier."""
    ev = _load_event("KXHIGHAUS-26MAY08")
    market = next(m for m in ev.markets if m.ticker == "KXHIGHAUS-26MAY08-T76")
    rule = extract_resolution_rule(market)
    assert rule is not None
    assert rule.strike_type == "less"
    assert rule.cap_strike == 76
    assert rule.station and rule.station.cli_code == "CLIAUS"

    # obs 75.4°F → arrondi 75 → 75 < 76 → YES
    assert would_resolve_yes(rule, 75.4) is True
    # obs 75.5°F → arrondi 76 (round half up) → 76 < 76 = False → NO
    assert would_resolve_yes(rule, 75.5) is False
    # obs 75.6°F → arrondi 76 → NO  (l'edge: trader naïf voit 75.6 et pense YES)
    assert would_resolve_yes(rule, 75.6) is False
    # obs 74.9°F → arrondi 75 → YES
    assert would_resolve_yes(rule, 74.9) is True
    print("  ✓ Austin T76 (less): arrondi NWS bascule la résolution comme attendu")


def test_resolve_austin_high_B76() -> None:
    """KXHIGHAUS-26MAY08-B76.5 : between, floor=76, cap=77."""
    ev = _load_event("KXHIGHAUS-26MAY08")
    market = next(m for m in ev.markets if m.ticker == "KXHIGHAUS-26MAY08-B76.5")
    rule = extract_resolution_rule(market)
    assert rule is not None
    assert rule.strike_type == "between"
    assert rule.floor_strike == 76 and rule.cap_strike == 77

    assert would_resolve_yes(rule, 75.6) is True   # arrondi 76, dans [76,77]
    assert would_resolve_yes(rule, 77.4) is True   # arrondi 77, dans [76,77]
    assert would_resolve_yes(rule, 77.5) is False  # arrondi 78 → hors borne
    assert would_resolve_yes(rule, 75.4) is False  # arrondi 75 → hors borne
    print("  ✓ Austin B76.5 (between): bornes inclusives sur l'arrondi")


def test_resolve_austin_high_T83() -> None:
    """KXHIGHAUS-26MAY08-T83 : greater, floor=83 (open-ended haut)."""
    ev = _load_event("KXHIGHAUS-26MAY08")
    market = next(m for m in ev.markets if m.ticker == "KXHIGHAUS-26MAY08-T83")
    rule = extract_resolution_rule(market)
    assert rule is not None
    assert rule.strike_type == "greater"
    assert rule.floor_strike == 83

    assert would_resolve_yes(rule, 84.0) is True   # arrondi 84 > 83
    assert would_resolve_yes(rule, 83.5) is True   # arrondi 84 > 83 (round half up)
    assert would_resolve_yes(rule, 83.4) is False  # arrondi 83, pas > 83
    print("  ✓ Austin T83 (greater): seuil exclusif sur l'arrondi")


def test_resolve_rain_nyc_with_trace() -> None:
    """KXRAINNYC-26MAY08-T0 : rain >0, Trace=YES quand seuil=0."""
    ev = _load_event("KXRAINNYC-26MAY08")
    market = next(m for m in ev.markets if m.ticker == "KXRAINNYC-26MAY08-T0")
    rule = extract_resolution_rule(market)
    assert rule is not None
    assert rule.strike_type == "greater"
    assert rule.floor_strike == 0
    assert rule.trace_is_yes is True
    assert rule.station and rule.station.cli_code == "CLINYC"

    # 0.01" -> arrondi 0.01 > 0 → YES
    assert would_resolve_yes(rule, 0.01) is True
    # 0" exact + pas de trace -> NO
    assert would_resolve_yes(rule, 0.0, is_trace=False) is False
    # 0" exact + trace coded → YES (convention NWS)
    assert would_resolve_yes(rule, 0.0, is_trace=True) is True
    print("  ✓ NYC Rain (greater, trace=YES sur seuil 0)")


def test_resolve_rain_chicago_above_1inch_no_trace() -> None:
    """KXRAINCHIM-26MAY-1 : pluie cumulée mensuelle > 1\" → trace ne suffit PAS."""
    ev = _load_event("KXRAINCHIM-26MAY")
    market = next(m for m in ev.markets if m.ticker == "KXRAINCHIM-26MAY-1")
    rule = extract_resolution_rule(market)
    assert rule is not None
    assert rule.strike_type == "greater"
    assert rule.floor_strike == 1
    assert rule.station and rule.station.cli_code == "CLIMDW"

    # 0.5" cumul → arrondi 0.50, pas > 1 → NO
    assert would_resolve_yes(rule, 0.5) is False
    # 1.01" → 1.01 > 1 → YES
    assert would_resolve_yes(rule, 1.01) is True
    # Trace flag ne doit JAMAIS faire passer un seuil > 0 à YES
    assert would_resolve_yes(rule, 0.0, is_trace=True) is False
    print("  ✓ Chicago Rain >1\" : Trace ne court-circuite pas un seuil non-zero")


def main() -> int:
    tests = [
        test_rounding_temp,
        test_rounding_precip,
        test_infer_variable,
        test_extract_station_text,
        test_resolve_austin_high_T76,
        test_resolve_austin_high_B76,
        test_resolve_austin_high_T83,
        test_resolve_rain_nyc_with_trace,
        test_resolve_rain_chicago_above_1inch_no_trace,
    ]
    print(f"Running {len(tests)} resolution tests...\n")
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
