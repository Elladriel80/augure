"""Score les prédictions forward stockées contre les résolutions Kalshi.

Workflow :
1. ``forward_predict.py`` capture P(YES) chaque jour pour chaque market actif
   (climato, forecast_blend, ensemble) et stocke dans data/predictions/forward_*.json.
2. Quand les events sont résolus, ce script compare les prédictions stockées
   au vrai résultat (champ ``result`` du market sur Kalshi) et calcule
   Brier / log loss / accuracy par predictor.

Usage :
    python scripts/score_forward.py
    python scripts/score_forward.py --predictor ensemble  # ne montre qu'un predictor

Sortie : table comparée stdout + JSON détaillé dans data/scores/.
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
except Exception:
    pass

from src.config import DATA_DIR  # noqa: E402
from src.kalshi.client import KalshiClient  # noqa: E402
from src.simulation.scoring import (  # noqa: E402
    aggregate_metrics,
    event_top1_accuracy,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictor", default=None,
                        help="Filtre sur un predictor (climatology|forecast_blend|ensemble)")
    parser.add_argument("--no-fetch", action="store_true",
                        help="Ne pas requêter Kalshi pour les résolutions ; ne scorer que "
                             "les markets dont le résultat est déjà dans les fichiers")
    args = parser.parse_args()

    pred_dir = DATA_DIR / "predictions"
    files = sorted(pred_dir.glob("forward_*.json"))
    if not files:
        print(f"Aucune prédiction forward dans {pred_dir}.")
        print(f"Lance d'abord : python scripts/forward_predict.py")
        return 1

    # Charge toutes les captures de prédiction
    all_records: list[dict] = []
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        for r in data.get("records", []):
            r["_capture_at"] = data.get("snapshot_at")
            all_records.append(r)

    # Pour chaque market unique (par ticker + capture_at on garde la PREMIÈRE
    # prédiction = celle faite le plus tôt avant résolution. On peut affiner.)
    by_ticker_first: dict[str, dict] = {}
    for r in sorted(all_records, key=lambda x: x.get("_capture_at", "")):
        if r["ticker"] not in by_ticker_first:
            by_ticker_first[r["ticker"]] = r
    unique_records = list(by_ticker_first.values())
    print(f"Captures forward : {len(files)} fichier(s) → {len(unique_records)} markets uniques")

    # Récupère les résolutions depuis Kalshi (sauf si --no-fetch)
    resolutions: dict[str, str] = {}
    if not args.no_fetch:
        client = KalshiClient()
        # On groupe par event_ticker pour minimiser les appels
        events = sorted({r["event_ticker"] for r in unique_records})
        print(f"Récupération des résolutions Kalshi pour {len(events)} events...")
        for ev_ticker in events:
            try:
                ev = client.get_event(ev_ticker, with_nested_markets=True)
                for m in ev.markets:
                    if m.result in ("yes", "no"):
                        resolutions[m.ticker] = m.result
            except Exception as e:
                print(f"  [warn] {ev_ticker} : {type(e).__name__}: {e}")
                continue

    n_resolved = sum(1 for r in unique_records if r["ticker"] in resolutions)
    print(f"Markets résolus disponibles : {n_resolved}/{len(unique_records)}")
    if n_resolved == 0:
        print("\nAucun market résolu pour l'instant. Reviens dans 1-7 jours après "
              "la close de tes captures forward.")
        return 0

    # Détermine les predictors présents
    sample = next(iter(unique_records))
    predictors_in_data = list(sample.get("predictions", {}).keys())
    if args.predictor:
        if args.predictor not in predictors_in_data:
            print(f"Predictor {args.predictor} absent. Disponibles : {predictors_in_data}")
            return 1
        predictors_in_data = [args.predictor]

    # Pour chaque predictor, agrège les métriques
    print("\n" + "=" * 88)
    print(f"{'predictor':<18} {'n':>4} {'base':>6} {'acc@0.5':>8} {'Brier':>8} "
          f"{'BSS':>8} {'LogLoss':>8} {'top1':>6}")
    print("-" * 88)

    summary = {}
    for predictor in predictors_in_data:
        flat: list[dict] = []
        groups: dict[str, list[dict]] = defaultdict(list)
        for r in unique_records:
            if r["ticker"] not in resolutions:
                continue
            pred = r.get("predictions", {}).get(predictor, {})
            p = pred.get("prob_yes")
            if p is None:
                continue
            outcome = 1 if resolutions[r["ticker"]] == "yes" else 0
            row = {
                "ticker": r["ticker"],
                "event_ticker": r["event_ticker"],
                "prob_yes": float(p),
                "outcome": outcome,
                "yes_mid": r.get("yes_mid"),
            }
            flat.append(row)
            groups[r["event_ticker"]].append(row)

        if not flat:
            print(f"{predictor:<18} (aucune prédiction utilisable)")
            continue

        agg = aggregate_metrics(flat)
        top1 = event_top1_accuracy(list(groups.values()))
        print(f"{predictor:<18} {agg['n']:>4} {agg['base_rate']:>6.2f} "
              f"{agg['accuracy_at_0.5']:>8.2f} {agg['brier_score']:>8.4f} "
              f"{agg['brier_skill_score']:>+8.3f} {agg['log_loss']:>8.4f} "
              f"{top1['top1_accuracy']:>6.2f}")
        summary[predictor] = {**agg, "top1": top1}

    # Comparaison aux mids Kalshi (si disponibles) — c'est la vraie référence.
    # Note : on utilise la 1ère capture AVEC un yes_mid non nul, pas la 1ère
    # capture tout court. Les marchés Kalshi peuvent ne pas être quotés tôt
    # le matin (yes_mid=null sur les premières captures) ; les utiliser comme
    # référence donnerait market_flat vide et on perdrait le bench critique.
    print()
    market_flat = []
    by_ticker_with_quote: dict[str, dict] = {}
    for r in sorted(all_records, key=lambda x: x.get("_capture_at", "")):
        if r["ticker"] not in resolutions:
            continue
        if r.get("yes_mid") is None:
            continue
        if r["ticker"] not in by_ticker_with_quote:
            by_ticker_with_quote[r["ticker"]] = r
    for r in by_ticker_with_quote.values():
        market_flat.append({
            "ticker": r["ticker"],
            "prob_yes": float(r["yes_mid"]),
            "outcome": 1 if resolutions[r["ticker"]] == "yes" else 0,
        })
    if market_flat:
        agg = aggregate_metrics(market_flat)
        print(f"{'kalshi_mid':<18} {agg['n']:>4} {agg['base_rate']:>6.2f} "
              f"{agg['accuracy_at_0.5']:>8.2f} {agg['brier_score']:>8.4f} "
              f"{agg['brier_skill_score']:>+8.3f} {agg['log_loss']:>8.4f}")
        summary["kalshi_mid"] = agg

    print("=" * 88)
    print("\nLecture :")
    print("  - BSS (Brier skill score) > 0  → bat la baseline 'predict base rate'")
    print("  - Brier score plus bas que kalshi_mid → tu prédis mieux que le marché")
    print("  - top1 = part des events où le bin de plus haute proba est le bin gagnant")

    # JSON détaillé
    out_dir = DATA_DIR / "scores"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = out_dir / f"score_forward_{stamp}.json"
    out_path.write_text(json.dumps({
        "generated_at": stamp,
        "n_capture_files": len(files),
        "n_unique_markets": len(unique_records),
        "n_resolved": n_resolved,
        "summary": summary,
    }, indent=2, default=str), encoding="utf-8")
    print(f"\n→ Détail dans {out_path.relative_to(DATA_DIR.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
