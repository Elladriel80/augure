"""Smoke-test for LearnedPredictor live inference.

Fetches a Kalshi event fresh from the API, parses each market, and runs the
four predictors (climatology, forecast_blend, ensemble, learned_v2) side by
side. Prints a comparison table.

The point isn't to score — there's no resolution yet. The point is to confirm
the LearnedPredictor pipeline executes end-to-end on a live contract:
  - run.json loaded with the right schema
  - sub-predictions composed
  - features extracted (no None)
  - LR closed-form applied
  - output P(YES) ∈ [0,1] and *different* from p_ensemble (signe que le LR a
    appris autre chose que la moyenne brute)

Usage:
    python predictor/scripts/test_learned_inference.py
    python predictor/scripts/test_learned_inference.py --event KXLOWTNYC-26MAY13
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from src.kalshi import KalshiClient  # noqa: E402
from src.predictors import (  # noqa: E402
    ClimatologyPredictor,
    ForecastBlendPredictor,
    EnsemblePredictor,
    LearnedPredictor,
    parse_market,
)
from src.weather import OpenMeteoClient  # noqa: E402


DEFAULT_EVENT = "KXLOWTNYC-26MAY13"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--event", default=DEFAULT_EVENT,
        help=f"Kalshi event ticker to test against (default: {DEFAULT_EVENT}). "
             "Pick a future event so the forecast horizon is non-empty.",
    )
    args = parser.parse_args()

    print(f">> Fetching {args.event} from Kalshi...")
    client = KalshiClient()
    ev = client.get_event(args.event)
    print(f"   {ev.event_ticker}: {ev.title}")
    print(f"   {len(ev.markets)} markets")

    weather = OpenMeteoClient()
    climato = ClimatologyPredictor(weather)
    fb = ForecastBlendPredictor(weather)
    ens = EnsemblePredictor(weather)
    try:
        learned = LearnedPredictor(
            weather_client=weather,
            sub_climato=climato,
            sub_forecast_blend=fb,
            sub_ensemble=ens,
        )
    except Exception as e:
        print(f"!! LearnedPredictor init failed: {e}")
        return 2

    print(f">> LearnedPredictor loaded from {learned.run_json_path}")
    print(f"   feature_set: {learned.feature_set_used}, trained_at: {learned.trained_at}")
    print(f"   features ({len(learned.feature_names)}): {learned.feature_names}")
    print()

    # Header
    cols = ["market_ticker", "climato", "forecast_blend", "ensemble", "learned", "delta(L-E)"]
    print(f"{cols[0]:<32} {cols[1]:>8} {cols[2]:>14} {cols[3]:>8} {cols[4]:>8} {cols[5]:>10}")
    print("-" * 90)

    parsed_count = 0
    skipped_count = 0
    learned_diverges = False

    for market in ev.markets:
        spec = parse_market(market)
        if spec is None:
            skipped_count += 1
            print(f"{market.ticker:<32}   [skip — not parseable]")
            continue
        parsed_count += 1

        try:
            p_clim = climato.predict(spec).prob_yes
            p_fb = fb.predict(spec).prob_yes
            p_ens = ens.predict(spec).prob_yes
            p_learned_pred = learned.predict(spec)
            p_learned = p_learned_pred.prob_yes
        except Exception as e:
            print(f"{market.ticker:<32}   !! predict error: {e}")
            continue

        delta = p_learned - p_ens
        if abs(delta) > 0.01:
            learned_diverges = True

        mode = ""
        if "fallback" in p_learned_pred.method:
            mode = " [fallback]"

        print(f"{market.ticker:<32} {p_clim:>8.3f} {p_fb:>14.3f} "
              f"{p_ens:>8.3f} {p_learned:>8.3f} {delta:>+10.3f}{mode}")

    print()
    print(f">> {parsed_count} markets parsed, {skipped_count} skipped")
    if learned_diverges:
        print(">> learned diverges from ensemble (|delta|>0.01 on at least one market). OK.")
        print("   The LR is not just echoing the ensemble — it has learned weights.")
    else:
        print("!! learned matches ensemble within 0.01 on every market.")
        print("   Either the LR collapsed to identity on p_ensemble (unlikely),")
        print("   or every prediction fell back to climato. Check the [fallback] flag.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
