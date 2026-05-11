"""Client Open-Meteo : prévisions et historique.

Open-Meteo est gratuit, sans clé API. Deux endpoints utilisés :
- /v1/forecast : prévisions ensemble GFS/ECMWF jusqu'à 16 jours
- archive-api/v1/archive : observations historiques (ERA5 reanalysis)
"""
from __future__ import annotations
import json
import re
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

import requests

from src.config import USER_AGENT, FORECASTS_DIR


# Whitelist for cache-key sanitisation. Anything outside this set is
# collapsed to an underscore so a future caller passing a key sourced
# from untrusted input (e.g. a Kalshi ticker, a CLI arg) cannot escape
# the cache directory via "../", "C:\\", a NUL byte, or platform-specific
# separators.
_CACHE_KEY_SAFE_RE = re.compile(r"[^A-Za-z0-9._-]")


# Stations Kalshi mappées vers (lat, lon, timezone, station officielle)
# Les coordonnées correspondent aux stations NWS référencées dans les rules Kalshi.
CITIES: dict[str, dict] = {
    "AUSTIN":       {"lat": 30.1945, "lon": -97.6699, "tz": "America/Chicago",  "label": "Austin Bergstrom"},
    "BOSTON":       {"lat": 42.3656, "lon": -71.0096, "tz": "America/New_York", "label": "Boston Logan"},
    "CHICAGO":      {"lat": 41.9803, "lon": -87.9090, "tz": "America/Chicago",  "label": "Chicago O'Hare"},
    "DENVER":       {"lat": 39.8561, "lon": -104.6737, "tz": "America/Denver",  "label": "Denver International"},
    "HOUSTON":      {"lat": 29.9844, "lon": -95.3414, "tz": "America/Chicago",  "label": "Houston Intercontinental"},
    "LOSANGELES":   {"lat": 33.9416, "lon": -118.4085, "tz": "America/Los_Angeles", "label": "LAX"},
    "MIAMI":        {"lat": 25.7959, "lon": -80.2870,  "tz": "America/New_York", "label": "Miami International"},
    "NYC":          {"lat": 40.6413, "lon": -73.7781,  "tz": "America/New_York", "label": "JFK Airport"},
    "PHILADELPHIA": {"lat": 39.8729, "lon": -75.2437,  "tz": "America/New_York", "label": "Philadelphia International"},
    "SANANTONIO":   {"lat": 29.5337, "lon": -98.4698,  "tz": "America/Chicago",  "label": "San Antonio International"},
    "SANFRANCISCO": {"lat": 37.6189, "lon": -122.3750, "tz": "America/Los_Angeles", "label": "SFO"},
}


@dataclass
class DailyObservation:
    """Une observation journalière d'une station."""
    date: date
    temperature_max: Optional[float]    # °F
    temperature_min: Optional[float]    # °F
    precipitation_sum: Optional[float]  # mm
    snowfall_sum: Optional[float]       # cm
    raw: dict

    @property
    def temperature_max_f(self) -> Optional[float]:
        return self.temperature_max

    @property
    def precipitation_inches(self) -> Optional[float]:
        return self.precipitation_sum / 25.4 if self.precipitation_sum is not None else None

    @property
    def snowfall_inches(self) -> Optional[float]:
        return self.snowfall_sum / 2.54 if self.snowfall_sum is not None else None


@dataclass
class DailyForecast:
    """Une prévision journalière issue d'UN modèle météo."""
    model: str
    date: date
    temperature_max_f: Optional[float]
    temperature_min_f: Optional[float]
    precipitation_sum_mm: Optional[float]
    rain_sum_mm: Optional[float]
    snowfall_sum_cm: Optional[float]

    @property
    def precipitation_inches(self) -> Optional[float]:
        if self.precipitation_sum_mm is None:
            return None
        return self.precipitation_sum_mm / 25.4

    @property
    def rain_inches(self) -> Optional[float]:
        if self.rain_sum_mm is None:
            return None
        return self.rain_sum_mm / 25.4

    @property
    def snowfall_inches(self) -> Optional[float]:
        if self.snowfall_sum_cm is None:
            return None
        return self.snowfall_sum_cm / 2.54


