"""Simule des paris paper-trading à partir des prédictions.

Pipeline:
1. Charge les markets snapshotés (avec leurs prix actuels)
2. Run le predictor sur chacun
3. Pour chaque (market, prediction), décide YES/NO/SKIP selon l'edge
4. Si edge > seuil, log un PaperBet dans le ledger CSV

Usage:
    python scripts/simulate.py [--predictor climatology|forecast_blend] [--min-edge 0.05]
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
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from src.config import MARKETS_DIR, SIMULATION
from src.kalshi.models import Event
from src.predictors import ClimatologyPredictor, ForecastBlendPredictor, parse_market
from src.simulation import Ledger, PaperBet
from src.simulation.ledger import make_bet_id
from src.simulation.sizing import kelly_fractional_size


PREDICTORS = {
    "climatology": ClimatologyPredictor,
    "forecast_blend": ForecastBlendPredictor,
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictor", choices=PREDICTORS.keys(), default="forecast_blend")
    parser.add_argument("--min-edge", type=float, default=SIMULATION["min_edge_to_bet"])
    parser.add_argument("--bankroll", type=float, default=SIMULATION["starting_bankroll"])
    parser.add_argument("--kelly-fraction", type=float, default=SIMULATION["kelly_fraction"])
    parser.add_argument("--years-back", type=int, default=15)
    parser.add_argument("--dry-run", action="store_true",
                        help="Affiche les paris sans les écrire au ledger")
    args = parser.parse_args()

    predictor = PREDICTORS[args.predictor](years_back=args.years_back)
    ledger = Ledger()

    snapshot_files = sorted(MARKETS_DIR.glob("KX*.json"))
    if not snapshot_files:
        print("!! Aucun snapshot dans data/markets/.")
        return 1

    bets_placed = 0
    bets_skipped = 0
    now_iso = datetime.now(timezone.utc).isoformat()

    print(f">> Predictor: {args.predictor} | min_edge: {args.min_edge} | bankroll: ${args.bankroll}")
    print(f">> Snapshots à traiter: {len(snapshot_files)}\n")

    # Group predictions by event for normalization
    for snap_path in snapshot_files:
        raw = json.loads(snap_path.read_text(encoding="utf-8"))
        event = Event.from_api(raw)

        # Predire chaque market parsable
        event_predictions = []
        for market in event.markets:
            spec = parse_market(market)
            if spec is None:
                continue
            try:
                pred = predictor.predict(spec)
            except Exception as e:
                print(f"   [err] {market.ticker} — {e}")
                continue
            event_predictions.append((market, spec, pred))

        if not event_predictions:
            continue

        # Normalisation par event (si mutuellement exclusifs)
        if event.mutually_exclusive:
            total = sum(p.prob_yes for _, _, p in event_predictions)
            if total > 0:
                for _, _, p in event_predictions:
                    p.prob_yes = p.prob_yes / total

        # Décision pour chaque market
        print(f">> {event.event_ticker}: {event.title}")
        for market, spec, pred in event_predictions:
            implied = market.implied_prob_yes
            if implied is None:
                bets_skipped += 1
                print(f"   [skip] {market.ticker:<35} {spec.raw_subtitle:<22} (pas de cote — illiquide)")
                continue

            edge = pred.prob_yes - implied
            abs_edge = abs(edge)
            if abs_edge < args.min_edge:
                bets_skipped += 1
                print(f"   [skip] {market.ticker:<35} {spec.raw_subtitle:<22} "
                      f"P_model={pred.prob_yes:.3f} P_mkt={implied:.3f} edge={edge:+.3f} (< seuil)")
                continue

            # Direction. yes_bid/yes_ask sont déjà en dollars [0.0, 1.0],
            # donc le mid = (bid+ask)/2 (pas /200 — c'était le legacy cents).
            side = "YES" if edge > 0 else "NO"
            entry_price = (market.yes_bid + market.yes_ask) / 2.0
            stake = kelly_fractional_size(
                prob_yes=pred.prob_yes,
                market_yes_price=entry_price,
                side=side,
                kelly_fraction=args.kelly_fraction,
                bankroll=args.bankroll,
            )
            if stake <= 0:
                bets_skipped += 1
                continue

            bet = PaperBet(
                bet_id=make_bet_id(),
                placed_at_utc=now_iso,
                market_ticker=market.ticker,
                event_ticker=event.event_ticker,
                target_date=spec.target_date.isoformat(),
                side=side,
                stake_usd=stake,
                entry_price=entry_price,
                prob_model=pred.prob_yes,
                prob_market_implied=implied,
                edge=edge,
                method=pred.method,
                spec=spec.describe(),
            )

            if args.dry_run:
                print(f"   [DRY ] {market.ticker:<35} {spec.raw_subtitle:<22} "
                      f"side={side} stake=${stake:.2f} edge={edge:+.3f}")
            else:
                ledger.append(bet)
                print(f"   [BET ] {market.ticker:<35} {spec.raw_subtitle:<22} "
                      f"side={side} stake=${stake:.2f} edge={edge:+.3f}")
            bets_placed += 1

    print(f"\n>> Total: {bets_placed} paris placés, {bets_skipped} skippés")
    print(f">> Ledger: {ledger.path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
