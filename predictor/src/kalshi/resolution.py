"""Décodage des règles de résolution Kalshi (NWS Climatological Reports).

Phase B-1 — l'edge "résolution NWS" : Kalshi résout sur la base du
*Climatological Report (Daily)* d'une station NWS précise (Austin Bergstrom,
Central Park, etc.), avec un arrondi spécifique (entier pour les temps, 0.01"
pour la précip), et des conventions particulières (Trace = OUI pour la pluie).

Ce module :
1. Extrait la règle de résolution exacte d'un payload Market Kalshi
   (en s'appuyant sur ``cap_strike``/``floor_strike``/``strike_type`` plutôt
   que sur le subtitle ambigu) ;
2. Identifie la station NWS officielle (avec son code ICAO et ses coordonnées
   exactes — utile pour requêter Open-Meteo ou Meteostat sur le bon point) ;
3. Applique l'arrondi NWS sur une observation pour produire le verdict de
   résolution déterministe.

L'edge attendu : le grand public regarde des prévisions arrondies à la baisse
sur des sources grand-public (AccuWeather, Google Weather) ou des points
géographiques imprécis (centre-ville). Le module nous permet de raisonner
contre la *vraie* règle.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Literal, Optional

from .models import Market


# -- Type aliases --

ResolutionVariable = Literal["temp_max", "temp_min", "precip_in", "snow_in"]
StrikeType = Literal["less", "greater", "between"]
Rounding = Literal["nearest_int", "nearest_0.01"]


# -- Catalogue de stations NWS (CLI = Climatological Report Daily) --
#
# ICAO + coordonnées exactes du point de mesure. Quand un marché parle de
# "Chicago", il faut savoir s'il s'agit de O'Hare (KORD) ou Midway (KMDW) :
# ce ne sont pas le même climat.

@dataclass(frozen=True)
class NWSStation:
    cli_code: str          # ex "CLIAUS" (le code NWS du Climatological Report)
    icao: str              # ex "KAUS"
    name: str              # nom officiel ("Austin Bergstrom")
    lat: float
    lon: float
    wfo: str               # bureau de prévision NWS responsable (ex "ewx" pour Austin)


NWS_STATIONS: dict[str, NWSStation] = {
    "CLIAUS":  NWSStation("CLIAUS",  "KAUS",  "Austin Bergstrom",         30.1945, -97.6699, "ewx"),
    "CLINYC":  NWSStation("CLINYC",  "KNYC",  "New York Central Park",    40.7794, -73.9692, "okx"),
    "CLIORD":  NWSStation("CLIORD",  "KORD",  "Chicago O'Hare",           41.9803, -87.9090, "lot"),
    "CLIMDW":  NWSStation("CLIMDW",  "KMDW",  "Chicago Midway",           41.7868, -87.7522, "lot"),
    "CLIMIA":  NWSStation("CLIMIA",  "KMIA",  "Miami Intl",               25.7959, -80.2870, "mfl"),
    "CLILAX":  NWSStation("CLILAX",  "KLAX",  "Los Angeles Intl",         33.9425, -118.4081, "lox"),
    "CLIBOS":  NWSStation("CLIBOS",  "KBOS",  "Boston Logan",             42.3656, -71.0096, "box"),
    "CLIDEN":  NWSStation("CLIDEN",  "KDEN",  "Denver Intl",              39.8561, -104.6737, "bou"),
    "CLIPHL":  NWSStation("CLIPHL",  "KPHL",  "Philadelphia Intl",        39.8729, -75.2437, "phi"),
    "CLISFO":  NWSStation("CLISFO",  "KSFO",  "San Francisco Intl",       37.6213, -122.3790, "mtr"),
    "CLISAT":  NWSStation("CLISAT",  "KSAT",  "San Antonio Intl",         29.5337, -98.4698, "ewx"),
    "CLIPHX":  NWSStation("CLIPHX",  "KPHX",  "Phoenix Sky Harbor",       33.4373, -112.0078, "psr"),
    "CLIOKC":  NWSStation("CLIOKC",  "KOKC",  "Oklahoma City Will Rogers", 35.3931, -97.6007, "oun"),
    "CLIMSP":  NWSStation("CLIMSP",  "KMSP",  "Minneapolis-St Paul",      44.8848, -93.2223, "mpx"),
    "CLIIAH":  NWSStation("CLIIAH",  "KIAH",  "Houston Intercontinental", 29.9844, -95.3414, "hgx"),
    "CLISEA":  NWSStation("CLISEA",  "KSEA",  "Seattle-Tacoma",           47.4502, -122.3088, "sew"),
    "CLILAS":  NWSStation("CLILAS",  "KLAS",  "Las Vegas McCarran",       36.0840, -115.1537, "vef"),
    "CLIDCA":  NWSStation("CLIDCA",  "KDCA",  "Washington-National",      38.8521, -77.0377, "lwx"),
    # Note : KXHIGHTLV / KXLOWTLV correspondent à Las Vegas (CLILAS), pas Tel Aviv —
    # le tag "TLV" est une convention Kalshi interne (cf. rules_primary).
}


# Mapping series_prefix Kalshi → CLI code probable.
# Source vérifiée empiriquement sur les snapshots data/markets/.
# Pour les ambiguïtés (Chicago HIGH/LOW utilise O'Hare ou Midway selon série),
# on s'en remet à l'extraction texte de rules_primary — ce mapping est juste
# un fallback.
SERIES_TO_STATION: dict[str, str] = {
    "KXHIGHAUS":  "CLIAUS",
    "KXLOWTAUS":  "CLIAUS",
    "KXHIGHCHI":  "CLIORD",   # série principale Chicago = O'Hare
    "KXLOWTCHI":  "CLIORD",
    "KXHIGHTHOU": "CLIIAH",
    "KXHIGHTHOUS":"CLIIAH",
    "KXLOWTHOU":  "CLIIAH",
    "KXHIGHNY":   "CLINYC",
    "KXHIGHNYC":  "CLINYC",
    "KXLOWTNYC":  "CLINYC",
    "KXHIGHMIA":  "CLIMIA",
    "KXLOWTMIA":  "CLIMIA",
    "KXHIGHLAX":  "CLILAX",
    "KXLOWTLAX":  "CLILAX",
    "KXHIGHSATX": "CLISAT",
    "KXLOWTSATX": "CLISAT",
    "KXHIGHTSFO": "CLISFO",
    "KXLOWTSFO":  "CLISFO",
    "KXHIGHTBOS": "CLIBOS",
    "KXLOWTBOS":  "CLIBOS",
    "KXHIGHDEN":  "CLIDEN",
    "KXLOWTDEN":  "CLIDEN",
    "KXHIGHPHIL": "CLIPHL",
    "KXLOWTPHIL": "CLIPHL",
    "KXHIGHTPHX": "CLIPHX",
    "KXLOWTPHX":  "CLIPHX",
    "KXHIGHTOKC": "CLIOKC",
    "KXLOWTOKC":  "CLIOKC",
    "KXHIGHTMIN": "CLIMSP",
    "KXLOWTMIN":  "CLIMSP",
    "KXLOWTSEA":  "CLISEA",
    "KXHIGHTLV":  "CLILAS",     # Kalshi 'TLV' = Las Vegas (cf. rules_primary)
    "KXLOWTLV":   "CLILAS",
    "KXLOWTDC":   "CLIDCA",
    "KXHIGHDC":   "CLIDCA",
    "KXRAINNYC":  "CLINYC",
    "KXRAINNYCM": "CLINYC",
    "KXRAINCHI":  "CLIORD",
    "KXRAINCHIM": "CLIMDW",     # série pluie mensuelle Chicago = Midway
    "KXRAINMIAM": "CLIMIA",
    "KXRAINHOUM": "CLIIAH",
    "KXRAINSEAM": "CLISEA",
    "KXRAINAUSM": "CLIAUS",
}


# -- Variable inference --

# Préfixes de série → variable météo cible.
SERIES_TO_VARIABLE: dict[str, ResolutionVariable] = {
    "KXHIGH":  "temp_max",
    "KXHIGHT": "temp_max",
    "KXLOWT":  "temp_min",
    "KXLOW":   "temp_min",
    "KXRAIN":  "precip_in",
    "KXSNOW":  "snow_in",
}


def infer_variable(series_prefix: str) -> Optional[ResolutionVariable]:
    """Devine la variable météo depuis le préfixe série (KXHIGH... = temp_max)."""
    # Ordre par longueur décroissante pour matcher KXHIGHT avant KXHIGH.
    for prefix in sorted(SERIES_TO_VARIABLE, key=len, reverse=True):
        if series_prefix.startswith(prefix):
            return SERIES_TO_VARIABLE[prefix]
    return None


# -- Extraction de la station depuis rules_primary --

# Patterns observés dans les snapshots :
# - "recorded in Austin Bergstrom for May 08, 2026 as reported by ..."
# - "recorded at Central Park, New York on May 08, 2026 ..."
# - "at CLIMDW in Chicago in May 2026"
# - "at Seattle for May 8, 2026"
_STATION_PATTERNS = [
    re.compile(r"\bat\s+(CLI[A-Z]{3,4})\b"),
    re.compile(r"recorded\s+(?:at|in)\s+([A-Z][\w\s\-,'\.]+?)\s+(?:for|on)\s+\w+", re.I),
    re.compile(r"\bat\s+([A-Z][\w\s\-,'\.]+?)\s+(?:for|on)\s+\w+", re.I),
]

# Mots-clés textuels pour identifier la station si seule la ville est citée.
_NAME_TO_STATION: dict[str, str] = {
    "austin bergstrom": "CLIAUS",
    "central park":     "CLINYC",
    "central park, new york": "CLINYC",
    "chicago o'hare":   "CLIORD",
    "o'hare":           "CLIORD",
    "chicago midway":   "CLIMDW",
    "midway":           "CLIMDW",
    "miami intl":       "CLIMIA",
    "los angeles intl": "CLILAX",
    "lax":              "CLILAX",
    "boston logan":     "CLIBOS",
    "denver intl":      "CLIDEN",
    "philadelphia intl": "CLIPHL",
    "san francisco intl": "CLISFO",
    "san antonio intl": "CLISAT",
    "phoenix sky harbor": "CLIPHX",
    "oklahoma city":    "CLIOKC",
    "minneapolis":      "CLIMSP",
    "houston intercontinental": "CLIIAH",
    "seattle-tacoma":   "CLISEA",
    "seattle":          "CLISEA",
    "las vegas":        "CLILAS",
    "washington-national": "CLIDCA",
    "washington dc":    "CLIDCA",
    "washington":       "CLIDCA",
}


def extract_station(rules_primary: str, series_ticker: str = "") -> Optional[NWSStation]:
    """Extrait la station NWS depuis le texte des règles, avec fallback série.

    Stratégie :
    1. Cherche un code CLI explicite ("at CLIMDW") — le plus fiable.
    2. Cherche une mention de nom de station connue ("Central Park").
    3. Fallback sur SERIES_TO_STATION avec le préfixe série.
    """
    text = (rules_primary or "")
    text_lower = text.lower()

    # 1. Code CLI explicite
    for pat in _STATION_PATTERNS:
        m = pat.search(text)
        if not m:
            continue
        token = m.group(1)
        if token.upper().startswith("CLI") and token.upper() in NWS_STATIONS:
            return NWS_STATIONS[token.upper()]

    # 2. Match par nom (priorité aux noms les plus longs/spécifiques)
    for name in sorted(_NAME_TO_STATION, key=len, reverse=True):
        if name in text_lower:
            return NWS_STATIONS[_NAME_TO_STATION[name]]

    # 3. Fallback série
    if series_ticker:
        # On retire le suffixe date/strike pour ne garder que le préfixe série.
        prefix = series_ticker.split("-")[0]
        cli = SERIES_TO_STATION.get(prefix)
        if cli and cli in NWS_STATIONS:
            return NWS_STATIONS[cli]

    return None


# -- Règle de résolution --

@dataclass
class ResolutionRule:
    """Règle de résolution déterministe d'un marché Kalshi météo."""
    market_ticker: str
    variable: Optional[ResolutionVariable]
    strike_type: StrikeType
    floor_strike: Optional[float]   # borne inférieure (incluse pour temp arrondi entier)
    cap_strike: Optional[float]     # borne supérieure (varie selon strike_type)
    station: Optional[NWSStation]
    rounding: Rounding
    trace_is_yes: bool              # convention pluie : Trace résout OUI si seuil = 0
    rules_primary: str = field(repr=False)
    notes: list[str] = field(default_factory=list)

    @property
    def station_code(self) -> Optional[str]:
        return self.station.cli_code if self.station else None

    def describe(self) -> str:
        st = self.station.icao if self.station else "?"
        if self.strike_type == "less":
            return f"{self.variable} @ {st} : OUI si obs (arrondi) < {self.cap_strike}"
        if self.strike_type == "greater":
            return f"{self.variable} @ {st} : OUI si obs (arrondi) > {self.floor_strike}"
        return f"{self.variable} @ {st} : OUI si {self.floor_strike} <= obs (arrondi) <= {self.cap_strike}"


