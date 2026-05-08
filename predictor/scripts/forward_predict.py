"""Capture quotidienne des prédictions des trois predictors sur le panel Kalshi du jour.

À lancer chaque jour idéalement vers 14:00 UTC (après mise à jour des forecasts AM
et avant le close des markets J+1). Stocke les prédictions horodatées pour pouvoir
les scorer plus tard contre les résolutions NWS.

Usage:
    python scripts/forward_predict.py
    python scripts/forward_predict.py --predictors climatology,ensemble
    python scripts/forward_predict.py --series KXHIGHAUS,KXLOWTSEA

Sortie : data/predictions/forward_<TIMESTAMP>.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from src.config import MARKETS_DIR, DATA_DIR  # noqa: E402
from src.kalshi.models import Event  # noqa: E402
from src.predictors.parsers import parse_market  # noqa: E402
from src.predictors.climatology import ClimatologyPredictor  # noqa: E402
from src.predictors.forecast_blend import ForecastBlendPredictor  # noqa: E402
from src.predictors.ensemble import EnsemblePredictor  # noqa: E402
from src.weather import OpenMeteoClient  # noqa: E402


PREDICTOR_FACTORIES = {
    "climatology": lambda w: ClimatologyPredictor(w),
    "forecast_blend": lambda w: ForecastBlendPredictor(w),
    "ensemble": lambda w: EnsemblePredictor(w),
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictors", default="climatology,forecast_blend,ensemble",
                        help="Liste de predictors (virgule-séparée)")
    parser.add_argument("--series", default="",
                        help="Filtre par préfixes série (vide = tous les snapshots dispo)")
    args = parser.parse_args()

    predictor_names = [p.strip() for p in args.predictors.split(",") if p.strip()]
    unknown = [p for p in predictor_names if p not in PREDICTOR_FACTORIES]
    if unknown:
        print(f"Predictors inconnus : {unknown}")
        return 1

    series_filter = [s.strip() for s in args.series.split(",") if s.strip()]

    weather = OpenMeteoClient()
    predictors = {name: PREDICTOR_FACTORIES[name](weather) for name in predictor_names}

    snapshots = sorted(p for p in MARKETS_DIR.glob("*.json") if not p.name.startswith("_"))
    if series_filter:
        snapshots = [p for p in snapshots
                     if any(p.name.startswith(s) for s in series_filter)]

    if not snapshots:
        print("Pas de snapshots dans data/markets/. Lance scripts/fetch_markets.py d'abord.")
        return 1

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    print(f"Forward-prediction snapshot @ {timestamp}")
    print(f"  predictors : {predictor_names}")
    print(f"  events     : {len(snapshots)}")
    print()

    records: list[dict] = []
    for path in snapshots:
        ev = Event.from_api(json.loads(path.read_text(encoding="utf-8")))
        for m in ev.markets:
            spec = parse_market(m)
            if spec is None:
                continue
            row: dict = {
                "ticker": m.ticker,
                "event_ticker": ev.event_ticker,
                "series_ticker": ev.series_ticker,
                "subtitle": m.subtitle,
                "target_date": spec.target_date.isoformat(),
                "variable": spec.variable,
                "location_key": spec.location_key,
                "lower": spec.lower,
                "upper": spec.upper,
                "yes_bid": m.yes_bid,
                "yes_ask": m.yes_ask,
                "yes_mid": m.implied_prob_yes,
                "snapshot_at": timestamp,
                "predictions": {},
            }
            for name, predictor in predictors.items():
                try:
                    pred = predictor.predict(spec)
                    row["predictions"][name] = {
                        "prob_yes": pred.prob_yes,
                        "method": pred.method,
                        "inputs": _slim_inputs(pred.inputs),
                    }
                except Exception as e:
                    row["predictions"][name] = {"error": f"{type(e).__name__}: {e}"}
            records.append(row)
            mid_str = f"{m.implied_prob_yes:.2f}" if m.implied_prob_yes is not None else "—"
            preds_str = "  ".join(
                f"{n}={row['predictions'][n].get('prob_yes', '—'):.2f}"
                if isinstance(row["predictions"][n].get("prob_yes"), (int, float))
                else f"{n}=err"
                for n in predictor_names
            )
            print(f"  {m.ticker:<35} mid={mid_str:>5} {preds_str}")

    out_dir = DATA_DIR / "predictions"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"forward_{timestamp}.json"
    out_path.write_text(
        json.dumps({
            "snapshot_at": timestamp,
            "predictors": predictor_names,
            "n_records": len(records),
            "records": records,
        }, indent=2, default=str),
        encoding="utf-8",
    )
    print(f"\n→ Prédictions stockées dans {out_path.relative_to(DATA_DIR.parent)}")
    print(f"  Une fois les markets résolus, lance score_forward.py pour les évaluer.")
    return 0


def _slim_inputs(inputs: dict) -> dict:
    """Retire les inputs trop verbeux pour ne pas bloater le JSON."""
    drop_keys = {"climato_years_used"}
    return {k: v for k, v in inputs.items() if k not in drop_keys}


if __name__ == "__main__":
    sys.exit(main())