# Modèles Open-Meteo testés et confirmés disponibles (mai 2026).
# Mix de baselines numériques et de modèles IA — c'est le panel Phase A.1.
AVAILABLE_MODELS: dict[str, dict] = {
    "ecmwf_ifs025":           {"family": "numerical", "origin": "ECMWF",      "label": "ECMWF IFS"},
    "ecmwf_aifs025_single":   {"family": "ai",        "origin": "ECMWF",      "label": "ECMWF AIFS (AI)"},
    "gfs_graphcast025":       {"family": "ai",        "origin": "DeepMind",   "label": "Google GraphCast (AI)"},
    "gfs_global":             {"family": "numerical", "origin": "NOAA",       "label": "NOAA GFS"},
    "jma_gsm":                {"family": "numerical", "origin": "JMA",        "label": "JMA GSM"},
}

DEFAULT_ENSEMBLE = list(AVAILABLE_MODELS.keys())


class OpenMeteoClient:
    """Client minimaliste Open-Meteo (forecast + archive)."""

    FORECAST_BASE = "https://api.open-meteo.com/v1/forecast"
    ARCHIVE_BASE = "https://archive-api.open-meteo.com/v1/archive"

    def __init__(self, cache_dir: Path = FORECASTS_DIR):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # -- HTTP --

    # Maximum total time we are willing to spend on retries+sleeps for
    # a single _get call. Picks up runaway loops where 429s come back
    # back-to-back with a `Retry-After: 60`. Keeps the daily run bounded.
    _RETRY_BUDGET_SECONDS = 90
    # Cap any single Retry-After at this many seconds. Some upstreams
    # advise multi-minute sleeps; we'd rather bail out and re-run later.
    _RETRY_AFTER_CAP_SECONDS = 30

    def _get(self, base: str, params: dict) -> dict:
        url = f"{base}?{urlencode(params)}"
        budget_start = time.monotonic()
        last_exc: Optional[BaseException] = None
        for attempt in range(3):
            try:
                r = self.session.get(url, timeout=30)
                if r.status_code == 429:
                    # Respect Retry-After when the server provides it;
                    # fall back to exponential backoff otherwise. Cap
                    # the wait + check the global budget so a hostile
                    # or buggy header can't stall the pipeline.
                    sleep_for = self._parse_retry_after(r) or (2 ** attempt)
                    sleep_for = min(sleep_for, self._RETRY_AFTER_CAP_SECONDS)
                    if (time.monotonic() - budget_start) + sleep_for > self._RETRY_BUDGET_SECONDS:
                        raise requests.HTTPError(
                            f"open-meteo rate-limit budget exhausted "
                            f"after {time.monotonic() - budget_start:.1f}s "
                            f"(Retry-After suggested {sleep_for}s)"
                        )
                    time.sleep(sleep_for)
                    continue
                r.raise_for_status()
                return r.json()
            except requests.RequestException as exc:
                last_exc = exc
                if attempt == 2:
                    raise
                sleep_for = 1 + attempt
                if (time.monotonic() - budget_start) + sleep_for > self._RETRY_BUDGET_SECONDS:
                    raise
                time.sleep(sleep_for)
        if last_exc is not None:  # pragma: no cover — defensive
            raise last_exc
        return {}

    @staticmethod
    def _parse_retry_after(resp: requests.Response) -> Optional[float]:
        """Read a `Retry-After` header. Returns None if absent/invalid."""
        raw = resp.headers.get("Retry-After")
        if not raw:
            return None
        try:
            return max(0.0, float(raw))
        except ValueError:
            return None

    # -- Forecast --

    def forecast(
        self,
        lat: float,
        lon: float,
        days: int = 14,
        timezone: str = "auto",
        use_cache: bool = True,
    ) -> dict:
        """Récupère la prévision déterministe (multi-modèle best-of) pour les N prochains jours.

        Cache valide pour la session (clé par jour + lat/lon + days). Pour rafraîchir,
        supprime data/forecasts/forecast__*.json.
        """
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": ",".join([
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_sum",
                "rain_sum",
                "snowfall_sum",
                "precipitation_probability_max",
            ]),
            "temperature_unit": "fahrenheit",
            "precipitation_unit": "mm",
            "timezone": timezone,
            "forecast_days": days,
        }
        if use_cache:
            today = date.today().isoformat()
            key = f"{lat:.4f}_{lon:.4f}_d{days}_{today}"
            return self.cached_or_fetch(
                "forecast", key,
                lambda: self._get(self.FORECAST_BASE, params),
            )
        return self._get(self.FORECAST_BASE, params)

    def forecast_ensemble(
        self,
        lat: float,
        lon: float,
        days: int = 14,
        timezone: str = "auto",
    ) -> dict:
        """Récupère TOUS les membres de l'ensemble GFS pour avoir une distribution.

        On utilise l'API ensemble (GFS GEFS 31 membres). Plus utile que le forecast
        déterministe pour estimer P(événement).
        """
        params = {
            "latitude": lat,
            "longitude": lon,
            "models": "gfs_seamless,ecmwf_ifs025",
            "hourly": "temperature_2m,precipitation,snowfall",
            "temperature_unit": "fahrenheit",
            "precipitation_unit": "mm",
            "timezone": timezone,
            "forecast_days": days,
        }
        return self._get(self.FORECAST_BASE, params)

    def forecast_multi_model(
        self,
        lat: float,
        lon: float,
        models: Optional[list[str]] = None,
        days: int = 7,
        timezone: str = "auto",
        use_cache: bool = True,
    ) -> dict[str, list[DailyForecast]]:
        """Requête plusieurs modèles en un seul appel et retourne {model: [DailyForecast]}.

        Open-Meteo, quand on passe ``models=a,b,c``, suffixe chaque variable par
        ``_<model>`` dans la réponse. On parse ça en un dict propre.

        Args:
            models: liste de modèles parmi AVAILABLE_MODELS. Defaut = ensemble complet.
            days: horizon en jours.

        Note : tous les modèles ne couvrent pas toutes les variables (ex. GraphCast
        ne fournit pas snow). Les valeurs absentes sont None — c'est au caller
        de gérer.
        """
        models = models or DEFAULT_ENSEMBLE
        unknown = [m for m in models if m not in AVAILABLE_MODELS]
        if unknown:
            raise ValueError(f"Modèles inconnus : {unknown}. Voir AVAILABLE_MODELS.")

        params = {
            "latitude": lat,
            "longitude": lon,
            "models": ",".join(models),
            "daily": ",".join([
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_sum",
                "rain_sum",
                "snowfall_sum",
            ]),
            "temperature_unit": "fahrenheit",
            "precipitation_unit": "mm",
            "timezone": timezone,
            "forecast_days": days,
        }

        if use_cache:
            today = date.today().isoformat()
            key = f"multi_{lat:.4f}_{lon:.4f}_d{days}_{today}_{'-'.join(sorted(models))}"
            data = self.cached_or_fetch(
                "forecast_multi", key,
                lambda: self._get(self.FORECAST_BASE, params),
            )
        else:
            data = self._get(self.FORECAST_BASE, params)

        return _parse_multi_model_daily(data, models)

    # -- Historique --

    def historical(
        self,
        lat: float,
        lon: float,
        start_date: date,
        end_date: date,
        timezone: str = "auto",
        use_cache: bool = True,
    ) -> dict:
        """Observations historiques journalières (ERA5 reanalysis).

        Cache disque : par défaut, la même requête (lat, lon, dates) ne sera
        appelée qu'une fois. Utile car la climato sur 15 ans pour la même
        ville est invariable.
        """
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "daily": ",".join([
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_sum",
                "rain_sum",
                "snowfall_sum",
            ]),
            "temperature_unit": "fahrenheit",
            "precipitation_unit": "mm",
            "timezone": timezone,
        }
        if use_cache:
            key = f"{lat:.4f}_{lon:.4f}_{start_date.isoformat()}_{end_date.isoformat()}"
            return self.cached_or_fetch(
                "historical", key,
                lambda: self._get(self.ARCHIVE_BASE, params),
            )
        return self._get(self.ARCHIVE_BASE, params)

    def historical_observations(
        self,
        lat: float,
        lon: float,
        start_date: date,
        end_date: date,
        timezone: str = "auto",
    ) -> list[DailyObservation]:
        """Wrapper qui parse historical() en liste typée."""
        data = self.historical(lat, lon, start_date, end_date, timezone)
        daily = data.get("daily", {})
        dates = daily.get("time", [])
        out = []
        for i, d in enumerate(dates):
            out.append(DailyObservation(
                date=date.fromisoformat(d),
                temperature_max=_get_at(daily, "temperature_2m_max", i),
                temperature_min=_get_at(daily, "temperature_2m_min", i),
                precipitation_sum=_get_at(daily, "precipitation_sum", i),
                snowfall_sum=_get_at(daily, "snowfall_sum", i),
                raw={k: _get_at(daily, k, i) for k in daily.keys() if k != "time"},
            ))
        return out

    # -- Cache --

    def cache_path(self, kind: str, key: str) -> Path:
        # SECURITY: collapse anything outside [A-Za-z0-9._-] to underscore
        # (covers "..", "/", "\\", drive letters, NUL bytes, control
        # chars). Then resolve the candidate and reject it if it escapes
        # `self.cache_dir`. Today `key` is internal-derived (lat/lon/
        # dates) but the guard is cheap and protects future callers.
        safe_kind = _CACHE_KEY_SAFE_RE.sub("_", kind)
        safe_key = _CACHE_KEY_SAFE_RE.sub("_", key)
        cache_root = self.cache_dir.resolve()
        candidate = (cache_root / f"{safe_kind}__{safe_key}.json").resolve()
        try:
            candidate.relative_to(cache_root)
        except ValueError as exc:
            raise ValueError(
                f"cache_path escape attempt for kind={kind!r} key={key!r}"
            ) from exc
        return candidate

    def cached_or_fetch(self, kind: str, key: str, fetcher) -> dict:
        """Lecture/écriture cache disque, avec garde-fou anti-cache-vide.

        Refuse d'écrire un cache si la réponse n'a pas de série temporelle
        utilisable — ça évite le piège où une réponse Open-Meteo vide
        (rate limit, erreur silencieuse, coords mal acceptées) est gelée
        définitivement et fait retourner 0 observations à chaque appel
        suivant. Si le fichier en cache est lui-même vide on le réécrit.
        """
        path = self.cache_path(kind, key)
        if path.exists():
            try:
                cached = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                cached = {}
            if _has_usable_series(cached):
                return cached
            # Cache vide / corrompu : on l'efface et on refetch
            try:
                path.unlink()
            except OSError:
                pass
        data = fetcher()
        if _has_usable_series(data):
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data


