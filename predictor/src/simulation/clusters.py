"""Clusters spatio-temporels pour le cap de corrélation des paris Kalshi.

Implémente le mapping ville → région NOAA et le parsing des tickers Kalshi,
support du portfolio-heat / correlation cap décrit dans le RFC :
``research/rfc/RFC-portfolio-heat-and-correlation-caps.md``.

Le parsing distingue les tickers *daily* des tickers *monthly* par la
longueur du segment date (``YYMMMDD`` vs ``YYMMM``). En monthly, le code
ville porte un ``M`` final (ex. ``KXRAINMIAM-26MAY`` → ville ``MIA``).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Literal

NOAARegion = Literal["NE", "SE", "MW", "NW", "SW", "PLAINS", "AK", "HI"]

# Préfixes de type de marché Kalshi observés dans data/markets/.
# IMPORTANT : ordre par longueur décroissante (matcher HIGHT avant HIGH).
_MARKET_TYPE_PREFIXES: tuple[str, ...] = ("HIGHT", "LOWT", "TEMP", "HIGH", "RAIN")

# Mapping ville → région NOAA pragmatique. On garde la grille à 8 régions
# du RFC ({NE, SE, MW, NW, SW, PLAINS, AK, HI}) sans introduire de "WEST"
# séparé : SoCal, Vegas et Phoenix sont regroupés dans SW.
CITY_TO_NOAA: dict[str, NOAARegion] = {
    # Northeast
    "NYC": "NE", "NY": "NE", "BOS": "NE", "PHIL": "NE", "DC": "NE",
    # Southeast / Gulf
    "ATL": "SE", "MIA": "SE", "HOU": "SE", "NOLA": "SE",
    # Midwest
    "CHI": "MW", "MIN": "MW",
    # Northwest
    "SEA": "NW", "PDX": "NW",
    # Southwest (inclut SoCal et Désert)
    "LAX": "SW", "SFO": "SW", "PHX": "SW", "SAN": "SW", "LV": "SW",
    # Plaines (Texas hors Houston + Oklahoma + Front Range)
    "DAL": "PLAINS", "AUS": "PLAINS", "OKC": "PLAINS", "DEN": "PLAINS",
    "SATX": "PLAINS",
}

# Date d'un marché Kalshi en fin de ticker :
#   daily   → ``YYMMMDD`` (7 chars, ex. ``26MAY08``)
#   monthly → ``YYMMM``   (5 chars, ex. ``26MAY``)
_DATE_DAILY_RE = re.compile(r"^\d{2}[A-Z]{3}\d{2}$")
_DATE_MONTHLY_RE = re.compile(r"^\d{2}[A-Z]{3}$")


@dataclass(frozen=True)
class BetContext:
    """Snapshot d'un pari ouvert utilisé par ``PortfolioHeat``.

    ``fraction_engaged`` est la fraction de bankroll réellement engagée
    (montant misé / bankroll au moment du sizing). Le cumul de ces
    fractions sur les paris non-settled alimente le portfolio heat et
    le cluster cap.
    """

    bet_id: str
    market_ticker: str
    spatial_cluster: NOAARegion
    settlement_date: date
    fraction_engaged: float


def parse_city_from_ticker(ticker: str) -> str:
    """Extrait le code ville d'un ticker Kalshi météo.

    Formats supportés :
      - daily   : ``KX{TYPE}{CITY}-{YYMMMDD}``  ex. ``KXLOWTNYC-26MAY17``
      - monthly : ``KX{TYPE}{CITY}M-{YYMMM}``   ex. ``KXRAINCHIM-26MAY``

    En monthly, le ``M`` final du segment ville est strippé après détection
    via la longueur du segment date — pas via une heuristique sur les
    dernières lettres du code ville (sinon ``MIAM`` ressemble à un code).

    Lève ``ValueError`` si le ticker n'est pas parseable (préfixe absent,
    market type inconnu, segment date non reconnu).
    """
    if not ticker or "-" not in ticker:
        raise ValueError(f"Ticker non parseable (pas de tiret) : {ticker!r}")
    head, _, date_part = ticker.rpartition("-")
    if _DATE_DAILY_RE.match(date_part):
        is_monthly = False
    elif _DATE_MONTHLY_RE.match(date_part):
        is_monthly = True
    else:
        raise ValueError(
            f"Segment date non reconnu dans le ticker {ticker!r} : "
            f"attendu YYMMMDD ou YYMMM, reçu {date_part!r}."
        )
    if not head.startswith("KX"):
        raise ValueError(
            f"Ticker ne commence pas par 'KX' : {ticker!r}."
        )
    after_kx = head[2:]
    for prefix in _MARKET_TYPE_PREFIXES:
        if after_kx.startswith(prefix):
            city = after_kx[len(prefix):]
            break
    else:
        raise ValueError(
            f"Type de marché inconnu dans {ticker!r} : "
            f"préfixes connus = {_MARKET_TYPE_PREFIXES}."
        )
    if is_monthly:
        if not city.endswith("M"):
            raise ValueError(
                f"Ticker monthly {ticker!r} : segment ville {city!r} "
                f"devrait se terminer par 'M'."
            )
        city = city[:-1]
    if not city:
        raise ValueError(f"Code ville vide après parsing de {ticker!r}.")
    return city


def spatial_cluster_for_ticker(ticker: str) -> NOAARegion:
    """Retourne la région NOAA du ticker, ou lève ``ValueError``."""
    city = parse_city_from_ticker(ticker)
    if city not in CITY_TO_NOAA:
        raise ValueError(
            f"Ville {city!r} (ticker {ticker!r}) absente du mapping NOAA. "
            f"Ajouter dans CITY_TO_NOAA après vérification de la région."
        )
    return CITY_TO_NOAA[city]


def same_settlement_window(d1: date, d2: date, window_days: int = 3) -> bool:
    """Vrai si les deux dates sont à ``window_days`` jours ou moins l'une de
    l'autre (bornes incluses)."""
    return abs((d1 - d2).days) <= window_days
