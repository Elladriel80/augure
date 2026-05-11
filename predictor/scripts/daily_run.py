"""Routine quotidienne autonome : fetch markets → forward predict → score résolus.

Lancée chaque jour à heure fixe par la skill `schedule`. Idempotente :
- Si un step échoue, les autres tournent quand même.
- Toutes les sorties sont stockées disque (pas de perte si le run plante).
- Trace stdout structurée pour debug a posteriori.

Usage manuel :
    python scripts/daily_run.py

Exit code : 0 si tous les steps OK, 1 si au moins un step a planté
(mais on continue quand même les suivants).
"""
from __future__ import annotations

import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def run_step(name: str, cmd: list[str]) -> bool:
    print(f"\n{'=' * 70}")
    print(f"[STEP] {name}")
    print(f"  cmd : {' '.join(cmd)}")
    print(f"  at  : {datetime.now(timezone.utc).isoformat()}")
    print("-" * 70)
    try:
        result = subprocess.run(
            cmd, cwd=str(ROOT), check=False,
            timeout=60 * 30,  # 30 minutes max par step
        )
        ok = result.returncode == 0
        print(f"  → exit code: {result.returncode} ({'OK' if ok else 'FAIL'})")
        return ok
    except subprocess.TimeoutExpired:
        print(f"  → TIMEOUT après 30 min")
        return False
    except Exception:
        print(f"  → EXCEPTION:")
        traceback.print_exc()
        return False


def main() -> int:
    started_at = datetime.now(timezone.utc)
    print(f"daily_run start @ {started_at.isoformat()}")
    print(f"working dir : {ROOT}")

    py = sys.executable

    steps = [
        # `--all-weather` est requis : sans ce flag, fetch_markets écrit
        # seulement un summary et ne refresh PAS les snapshots des markets,
        # donc forward_predict bosse sur des données 2-3 jours obsolètes.
        # Cf. bug détecté le 2026-05-10 (predictions sur target_date passé).
        ("fetch_markets",   [py, str(SCRIPTS / "fetch_markets.py"), "--all-weather"]),
        ("forward_predict", [py, str(SCRIPTS / "forward_predict.py")]),
        # Le score essaie de récupérer les résolutions Kalshi pour les markets
        # capturés les jours précédents. C'est ce qui ferme la boucle.
        ("score_forward",   [py, str(SCRIPTS / "score_forward.py")]),
    ]

    results: dict[str, bool] = {}
    for name, cmd in steps:
        results[name] = run_step(name, cmd)

    print(f"\n{'=' * 70}")
    print("SUMMARY")
    for name, ok in results.items():
        print(f"  {name:<20} {'OK' if ok else 'FAIL'}")
    duration = (datetime.now(timezone.utc) - started_at).total_seconds()
    print(f"  total duration   : {duration:.1f}s")

    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