def _get_at(d: dict, key: str, i: int):
    arr = d.get(key)
    if arr is None or i >= len(arr):
        return None
    return arr[i]


def _parse_multi_model_daily(data: dict, models: list[str]) -> dict[str, list[DailyForecast]]:
    """Parse la réponse Open-Meteo multi-modèles en {model: [DailyForecast]}.

    Format de la réponse : daily.temperature_2m_max_<model>, etc.
    """
    daily = data.get("daily", {}) or {}
    dates = daily.get("time", []) or []

    out: dict[str, list[DailyForecast]] = {}
    for model in models:
        forecasts: list[DailyForecast] = []
        tmax_arr = daily.get(f"temperature_2m_max_{model}") or []
        tmin_arr = daily.get(f"temperature_2m_min_{model}") or []
        prcp_arr = daily.get(f"precipitation_sum_{model}") or []
        rain_arr = daily.get(f"rain_sum_{model}") or []
        snow_arr = daily.get(f"snowfall_sum_{model}") or []
        for i, d in enumerate(dates):
            forecasts.append(DailyForecast(
                model=model,
                date=date.fromisoformat(d),
                temperature_max_f=_arr_at(tmax_arr, i),
                temperature_min_f=_arr_at(tmin_arr, i),
                precipitation_sum_mm=_arr_at(prcp_arr, i),
                rain_sum_mm=_arr_at(rain_arr, i),
                snowfall_sum_cm=_arr_at(snow_arr, i),
            ))
        out[model] = forecasts
    return out


def _arr_at(arr, i: int):
    if arr is None or i >= len(arr):
        return None
    return arr[i]


def _has_usable_series(data: dict) -> bool:
    """True si la réponse Open-Meteo contient au moins une série temporelle non-vide.

    On vérifie à la fois `daily.time` et `hourly.time` pour couvrir tous les
    endpoints (forecast, archive, multi-model). Une réponse sans temps =
    cache pourri à ne pas écrire.
    """
    if not isinstance(data, dict):
        return False
    daily = data.get("daily") or {}
    hourly = data.get("hourly") or {}
    if isinstance(daily, dict) and daily.get("time"):
        return True
    if isinstance(hourly, dict) and hourly.get("time"):
        return True
    return False


def get_city(name: str) -> dict:
    """Lookup case-insensitive d'une ville par nom court (NYC, BOSTON, etc.)."""
    key = name.upper()
    if key not in CITIES:
        raise KeyError(f"Ville inconnue: {name}. Disponibles: {list(CITIES)}")
    return CITIES[key]
