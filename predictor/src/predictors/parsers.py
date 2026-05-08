"""Parsing des tickers/subtitles Kalshi vers ContractSpec."""
from __future__ import annotations
import re
from datetime import date, datetime
from typing import Optional

from src.kalshi.models import Market
from .base import ContractSpec, WeatherVar


# Mapping series_prefix → (variable, city_key)
# Le prefix est l'en-tête du ticker avant le '-'.
SERIES_MAP: dict[str, tuple[WeatherVar, str]] = {
    "KXHIGHAUS":  ("temp_max", "AUSTIN"),
    "KXLOWTAUS":  ("temp_min", "AUSTIN"),
    "KXHIGHCHI":  ("temp_max", "CHICAGO"),
    "KXLOWTCHI":  ("temp_min", "CHICAGO"),
    "KXHIGHHOU":  ("temp_max", "HOUSTON"),
    "KXLOWTHOU":  ("temp_min", "HOUSTON"),
    "KXHIGHNYC":  ("temp_max", "NYC"),
    "KXLOWTNYC":  ("temp_min", "NYC"),
    "KXHIGHMIA":  ("temp_max", "MIAMI"),
    "KXLOWTMIA":  ("temp_min", "MIAMI"),
    "KXHIGHLA":   ("temp_max", "LOSANGELES"),
    "KXLOWTLA":   ("temp_min", "LOSANGELES"),
    "KXHIGHSATX": ("temp_max", "SANANTONIO"),
    "KXLOWTSATX": ("temp_min", "SANANTONIO"),
    "KXHIGHSF":   ("temp_max", "SANFRANCISCO"),
    "KXLOWTSF":   ("temp_min", "SANFRANCISCO"),
    "KXHIGHBOS":  ("temp_max", "BOSTON"),
    "KXLOWTBOS":  ("temp_min", "BOSTON"),
    "KXHIGHDEN":  ("temp_max", "DENVER"),
    "KXLOWTDEN":  ("temp_min", "DENVER"),
    "KXHIGHPHIL": ("temp_max", "PHILADELPHIA"),
    "KXLOWTPHIL": ("temp_min", "PHILADELPHIA"),
}


# Format date Kalshi: "26MAY08" = 2026-05-08
DATE_RE = re.compile(r"^(\d{2})([A-Z]{3})(\d{2})$")
MONTH_MAP = {m: i + 1 for i, m in enumerate([
    "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
    "JUL", "AUG", "SEP", "OCT", "NOV", "DEC",
])}


def parse_kalshi_date(token: str) -> Optional[date]:
    """26MAY08 → 2026-05-08."""
    m = DATE_RE.match(token)
    if not m:
        return None
    yy, mon, dd = m.groups()
    if mon not in MONTH_MAP:
        return None
    year = 2000 + int(yy)
    return date(year, MONTH_MAP[mon], int(dd))


# Subtitle patterns observés:
#   "75° or below"
#   "76° to 77°"
#   "84° or above"
#   "Below 1.0\""    (snow)
#   "Above 5.0\""
#   "1.0\" to 2.0\""
SUBTITLE_PATTERNS = [
    # "X° or below" → upper=X
    (re.compile(r"(?P<x>-?\d+(?:\.\d+)?)°?\s*or\s*below", re.I),
     lambda m: (None, float(m.group("x")))),
    # "X or below"
    (re.compile(r"(?P<x>-?\d+(?:\.\d+)?)\"?\s*or\s*less", re.I),
     lambda m: (None, float(m.group("x")))),
    (re.compile(r"below\s+(?P<x>-?\d+(?:\.\d+)?)", re.I),
     lambda m: (None, float(m.group("x")))),
    # "X° or above" / "X or more"
    (re.compile(r"(?P<x>-?\d+(?:\.\d+)?)°?\s*or\s*above", re.I),
     lambda m: (float(m.group("x")), None)),
    (re.compile(r"(?P<x>-?\d+(?:\.\d+)?)\"?\s*or\s*more", re.I),
     lambda m: (float(m.group("x")), None)),
    (re.compile(r"above\s+(?P<x>-?\d+(?:\.\d+)?)", re.I),
     lambda m: (float(m.group("x")), None)),
    # "X° to Y°"
    (re.compile(r"(?P<x>-?\d+(?:\.\d+)?)°?\s*to\s*(?P<y>-?\d+(?:\.\d+)?)°?", re.I),
     lambda m: (float(m.group("x")), float(m.group("y")))),
]


def parse_subtitle_bounds(subtitle: str) -> Optional[tuple[Optional[float], Optional[float]]]:
    """Extrait (lower, upper) depuis un subtitle Kalshi. Renvoie None si non parsable."""
    s = (subtitle or "").strip()
    if not s:
        return None
    for pattern, builder in SUBTITLE_PATTERNS:
        m = pattern.search(s)
        if m:
            return builder(m)
    return None


def parse_ticker(ticker: str) -> Optional[tuple[str, date, str]]:
    """Décompose un ticker Kalshi en (series_prefix, target_date, market_suffix).

    Ex: 'KXHIGHAUS-26MAY08-T76' → ('KXHIGHAUS', date(2026,5,8), 'T76')
    """
    parts = ticker.split("-")
    if len(parts) < 3:
        return None
    series_prefix = parts[0]
    date_token = parts[1]
    market_suffix = "-".join(parts[2:])
    target_date = parse_kalshi_date(date_token)
    if target_date is None:
        return None
    return series_prefix, target_date, market_suffix


def parse_market(market: Market) -> Optional[ContractSpec]:
    """Tente de parser un Market en ContractSpec normalisée. Renvoie None si non supporté."""
    parsed = parse_ticker(market.ticker)
    if parsed is None:
        return None
    series_prefix, target_date, _suffix = parsed

    if series_prefix not in SERIES_MAP:
        return None  # série non supportée pour l'instant
    variable, location_key = SERIES_MAP[series_prefix]

    bounds = parse_subtitle_bounds(market.subtitle)
    if bounds is None:
        return None
    lower, upper = bounds

    return ContractSpec(
        market_ticker=market.ticker,
        event_ticker=market.event_ticker,
        variable=variable,
        location_key=location_key,
        target_date=target_date,
        lower=lower,
        upper=upper,
        raw_subtitle=market.subtitle,
    )
