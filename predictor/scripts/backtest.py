"""Backtest : run le predictor sur des events Kalshi DÉJÀ RÉSOLUS et mesure l'accuracy.

Pour chaque event settled :
- pour chaque market (bin), prédit P(OUI) avec UNIQUEMENT des données antérieures
  à la date de résolution (pas de leakage)
- compare à l'outcome réel (yes/no) du market
- agrège accuracy, Brier score, log loss

Usage:
    python scripts/backtest.py [--series KXHIGHAUS,KXLOWTAUS] [--limit 30]
"""
from __future__ import annotations
import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from src.kalshi import KalshiClient
from src.kalshi.models import Event
from src.predictors import (
    ClimatologyPredictor,
    ForecastBlendPredictor,
    parse_market,
)
from src.predictors.ensemble import EnsemblePredictor
from src.predictors.parsers import SERIES_MAP
from src.simulation.scoring import aggregate_metrics, event_top1_accuracy


DEFAULT_SERIES = list(SERIES_MAP.keys())[:6]  # 6 séries par défaut pour ne pas spammer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--series", type=str, default=",".join(DEFAULT_SERIES),
        help="Tickers de séries à backtester (séparés par virgules)",
    )
    parser.add_argument("--predictor", choices=["climatology", "forecast_blend", "ensemble"],
                        default="climatology",
                        help="Pour le backtest, climatology est cohérent (forecast_blend "
                             "et ensemble appellent un forecast actuel, donc inadaptés "
                             "pour des events anciens — utiles pour forward-test seulement).")
    parser.add_argument("--limit", type=int, default=20,
                        help="Limite d'events settled par série")
    parser.add_argument("--years-back", type=int, default=15)
    args = parser.parse_args()

    series_list = [s.strip() for s in args.series.split(",") if s.strip()]
    print(f">> Séries: {series_list}")
    print(f">> Predictor: {args.predictor} | years_back: {args.years_back}")

    if args.predictor == "climatology":
        predictor = ClimatologyPredictor(years_back=args.years_back)
    elif args.predictor == "forecast_blend":
        predictor = ForecastBlendPredictor(years_back=args.years_back)
    else:  # ensemble
        predictor = EnsemblePredictor(years_back=args.years_back)

    client = KalshiClient()
    all_records = []      # liste de dicts pour aggregate_metrics
    event_groups = []     # liste de listes pour top-1 accuracy
    per_series = defaultdict(list)

    for series_ticker in series_list:
        print(f"\n>> Pulling settled events for {series_ticker}...")
        try:
            events = list(client.list_events(
                series_ticker=series_ticker, status="settled", with_nested_markets=True,
            ))
        except Exception as e:
            print(f"   !! erreur: {e}")
            continue
        events = events[: args.limit]
        print(f"   {len(events)} events à backtester")

        for ev in events:
            event_records = []
            for market in ev.markets:
                if market.result not in ("yes", "no"):
                    continue
                spec = parse_market(market)
                if spec is None:
                    continue
                try:
                    pred = predictor.predict(spec)
                except Exception as e:
                    print(f"   [err] {market.ticker} — {e}")
                    continue
                outcome = 1 if market.result == "yes" else 0
                rec = {
                    "ticker": market.ticker,
                    "event_ticker": ev.event_ticker,
                    "spec": spec.describe(),
                    "subtitle": market.subtitle,
                    "prob_yes": pred.prob_yes,
                    "outcome": outcome,
                    "method": pred.method,
                    "series": series_ticker,
                }
                event_records.append(rec)

            # Normaliser par event mutuellement exclusif
            if event_records and ev.mutually_exclusive:
                s = sum(r["prob_yes"] for r in event_records)
                if s > 0:
                    for r in event_records:
                        r["prob_yes"] = r["prob_yes"] / s

            if event_records:
                all_records.extend(event_records)
                event_groups.append(event_records)
                per_series[series_ticker].extend(event_records)
                # Quick log
                top = max(event_records, key=lambda r: r["prob_yes"])
                winner = next((r for r in event_records if r["outcome"] == 1), None)
                hit = "OK" if (winner and top["ticker"] == winner["ticker"]) else "miss"
                wstr = winner["subtitle"] if winner else "?"
                print(f"   {ev.event_ticker:<28} top1={top['subtitle']:<22} (P={top['prob_yes']:.2f}) "
                      f"actual={wstr:<22} -> {hit}")

    # Agrégats
    print("\n" + "=" * 70)
    print("MÉTRIQUES GLOBALES")
    print("=" * 70)

    agg = aggregate_metrics(all_records)
    top1 = event_top1_accuracy(event_groups)
    print(f"  Markets prédits     : {agg['n']}")
    print(f"  Events backtest     : {top1['n_events']}")
    print(f"  Base rate (P(YES))  : {agg['base_rate']:.3f}")
    print(f"  Top-1 accuracy      : {top1['top1_accuracy']:.3f}  ({top1['top1_correct']}/{top1['n_events']})")
    print(f"  Brier score         : {agg['brier_score']:.4f}")
    print(f"  Brier baseline const: {agg['brier_baseline_constant']:.4f}")
    print(f"  Brier skill score   : {agg['brier_skill_score']:+.4f}  (>0 = mieux que constante)")
    print(f"  Log loss            : {agg['log_loss']:.4f}")

    print("\nPar série :")
    print(f"  {'Series':<14} {'N':>4} {'Brier':>8} {'BSS':>8} {'LogLoss':>8}")
    for s, recs in per_series.items():
        a = aggregate_metrics(recs)
        print(f"  {s:<14} {a['n']:>4} {a['brier_score']:>8.4f} {a['brier_skill_score']:>+8.3f} {a['log_loss']:>8.4f}")

    # Écrit rapport
    out_dir = ROOT / "data" / "backtests"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = out_dir / f"backtest_{args.predictor}_{ts}.json"
    report_path.write_text(json.dumps({
        "predictor": args.predictor,
        "years_back": args.years_back,
        "series": series_list,
        "n_records": len(all_records),
        "global": agg,
        "top1": top1,
        "per_series": {s: aggregate_metrics(r) for s, r in per_series.items()},
        "records": all_records,
    }, indent=2), encoding="utf-8")
    print(f"\n>> Rapport: {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
