"""Mesures de biais microstructure exploitables sur les events Kalshi météo.

Les fonctions ici prennent une liste de BinQuote ordonnée et calculent :
- vig_residual : 1 - somme des YES mid (positif = vig payée par le trader,
  négatif = arbitrage théorique au mid).
- spread_profile : spread bid/ask par bin, indexé par "tail position"
  (distance à la médiane de la distribution implicite).
- tail_underpricing : compare la masse de probabilité dans les bins extrêmes
  à un pivot (climato si fournie, sinon distribution gaussienne ajustée).
- modal_concentration : fraction d'OI sur le bin de plus haute proba implicite.

Tous les scores sont normalisés pour être agrégeables sur un grand panel
de markets — c'est ce qui permettra de mesurer si un biais est répliqué
sur un grand échantillon ou simplement du bruit.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from .distribution import BinQuote, implied_distribution, sum_yes_mid


@dataclass
class EventBiases:
    """Score de biais microstructure pour UN event."""
    event_ticker: str
    n_bins: int
    n_quoted: int
    sum_mid: Optional[float]
    vig_residual: Optional[float]              # 1 - sum_mid
    median_spread: Optional[float]
    extreme_spread_avg: Optional[float]        # spread moyen sur les 2 bins extrêmes
    central_spread_avg: Optional[float]        # spread moyen sur les bins centraux
    spread_skew: Optional[float]               # extreme - central
    implied_mean: Optional[float]
    implied_std: Optional[float]
    modal_oi_share: Optional[float]            # part de l'OI sur le bin modal
    tail_mass: Optional[float]                 # proba implicite cumulée des bins extrêmes (10% chacun côté)
    notes: list[str]


def _spread(b: BinQuote) -> Optional[float]:
    return b.spread


def event_biases(event_ticker: str, bins: list[BinQuote]) -> EventBiases:
    notes: list[str] = []

    n_bins = len(bins)
    quoted = [b for b in bins if b.yes_mid is not None]
    n_quoted = len(quoted)

    s_mid = sum_yes_mid(bins)
    vig = (1.0 - s_mid) if s_mid is not None else None

    spreads = [b.spread for b in quoted if b.spread is not None]
    median_spread = _median(spreads) if spreads else None

    # Extrêmes vs central : moyennage des 2 bins extrêmes (plus haut / plus bas)
    # vs des bins du milieu. Permet de voir si les tails sont moins liquides.
    extreme_spread = None
    central_spread = None
    if n_quoted >= 4:
        extreme_bins = [quoted[0], quoted[-1]]
        central_bins = quoted[1:-1]
        extreme_spreads = [b.spread for b in extreme_bins if b.spread is not None]
        central_spreads = [b.spread for b in central_bins if b.spread is not None]
        if extreme_spreads:
            extreme_spread = sum(extreme_spreads) / len(extreme_spreads)
        if central_spreads:
            central_spread = sum(central_spreads) / len(central_spreads)
    spread_skew = (
        (extreme_spread - central_spread)
        if (extreme_spread is not None and central_spread is not None)
        else None
    )

    # Distribution implicite normalisée (somme = 1)
    dist = implied_distribution(bins)

    implied_mean = None
    implied_std = None
    if dist:
        pts = [(b.midpoint, p) for b, p in dist if b.midpoint is not None]
        if pts:
            implied_mean = sum(m * p for m, p in pts)
            var = sum(p * (m - implied_mean) ** 2 for m, p in pts)
            implied_std = math.sqrt(var) if var > 0 else 0.0

    # OI concentration sur le bin modal
    modal_oi_share = None
    total_oi = sum(b.open_interest for b in bins) or 0.0
    if total_oi > 0 and dist:
        # bin modal = proba normalisée maximale
        modal_bin = max(dist, key=lambda x: x[1])[0]
        modal_oi_share = modal_bin.open_interest / total_oi

    # Tail mass : bins aux extrémités cumulées (≤10e centile et ≥90e)
    tail_mass = None
    if dist:
        tail_mass = sum(p for b, p in dist if (
            b.strike_type == "less" or b.strike_type == "greater"
        ))
        # fallback : si pas de bornes ouvertes, prends les deux extrêmes
        if tail_mass == 0.0 and len(dist) >= 2:
            sorted_dist = sorted(dist, key=lambda x: (
                x[0].midpoint if x[0].midpoint is not None else 0.0
            ))
            tail_mass = sorted_dist[0][1] + sorted_dist[-1][1]

    if n_quoted < n_bins:
        notes.append(f"{n_bins - n_quoted} bins non quotés (bid OU ask manquant)")
    if s_mid is not None and abs(s_mid - 1.0) > 0.05:
        if s_mid > 1.05:
            notes.append(f"vig importante : sum_mid={s_mid:.3f} → coût ~{(s_mid-1)*100:.1f}%")
        else:
            notes.append(f"sum_mid={s_mid:.3f} sous 1 → arbitrage théorique au mid")

    return EventBiases(
        event_ticker=event_ticker,
        n_bins=n_bins,
        n_quoted=n_quoted,
        sum_mid=s_mid,
        vig_residual=vig,
        median_spread=median_spread,
        extreme_spread_avg=extreme_spread,
        central_spread_avg=central_spread,
        spread_skew=spread_skew,
        implied_mean=implied_mean,
        implied_std=implied_std,
        modal_oi_share=modal_oi_share,
        tail_mass=tail_mass,
        notes=notes,
    )


def _median(xs: list[float]) -> float:
    s = sorted(xs)
    n = len(s)
    if n == 0:
        return 0.0
    if n % 2 == 1:
        return s[n // 2]
    return (s[n // 2 - 1] + s[n // 2]) / 2.0


# -- Tail underpricing vs climatologie --

def tail_underpricing_vs_climato(
    bins: list[BinQuote],
    climato_probs_per_bin: dict[str, float],
) -> Optional[dict]:
    """Compare la proba implicite Kalshi à la climato pour chaque bin extrême.

    Args:
        bins: les BinQuote de l'event.
        climato_probs_per_bin: dict ticker → P_climato(YES) calculée séparément.

    Returns:
        Pour les bins "less" / "greater" (les tails ouvertes), l'écart
        climato - implied_mid. Si > 0 et taille suffisante, signal de bin
        sous-coté (acheter YES paie en espérance).
    """
    out: dict[str, dict] = {}
    for b in bins:
        if b.strike_type not in ("less", "greater"):
            continue
        if b.yes_mid is None:
            continue
        p_climato = climato_probs_per_bin.get(b.ticker)
        if p_climato is None:
            continue
        edge_yes = p_climato - b.yes_mid          # YES sous-coté si edge > 0
        edge_no = (1 - p_climato) - (1 - b.yes_mid)  # symétrique
        out[b.ticker] = {
            "tail_side": b.strike_type,
            "yes_mid": b.yes_mid,
            "p_climato": p_climato,
            "edge_yes": edge_yes,
            "edge_no": edge_no,
            "bid_size_yes": b.yes_bid_size,
            "ask_size_yes": b.yes_ask_size,
        }
    if not out:
        return None
    return out