def _infer_rounding(variable: Optional[ResolutionVariable]) -> Rounding:
    if variable in ("precip_in", "snow_in"):
        return "nearest_0.01"
    return "nearest_int"


def extract_resolution_rule(market: Market) -> Optional[ResolutionRule]:
    """Construit une ResolutionRule depuis un Market Kalshi.

    Renvoie None si la donnée brute n'a pas les champs nécessaires.
    """
    raw = market.raw or {}
    strike_type_str = (raw.get("strike_type") or "").lower()
    if strike_type_str not in ("less", "greater", "between"):
        return None

    series_prefix = market.ticker.split("-")[0] if market.ticker else ""
    variable = infer_variable(series_prefix)
    rounding = _infer_rounding(variable)

    # cap_strike / floor_strike sont parfois absents (notamment pour les bornes ouvertes).
    cap = raw.get("cap_strike")
    floor = raw.get("floor_strike")
    cap = float(cap) if cap is not None else None
    floor = float(floor) if floor is not None else None

    notes: list[str] = []
    rules_primary = raw.get("rules_primary", "") or ""
    rules_secondary = raw.get("rules_secondary", "") or ""

    # Convention "Trace = OUI" : présente uniquement dans les rain markets seuil 0.
    trace_is_yes = False
    if variable in ("precip_in", "snow_in"):
        if ("trace" in rules_secondary.lower() or "is t " in rules_secondary.lower()
                or " t (" in rules_secondary.lower()):
            trace_is_yes = True
            notes.append("Trace = YES (NWS reports 'T' for trace precipitation)")

    # Détection arrondi explicite dans rules_secondary
    if "rounding" in rules_secondary.lower():
        notes.append("rules_secondary mentions rounding/conversion nuances")

    station = extract_station(rules_primary, series_ticker=market.ticker)
    if station is None:
        notes.append("station NWS non identifiée — résolution sera approximative")

    return ResolutionRule(
        market_ticker=market.ticker,
        variable=variable,
        strike_type=strike_type_str,  # type: ignore[arg-type]
        floor_strike=floor,
        cap_strike=cap,
        station=station,
        rounding=rounding,
        trace_is_yes=trace_is_yes,
        rules_primary=rules_primary,
        notes=notes,
    )


