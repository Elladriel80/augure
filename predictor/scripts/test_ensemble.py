"""Test live de l'EnsemblePredictor sur le panel Kalshi du jour.

Utilisation : python scripts/test_ensemble.py

Pour chaque event Kalshi température disponible dans data/markets/, on calcule
P(YES) avec :
- climato seule (baseline existante)
- forecast_blend (existing predictor, modèle déterministe Open-Meteo)
- ensemble multi-modèles (Phase A.1)

Et on affiche côte à côte. C'est un check de plausibilité, pas un backtest.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import MARKETS_DIR  # noqa: E402
from src.kalshi.models import Event  # noqa: E402
from src.predictors.parsers import parse_market  # noqa: E402
from src.predictors.climatology import ClimatologyPredictor  # noqa: E402
from src.predictors.forecast_blend import ForecastBlendPredictor  # noqa: E402
from src.predictors.ensemble import EnsemblePredictor  # noqa: E402
from src.weather import OpenMeteoClient  # noqa: E402


def main() -> int:
    snapshots = sorted(p for p in MARKETS_DIR.glob("KXHIGH*-26MAY08.json"))
    if not snapshots:
        print("Pas de snapshots HIGH temp pour aujourd'hui (26MAY08).")
        return 1

    weather = OpenMeteoClient()
    climato = ClimatologyPredictor(weather)
    blend = ForecastBlendPredictor(weather)
    ensemble = EnsemblePredictor(weather)

    print(f"{'ticker':<35} {'subtitle':<22} {'mkt mid':>8} {'climato':>8} {'blend':>8} {'ensemble':>9} {'σ_inter':>8} {'µ':>6}")
    print("-" * 120)

    n_done = 0
    for path in snapshots[:4]:  # limite à 4 events pour ne pas saturer Open-Meteo
        ev = Event.from_api(json.loads(path.read_text(encoding="utf-8")))
        for m in ev.markets:
            spec = parse_market(m)
            if spec is None:
                continue
            try:
                p_clim = climato.predict(spec).prob_yes
                p_blend = blend.predict(spec).prob_yes
                pred_ens = ensemble.predict(spec)
                p_ens = pred_ens.prob_yes
                sigma = pred_ens.inputs.get("sigma_inter_models", 0.0) or 0.0
                mu = pred_ens.inputs.get("mu")
            except Exception as e:
                print(f"{m.ticker:<35} ERREUR {type(e).__name__}: {e}")
                continue

            mid = m.implied_prob_yes
            print(f"{m.ticker:<35} {spec.raw_subtitle:<22} "
                  f"{_fmt(mid, '.2f'):>8} {p_clim:>8.2f} {p_blend:>8.2f} "
                  f"{p_ens:>9.2f} {sigma:>8.2f} {_fmt(mu, '.1f'):>6}")
            n_done += 1

    print(f"\n{n_done} markets prédits.")
    return 0


def _fmt(x, fmt: str) -> str:
    if x is None:
        return "—"
    return f"{x:{fmt}}"


if __name__ == "__main__":
    sys.exit(main())
