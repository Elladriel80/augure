"""Récupère la prévision Open-Meteo pour une ville donnée.

Usage:
    python scripts/fetch_forecast.py --city AUSTIN
    python scripts/fetch_forecast.py --city NYC --days 7
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from src.weather import OpenMeteoClient, CITIES


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--city", required=True, help=f"Une de: {', '.join(CITIES.keys())}")
    parser.add_argument("--days", type=int, default=14)
    args = parser.parse_args()

    city_key = args.city.upper()
    if city_key not in CITIES:
        print(f"!! Ville inconnue. Choix: {list(CITIES.keys())}")
        return 1

    city = CITIES[city_key]
    client = OpenMeteoClient()

    print(f">> Forecast {city['label']} ({city['lat']}, {city['lon']}) — {args.days} jours")
    data = client.forecast(city["lat"], city["lon"], days=args.days, timezone=city["tz"])

    daily = data.get("daily", {})
    times = daily.get("time", [])
    tmax = daily.get("temperature_2m_max", [])
    tmin = daily.get("temperature_2m_min", [])
    precip = daily.get("precipitation_sum", [])
    snow = daily.get("snowfall_sum", [])
    pop = daily.get("precipitation_probability_max", [])

    print(f"\n{'Date':<12} {'Tmax °F':>8} {'Tmin °F':>8} {'Precip mm':>10} {'Snow cm':>8} {'POP %':>6}")
    print("-" * 60)
    for i, d in enumerate(times):
        print(f"{d:<12} {tmax[i]:>8.1f} {tmin[i]:>8.1f} "
              f"{(precip[i] or 0):>10.1f} {(snow[i] or 0):>8.1f} "
              f"{(pop[i] if i < len(pop) and pop[i] is not None else 0):>6}")

    # Cache la réponse
    cache_path = client.cache_path("forecast", f"{city_key}_d{args.days}")
    cache_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"\n>> Cached: {cache_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