# -- Application de l'arrondi NWS --

def apply_nws_rounding(value: float, rounding: Rounding) -> float:
    """Reproduit l'arrondi qu'applique le NWS Climatological Report.

    - Temp : reportée en degrés entiers, *round half up* (75.5 → 76, 76.5 → 77).
      C'est la convention de la NWS Surface Observation Manual, distincte du
      banker's rounding par défaut de Python (qui ferait 76.5 → 76).
    - Précip : reportée en centièmes de pouce. NWS utilise round-half-up également.
    """
    if rounding == "nearest_int":
        # round half up, gère correctement les négatifs : -10.5 → -10, -10.6 → -11
        return float(math.floor(value + 0.5))
    if rounding == "nearest_0.01":
        # round half up à deux décimales
        return math.floor(value * 100 + 0.5) / 100.0
    return value


def would_resolve_yes(
    rule: ResolutionRule,
    observed_value: float,
    is_trace: bool = False,
) -> bool:
    """Verdict de résolution déterministe étant donné une observation.

    Args:
        rule: la règle extraite du market.
        observed_value: la valeur brute (ex. température en °F, précip en pouces).
        is_trace: True si l'observation NWS est codée "T" (Trace, pluie < 0.005").
    """
    # Convention pluie : Trace résout OUI si le seuil est 0
    if is_trace and rule.trace_is_yes:
        # uniquement quand le seuil est 0 — au-delà, "T" est < seuil et résout NO.
        seuil = rule.floor_strike if rule.strike_type == "greater" else rule.cap_strike
        if seuil is not None and seuil <= 0.0:
            return True
        return False

    rounded = apply_nws_rounding(observed_value, rule.rounding)

    if rule.strike_type == "less":
        # cap_strike défini : OUI si obs_arrondi < cap_strike
        if rule.cap_strike is None:
            return False
        return rounded < rule.cap_strike

    if rule.strike_type == "greater":
        # floor_strike défini : OUI si obs_arrondi > floor_strike
        if rule.floor_strike is None:
            return False
        return rounded > rule.floor_strike

    # between : OUI si floor <= obs_arrondi <= cap
    if rule.floor_strike is None or rule.cap_strike is None:
        return False
    return rule.floor_strike <= rounded <= rule.cap_strike


def near_threshold_margin(rule: ResolutionRule, observed_value: float) -> float:
    """Distance entre l'observation arrondie et le seuil le plus proche du verdict.

    Utile pour identifier les marchés "knife-edge" où l'arrondi NWS bascule le
    résultat — c'est là que l'edge est maximal pour qui modélise correctement
    l'arrondi.
    """
    rounded = apply_nws_rounding(observed_value, rule.rounding)
    candidates: list[float] = []
    if rule.cap_strike is not None:
        candidates.append(abs(rounded - rule.cap_strike))
    if rule.floor_strike is not None:
        candidates.append(abs(rounded - rule.floor_strike))
    return min(candidates) if candidates else float("inf")
