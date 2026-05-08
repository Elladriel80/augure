"""Audit des règles de résolution sur tous les snapshots de markets disponibles.

Sortie : un rapport texte + un JSON détaillé pour chaque market avec
- la station NWS identifiée (CLI code, ICAO, lat/lon),
- la règle de résolution déterministe (strike_type, floor, cap),
- les notes (Trace=YES, station inconnue, etc.),
- des cas-limites d'arrondi pour vérifier visuellement.

Utilisation :
    python scripts/audit_resolution.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# Ajout du répertoire parent pour imports src.*
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import MARKETS_DIR, DATA_DIR  # noqa: E402
from src.kalshi.models import Event           # noqa: E402
from src.kalshi.resolution import (            # noqa: E402
    extract_resolution_rule,
    apply_nws_rounding,
    would_resolve_yes,
)


def main() -> int:
    snapshots = sorted(MARKETS_DIR.glob("*.json"))
    snapshots = [p for p in snapshots if not p.name.startswith("_")]

    if not snapshots:
        print(f"Aucun snapshot dans {MARKETS_DIR}")
        return 1

    print(f"Audit de {len(snapshots)} events Kalshi (résolution NWS)\n")
    print("=" * 88)

    rows: list[dict] = []
    series_count: Counter[str] = Counter()
    station_count: Counter[str] = Counter()
    unknown_station_examples: list[str] = []
    knife_edge_examples: list[dict] = []

    for path in snapshots:
        raw = json.loads(path.read_text(encoding="utf-8"))
        ev = Event.from_api(raw)
        series_count[ev.series_ticker] += 1
        for m in ev.markets:
            rule = extract_resolution_rule(m)
            if rule is None:
                rows.append({
                    "ticker": m.ticker,
                    "status": "UNPARSEABLE",
                    "rules_primary": (m.rules_primary or "")[:120],
                })
                continue

            station_label = rule.station.cli_code if rule.station else "UNKNOWN"
            station_count[station_label] += 1

            if rule.station is None:
                unknown_station_examples.append(
                    f"{m.ticker} -> {(m.rules_primary or '')[:140]}"
                )

            row = {
                "ticker": m.ticker,
                "variable": rule.variable,
                "strike_type": rule.strike_type,
                "floor": rule.floor_strike,
                "cap": rule.cap_strike,
                "station": station_label,
                "icao": rule.station.icao if rule.station else None,
                "lat": rule.station.lat if rule.station else None,
                "lon": rule.station.lon if rule.station else None,
                "rounding": rule.rounding,
                "trace_is_yes": rule.trace_is_yes,
                "notes": rule.notes,
                "describe": rule.describe(),
            }
            rows.append(row)

            # cas-limite : on simule une obs juste au seuil pour vérifier
            # que l'arrondi bascule la résolution comme prévu.
            if rule.variable in ("temp_max", "temp_min") and rule.cap_strike is not None:
                # obs = cap - 0.4 → arrondi à cap-0 = cap (banker's rounding) ?
                # Pour rule "less" cap=76, obs=75.6 → arrondi=76 → 76 < 76 = FALSE → NO
                # Trader naif voyant prevision 75.6 pense YES, mais c'est NO.
                obs = rule.cap_strike - 0.4
                yes = would_resolve_yes(rule, obs)
                rounded = apply_nws_rounding(obs, rule.rounding)
                knife_edge_examples.append({
                    "ticker": m.ticker,
                    "obs": obs,
                    "rounded": rounded,
                    "verdict_yes": yes,
                    "rule": rule.describe(),
                })

    # -- Rapport texte --

    print("\nSéries observées :")
    for s, n in series_count.most_common():
        print(f"  {s:<20} {n:>3} events")

    print("\nStations identifiées :")
    for s, n in station_count.most_common():
        print(f"  {s:<10} {n:>4} markets")

    if unknown_station_examples:
        print(f"\n{len(unknown_station_examples)} markets sans station identifiée. Exemples :")
        for ex in unknown_station_examples[:5]:
            print(f"  - {ex}")

    print("\nExemples de knife-edge (obs juste sous le cap, après arrondi NWS) :")
    for ex in knife_edge_examples[:8]:
        print(f"  {ex['ticker']:<35} obs={ex['obs']:.1f} → rounded={ex['rounded']:.0f} → "
              f"{'YES' if ex['verdict_yes'] else 'NO'}  ({ex['rule']})")

    # -- Sortie JSON détaillée --

    out_dir = DATA_DIR / "audits"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = out_dir / f"resolution_audit_{stamp}.json"
    out_path.write_text(
        json.dumps({
            "generated_at": stamp,
            "n_events": len(snapshots),
            "n_markets": len(rows),
            "series_count": dict(series_count),
            "station_count": dict(station_count),
            "rows": rows,
        }, indent=2, default=str),
        encoding="utf-8",
    )
    print(f"\n→ Audit complet écrit dans {out_path.relative_to(DATA_DIR.parent)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
