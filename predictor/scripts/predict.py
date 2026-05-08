"""Run un predictor sur les marchés Kalshi snapshotés.

Usage:
    python scripts/predict.py [--predictor climatology|forecast_blend]
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

# Force UTF-8 sur stdout (Windows console = cp1252 par défaut)
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import MARKETS_DIR
from src.kalshi.models import Event
from src.predictors import ClimatologyPredictor, ForecastBlendPredictor, parse_market


PREDICTORS = {
    "climatology": ClimatologyPredictor,
    "forecast_blend": ForecastBlendPredictor,
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictor", choices=PREDICTORS.keys(), default="forecast_blend")
    parser.add_argument("--years-back", type=int, default=15)
    parser.add_argument("--out", type=str, default=None,
                        help="Fichier JSON de sortie (par défaut: data/predictions/<predictor>_<timestamp>.json)")
    args = parser.parse_args()

    predictor_cls = PREDICTORS[args.predictor]
    predictor = predictor_cls(years_back=args.years_back)

    snapshot_files = sorted(MARKETS_DIR.glob("KX*.json"))
    if not snapshot_files:
        print("!! Aucun snapshot dans data/markets/. Lance d'abord scripts/fetch_markets.py --all-weather")
        return 1

    print(f">> Predictor: {args.predictor}")
    print(f">> Snapshots à traiter: {len(snapshot_files)}")

    results = []
    skipped = []

    for snap_path in snapshot_files:
        raw = json.loads(snap_path.read_text(encoding="utf-8"))
        event = Event.from_api(raw)
        print(f"\n>> {event.event_ticker}: {event.title}")
        for market in event.markets:
            spec = parse_market(market)
            if spec is None:
                skipped.append({"ticker": market.ticker, "reason": "not parseable"})
                print(f"   [skip] {market.ticker} — non parsable ({market.subtitle})")
                continue

            try:
                pred = predictor.predict(spec)
            except Exception as e:
                skipped.append({"ticker": market.ticker, "reason": f"predict error: {e}"})
                print(f"   [err] {market.ticker} — {e}")
                continue

            implied = market.implied_prob_yes
            implied_str = f"{implied:.3f}" if implied is not None else "  -  "
            edge = (pred.prob_yes - implied) if implied is not None else None
            edge_str = f"{edge:+.3f}" if edge is not None else "  -  "

            print(f"   [{spec.describe():<60}] "
                  f"P_model={pred.prob_yes:.3f}  P_market={implied_str}  edge={edge_str}")

            results.append({
                "market_ticker": market.ticker,
                "event_ticker": event.event_ticker,
                "spec": spec.describe(),
                "subtitle": market.subtitle,
                "prob_model_raw": pred.prob_yes,
                "prob_market_implied": implied,
                "yes_bid": market.yes_bid,
                "yes_ask": market.yes_ask,
                "method": pred.method,
                "confidence": pred.confidence,
                "inputs": _json_safe(pred.inputs),
            })

    # Normalisation par event : pour chaque event mutuellement exclusif,
    # les probas doivent sommer à 1. On renormalise.
    by_event: dict[str, list[dict]] = {}
    for r in results:
        by_event.setdefault(r["event_ticker"], []).append(r)
    for ev_ticker, rs in by_event.items():
        s = sum(r["prob_model_raw"] for r in rs)
        if s > 0:
            for r in rs:
                r["prob_model"] = r["prob_model_raw"] / s
        else:
            for r in rs:
                r["prob_model"] = 1.0 / len(rs)
        # Recompute edge sur la proba normalisée
        for r in rs:
            if r["prob_market_implied"] is not None:
                r["edge"] = r["prob_model"] - r["prob_market_implied"]
            else:
                r["edge"] = None

    print("\n>> Probabilités normalisées par event:")
    for ev_ticker, rs in by_event.items():
        print(f"   {ev_ticker} (sum_raw={sum(r['prob_model_raw'] for r in rs):.3f})")
        for r in rs:
            implied = r['prob_market_implied']
            i_str = f"{implied:.3f}" if implied is not None else "  -  "
            edge = r.get('edge')
            e_str = f"{edge:+.3f}" if edge is not None else "  -  "
            print(f"     {r['subtitle']:<22} P_model={r['prob_model']:.3f}  P_market={i_str}  edge={e_str}")

    out_dir = ROOT / "data" / "predictions"
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.out:
        out_path = Path(args.out)
    else:
        from datetime import datetime, timezone
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_path = out_dir / f"{args.predictor}_{ts}.json"

    out_path.write_text(json.dumps({
        "predictor": args.predictor,
        "n_results": len(results),
        "n_skipped": len(skipped),
        "results": results,
        "skipped": skipped,
    }, indent=2), encoding="utf-8")

    print(f"\n>> {len(results)} prédictions, {len(skipped)} skippées")
    print(f">> Sauvé: {out_path}")
    return 0


def _json_safe(d: dict) -> dict:
    """Convertit les sets/dates en types JSON-compatibles."""
    out = {}
    for k, v in d.items():
        if isinstance(v, set):
            out[k] = sorted(v)
        elif hasattr(v, "isoformat"):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


if __name__ == "__main__":
    sys.exit(main())
