"""Récupère les marchés météo Kalshi ouverts et les snapshote sur disque.

Usage:
    python scripts/fetch_markets.py [--all-weather] [--limit N]

Par défaut, n'affiche qu'un résumé. Avec --all-weather, snapshot tous les events ouverts.
"""
from __future__ import annotations
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import sys as _sys
    _sys.stdout.reconfigure(encoding="utf-8")
    _sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# Permet d'exécuter le script depuis n'importe où
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.kalshi import KalshiClient


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all-weather", action="store_true",
                        help="Snapshot tous les events ouverts des séries météo")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limite le nombre de séries traitées")
    parser.add_argument("--series", type=str, default=None,
                        help="Filtre sur un ticker de série spécifique")
    args = parser.parse_args()

    client = KalshiClient()

    print(">> Récupération des séries météo...")
    weather_series = client.list_weather_series()
    print(f"   {len(weather_series)} séries météo détectées.")

    if args.series:
        weather_series = [s for s in weather_series if s.ticker == args.series]
        if not weather_series:
            print(f"!! Série '{args.series}' introuvable.")
            return 1

    if args.limit:
        weather_series = weather_series[: args.limit]

    summary = []
    snapshot_count = 0

    for s in weather_series:
        print(f"\n>> {s.ticker} — {s.title}")
        try:
            events = list(client.list_events(
                series_ticker=s.ticker,
                status="open",
                with_nested_markets=True,
            ))
        except Exception as e:
            print(f"   !! erreur: {e}")
            continue

        if not events:
            print("   (aucun event ouvert)")
            continue

        for ev in events:
            n_active = sum(1 for m in ev.markets if m.status == "active")
            n_with_quotes = sum(1 for m in ev.markets
                                if m.yes_bid is not None and m.yes_ask is not None)
            print(f"   - {ev.event_ticker}: {ev.title}")
            print(f"     {len(ev.markets)} markets ({n_active} active, {n_with_quotes} quoted)")

            summary.append({
                "series_ticker": s.ticker,
                "series_title": s.title,
                "event_ticker": ev.event_ticker,
                "event_title": ev.title,
                "n_markets": len(ev.markets),
                "n_active": n_active,
                "n_quoted": n_with_quotes,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            })

            if args.all_weather:
                client.snapshot_event(ev)
                snapshot_count += 1

    # Sauvegarde du résumé
    summary_path = client.snapshot_dir / "_summary.json"
    summary_path.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "series_count": len(weather_series),
        "events": summary,
    }, indent=2), encoding="utf-8")

    print(f"\n>> Résumé sauvé: {summary_path}")
    if args.all_weather:
        print(f">> Events snapshotés: {snapshot_count}")
    print(f">> Total events ouverts: {len(summary)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
