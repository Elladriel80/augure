"""Modèles de données Kalshi (lecture seule)."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Series:
    """Une série Kalshi regroupe des events récurrents (ex: KXSNOWNYM = neige NYC)."""
    ticker: str
    title: str
    category: Optional[str] = None
    raw: dict = field(default_factory=dict)

    @classmethod
    def from_api(cls, data: dict) -> "Series":
        return cls(
            ticker=data.get("ticker", ""),
            title=data.get("title", ""),
            category=data.get("category"),
            raw=data,
        )


@dataclass
class Market:
    """Un contrat binaire OUI/NON. Prix exposés en dollars [0.0, 1.0] = proba implicite."""
    ticker: str
    event_ticker: str
    subtitle: str
    yes_bid: Optional[float]    # dollars [0.0, 1.0]
    yes_ask: Optional[float]    # dollars [0.0, 1.0]
    last_price: Optional[float] # dollars
    volume: Optional[float]
    status: str                  # "active", "closed", "settled"
    close_time: Optional[datetime]
    expiration_time: Optional[datetime]
    rules_primary: str
    result: Optional[str]        # "yes", "no", None si non résolu
    raw: dict = field(default_factory=dict)

    @property
    def implied_prob_yes(self) -> Optional[float]:
        """Probabilité implicite par le marché (mid yes_bid/yes_ask) en [0,1]."""
        if self.yes_bid is None or self.yes_ask is None:
            return None
        return (self.yes_bid + self.yes_ask) / 2.0

    @property
    def is_resolved(self) -> bool:
        return self.result in ("yes", "no")

    @classmethod
    def from_api(cls, data: dict) -> "Market":
        def parse_dt(s: Optional[str]) -> Optional[datetime]:
            if not s:
                return None
            try:
                return datetime.fromisoformat(s.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                return None

        # L'API Kalshi expose les prix en deux formes :
        # - cents int (champ legacy : "yes_bid", "yes_ask", "last_price")
        # - dollars string (champ récent : "yes_bid_dollars", "yes_ask_dollars",
        #   "last_price_dollars"). On normalise tout vers des floats [0.0, 1.0].
        return cls(
            ticker=data.get("ticker", ""),
            event_ticker=data.get("event_ticker", ""),
            subtitle=data.get("subtitle") or data.get("yes_sub_title") or "",
            yes_bid=_price_to_dollars(data, "yes_bid"),
            yes_ask=_price_to_dollars(data, "yes_ask"),
            last_price=_price_to_dollars(data, "last_price"),
            volume=_to_float(data.get("volume_fp")) or _to_float(data.get("volume")),
            status=data.get("status", ""),
            close_time=parse_dt(data.get("close_time")),
            expiration_time=parse_dt(data.get("expiration_time")),
            rules_primary=data.get("rules_primary", ""),
            result=data.get("result") or None,
            raw=data,
        )


def _to_float(x) -> Optional[float]:
    if x is None or x == "":
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _price_to_dollars(data: dict, base_field: str) -> Optional[float]:
    """Lit un prix Kalshi et renvoie sa valeur en dollars [0.0, 1.0].

    Tente d'abord ``<base>_dollars`` (string) puis ``<base>`` (cents int).
    """
    dollars_str = data.get(f"{base_field}_dollars")
    v = _to_float(dollars_str)
    if v is not None:
        return v
    cents = _to_float(data.get(base_field))
    if cents is not None:
        return cents / 100.0
    return None


@dataclass
class Event:
    """Un event regroupe des markets mutuellement exclusifs (ex: les bins de température)."""
    event_ticker: str
    series_ticker: str
    title: str
    sub_title: Optional[str]
    mutually_exclusive: bool
    markets: list[Market]
    raw: dict = field(default_factory=dict)

    @classmethod
    def from_api(cls, data: dict) -> "Event":
        markets_raw = data.get("markets", []) or []
        return cls(
            event_ticker=data.get("event_ticker", ""),
            series_ticker=data.get("series_ticker", ""),
            title=data.get("title", ""),
            sub_title=data.get("sub_title"),
            mutually_exclusive=bool(data.get("mutually_exclusive")),
            markets=[Market.from_api(m) for m in markets_raw],
            raw=data,
        )
