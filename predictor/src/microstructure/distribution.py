"""Extraction de la distribution implicite d'un event Kalshi mutuellement exclusif.

Pour les events 'highest temp in city' / 'lowest temp', les bins forment une
partition (mutually_exclusive=True) — les YES_mid devraient sommer à ~1.
On extrait :
- la liste des bins ordonnée par seuil croissant,
- les midpoints (centre du bin) pour pouvoir calculer une moyenne/std,
- les prix bid/ask et le mid YES,
- l'open interest et le volume.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class BinQuote:
    """Cotation d'un bin de l'event mutuellement exclusif."""
    ticker: str
    strike_type: str                # "less", "greater", "between"
    floor: Optional[float]
    cap: Optional[float]
    yes_bid_dollars: Optional[float]
    yes_ask_dollars: Optional[float]
    yes_bid_size: float
    yes_ask_size: float
    last_price_dollars: Optional[float]
    open_interest: float
    volume_24h: float

    @property
    def yes_mid(self) -> Optional[float]:
        if self.yes_bid_dollars is None or self.yes_ask_dollars is None:
            return None
        return (self.yes_bid_dollars + self.yes_ask_dollars) / 2.0

    @property
    def spread(self) -> Optional[float]:
        if self.yes_bid_dollars is None or self.yes_ask_dollars is None:
            return None
        return self.yes_ask_dollars - self.yes_bid_dollars

    @property
    def midpoint(self) -> Optional[float]:
        """Centre estimé du bin sur l'axe variable (utile pour calculer une moyenne).

        Pour un bin "less than 76" (T76), le centre est borné à gauche par
        l'extrémité du bin précédent. On retourne ici la borne du seuil :
        les ouvertures ouvertes (T76 et T83 par ex.) se voient attribuer
        cap-1 ou floor+1 comme proxy ; le caller peut ensuite raffiner.
        """
        if self.strike_type == "between" and self.floor is not None and self.cap is not None:
            return (self.floor + self.cap) / 2.0
        if self.strike_type == "less" and self.cap is not None:
            return self.cap - 0.5
        if self.strike_type == "greater" and self.floor is not None:
            return self.floor + 0.5
        return None


def extract_bins(event_raw: dict) -> list[BinQuote]:
    """Extrait les bins d'un event raw (depuis snapshot JSON)."""
    bins: list[BinQuote] = []
    for m in event_raw.get("markets", []) or []:
        bins.append(BinQuote(
            ticker=m.get("ticker", ""),
            strike_type=(m.get("strike_type") or "").lower(),
            floor=_to_float(m.get("floor_strike")),
            cap=_to_float(m.get("cap_strike")),
            yes_bid_dollars=_to_float(m.get("yes_bid_dollars")),
            yes_ask_dollars=_to_float(m.get("yes_ask_dollars")),
            yes_bid_size=_to_float(m.get("yes_bid_size_fp")) or 0.0,
            yes_ask_size=_to_float(m.get("yes_ask_size_fp")) or 0.0,
            last_price_dollars=_to_float(m.get("last_price_dollars")),
            open_interest=_to_float(m.get("open_interest_fp")) or 0.0,
            volume_24h=_to_float(m.get("volume_24h_fp")) or 0.0,
        ))
    # Tri par midpoint croissant pour avoir la distribution dans l'ordre
    bins.sort(key=lambda b: (b.midpoint if b.midpoint is not None else float("inf")))
    return bins


def sum_yes_mid(bins: list[BinQuote]) -> Optional[float]:
    """Somme des YES mid sur les bins quotés. ~1 idéal, > 1 = vig."""
    vals = [b.yes_mid for b in bins if b.yes_mid is not None]
    if not vals:
        return None
    return sum(vals)


def implied_distribution(bins: list[BinQuote]) -> list[tuple[BinQuote, float]]:
    """Renvoie (bin, prob_normalisée) pour les bins quotés. Normalisation = somme 1."""
    quoted = [(b, b.yes_mid) for b in bins if b.yes_mid is not None and b.yes_mid > 0]
    total = sum(p for _, p in quoted)
    if total <= 0:
        return []
    return [(b, p / total) for b, p in quoted]


def implied_mean_std(bins: list[BinQuote]) -> Optional[tuple[float, float]]:
    """Moyenne et std implicites de la variable, en utilisant midpoints + probs normalisées."""
    dist = implied_distribution(bins)
    pts = [(b.midpoint, p) for b, p in dist if b.midpoint is not None]
    if not pts:
        return None
    mean = sum(m * p for m, p in pts)
    var = sum(p * (m - mean) ** 2 for m, p in pts)
    return mean, math.sqrt(var) if var > 0 else 0.0


def _to_float(x) -> Optional[float]:
    if x is None or x == "":
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None
