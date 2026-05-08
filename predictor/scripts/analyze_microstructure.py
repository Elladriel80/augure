"""Analyse microstructure des snapshots Kalshi présents dans data/markets/.

Pour chaque event, calcule :
- vig (1 - somme YES mids)
- spread médian, extrêmes vs centraux
- distribution implicite (mean, std)
- concentration de l'open interest sur le bin modal
- masse de tail

Sortie : rapport texte stdout + JSON détaillé dans data/audits/.

Utilisation : python scripts/analyze_microstructure.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import MARKETS_DIR, DATA_DIR  # noqa: E402
from src.microstructure.distribution import extract_bins  # noqa: E402
from src.microstructure.biases import event_biases  # noqa: E402


def main() -> int:
    snapshots = sorted(p for p in MARKETS_DIR.glob("*.json") if not p.name.startswith("_"))
    if not snapshots:
        print(f"Aucun snapshot dans {MARKETS_DIR}")
        return 1

    print(f"Microstructure : {len(snapshots)} events Kalshi\n")
    print("=" * 96)
    print(f"{'event':<28} {'nbins':>5} {'sum_mid':>8} {'vig%':>6} "
          f"{'med_spd':>8} {'spd_skew':>9} {'impl_µ':>8} {'impl_σ':>7} {'modal_oi':>9}")
    print("-" * 96)

    results: list[dict] = []
    series_groups: dict[str, list] = {}
    for path in snapshots:
        raw = json.loads(path.read_text(encoding="utf-8"))
        ev_ticker = raw.get("event_ticker", path.stem)
        series_ticker = raw.get("series_ticker", "")
        bins = extract_bins(raw)
        bias = event_biases(ev_ticker, bins)
        results.append({
            "event_ticker": ev_ticker,
            "series_ticker": series_ticker,
            "mutually_exclusive": raw.get("mutually_exclusive", False),
            "n_bins": bias.n_bins,
            "n_quoted": bias.n_quoted,
            "sum_mid": bias.sum_mid,
            "vig_residual": bias.vig_residual,
            "median_spread": bias.median_spread,
            "extreme_spread_avg": bias.extreme_spread_avg,
            "central_spread_avg": bias.central_spread_avg,
            "spread_skew": bias.spread_skew,
            "implied_mean": bias.implied_mean,
            "implied_std": bias.implied_std,
            "modal_oi_share": bias.modal_oi_share,
            "tail_mass": bias.tail_mass,
            "notes": bias.notes,
        })
        series_groups.setdefault(series_ticker, []).append(bias)

        print(f"{ev_ticker:<28} {bias.n_bins:>5} "
              f"{_fmt(bias.sum_mid, '.3f'):>8} "
              f"{_fmt((bias.sum_mid - 1)*100 if bias.sum_mid else None, '.1f'):>6} "
              f"{_fmt(bias.median_spread, '.3f'):>8} "
              f"{_fmt(bias.spread_skew, '.3f'):>9} "
              f"{_fmt(bias.implied_mean, '.1f'):>8} "
              f"{_fmt(bias.implied_std, '.2f'):>7} "
              f"{_fmt(bias.modal_oi_share, '.2f'):>9}")

    print("=" * 96)

    # -- Synthèse aggregée --

    print("\nSynthèse aggregée (ne compte que les events mutuellement exclusifs avec ≥3 bins quotés) :")
    me_events = [r for r in results
                 if r["mutually_exclusive"] and (r["n_quoted"] or 0) >= 3]
    if me_events:
        sums = [r["sum_mid"] for r in me_events if r["sum_mid"] is not None]
        vigs = [r["vig_residual"] for r in me_events if r["vig_residual"] is not None]
        skews = [r["spread_skew"] for r in me_events if r["spread_skew"] is not None]
        spreads = [r["median_spread"] for r in me_events if r["median_spread"] is not None]
        modal_ois = [r["modal_oi_share"] for r in me_events if r["modal_oi_share"] is not None]
        if sums:
            print(f"  sum_yes_mid : médiane {median(sums):.3f}  moyenne {mean(sums):.3f}  "
                  f"min {min(sums):.3f}  max {max(sums):.3f}  (n={len(sums)})")
        if vigs:
            # vig_residual = 1 - sum_mid → si négatif, c'est de la vig payée
            avg_vig_pct = -mean(vigs) * 100
            print(f"  vig moyenne payée au mid : {avg_vig_pct:+.2f}% du capital engagé")
        if spreads:
            print(f"  spread médian : médiane des médians {median(spreads):.3f} $  "
                  f"max {max(spreads):.3f}")
        if skews:
            print(f"  skew spread (extrême - central) : médiane {median(skews):+.3f}  "
                  f"moyenne {mean(skews):+.3f}")
            n_pos = sum(1 for s in skews if s > 0.005)
            print(f"    → {n_pos}/{len(skews)} events ont des bins extrêmes plus larges que le centre")
        if modal_ois:
            print(f"  modal OI share : médiane {median(modal_ois):.2f}  "
                  f"max {max(modal_ois):.2f}")

    # -- Sortie JSON --

    out_dir = DATA_DIR / "audits"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = out_dir / f"microstructure_{stamp}.json"
    out_path.write_text(
        json.dumps({
            "generated_at": stamp,
            "n_events": len(results),
            "events": results,
        }, indent=2, default=str),
        encoding="utf-8",
    )
    print(f"\n→ Détail JSON écrit dans {out_path.relative_to(DATA_DIR.parent)}")
    return 0


def _fmt(x, fmt: str) -> str:
    if x is None:
        return "—"
    return f"{x:{fmt}}"


if __name__ == "__main__":
    sys.exit(main())
