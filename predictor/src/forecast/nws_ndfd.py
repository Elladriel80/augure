"""NWS NDFD forecast fetcher (api.weather.gov).

The National Weather Service publishes the official forecast that
ultimately becomes the resolution source for Kalshi weather markets
(via the Climatological Report Daily / CLI* products at each station).
A *forecast* from the same agency that issues the *truth* should be
the highest-value signal we can pull.

Endpoints (no auth, free):
  1. GET /points/{lat},{lng}  -> returns the per-cell `forecast` URL.
  2. GET <forecast URL>        -> returns 12-hour periods out 7 days.

Periods alternate daytime/night, named "Today", "Tonight", "Tuesday",
"Tuesday Night", etc.  Each carries `temperature` (int), `temperatureUnit`
("F" or "C"), `probabilityOfPrecipitation.value` (int 0-100 or null),
`startTime` (ISO with local tz offset).

Conventions of fetch_forecast(lat, lng, target_date):
  - target_date is a 'YYYY-MM-DD' string in the station's *local* date.
  - temp_max_f = daytime-period temperature for target_date.
  - temp_min_f = nighttime-period temperature whose *startTime* falls on
    target_date (which is the night that *follows* the daytime — this
    matches how Kalshi typically frames low/high for a calendar day).
  - precipitation_chance_pct = max of POP across the day+night periods
    of target_date (None if both null).
  - precipitation_amount_in = not in this endpoint, kept as None for now
    (would require the gridpoints endpoint with quantitativePrecipitation
    in mm — explicit follow-up).

Disk cache: predictor/data/forecasts/nws_ndfd/{lat}_{lng}_{target_date}.json
Throttle: 1 req/sec, exponential backoff on 429/503 (up to 4 retries).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Optional

import requests

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import DATA_DIR  # noqa: E402

CACHE_DIR = DATA_DIR / "forecasts" / "nws_ndfd"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

USER_AGENT = "Augure-Predictor/1.0 (+https://github.com/Elladriel80/augure)"
BASE = "https://api.weather.gov"
THROTTLE_SECONDS = 1.0
_last_call_at: float = 0.0


def _throttle() -> None:
    global _last_call_at
    delta = time.monotonic() - _last_call_at
    if delta < THROTTLE_SECONDS:
        time.sleep(THROTTLE_SECONDS - delta)
    _last_call_at = time.monotonic()


def _get(url: str, max_retries: int = 4) -> dict[str, Any]:
    """GET with throttle, retry on 429/503 (exp backoff), raise on 4xx else."""
    headers = {"User-Agent": USER_AGENT, "Accept": "application/geo+json"}
    backoff = 2.0
    last_err: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        _throttle()
        try:
            r = requests.get(url, headers=headers, timeout=20)
        except requests.RequestException as e:
            last_err = e
            if attempt == max_retries:
                raise
            time.sleep(backoff)
            backoff *= 2
            continue
        if r.status_code in (429, 503):
            if attempt == max_retries:
                r.raise_for_status()
            time.sleep(backoff)
            backoff *= 2
            continue
        r.raise_for_status()
        return r.json()
    if last_err:
        raise last_err
    raise RuntimeError(f"unreachable: GET {url}")


def _cache_path(lat: float, lng: float, target_date: str) -> Path:
    # 4-decimal precision is ~11m at the equator, fine for station-grade points
    return CACHE_DIR / f"{lat:.4f}_{lng:.4f}_{target_date}.json"


def _parse_periods(periods: list[dict], target_date: str) -> dict[str, Any]:
    """Pick the day/night periods that match target_date in their LOCAL start."""
    day = None
    night = None
    for p in periods:
        start = p.get("startTime", "")
        # startTime looks like "2026-05-12T06:00:00-04:00" — first 10 chars = local date
        local_date = start[:10]
        if local_date != target_date:
            continue
        if p.get("isDaytime"):
            if day is None:
                day = p
        else:
            if night is None:
                night = p

    def _to_f(p: Optional[dict]) -> Optional[float]:
        if p is None:
            return None
        t = p.get("temperature")
        unit = p.get("temperatureUnit") or "F"
        if t is None:
            return None
        t = float(t)
        if unit.upper() == "C":
            return t * 9.0 / 5.0 + 32.0
        return t

    def _pop(p: Optional[dict]) -> Optional[float]:
        if p is None:
            return None
        v = (p.get("probabilityOfPrecipitation") or {}).get("value")
        return float(v) if v is not None else None

    pops = [v for v in (_pop(day), _pop(night)) if v is not None]
    return {
        "temp_max_f": _to_f(day),
        "temp_min_f": _to_f(night),
        "precipitation_chance_pct": max(pops) if pops else None,
        "precipitation_amount_in": None,
        "matched_day_name": day.get("name") if day else None,
        "matched_night_name": night.get("name") if night else None,
    }


def fetch_forecast(lat: float, lng: float, target_date: str) -> dict[str, Any]:
    """Return the NWS NDFD forecast for (lat, lng) and a target local date.

    Cached on disk; second call for the same key reads JSON. The cache
    is intentionally per (lat, lng, target_date) and has no TTL — the
    truth at the moment we observed it is what we want frozen for
    backtests. Delete the file to force a refresh.

    Returns a dict:
      {
        "temp_max_f": float | None,
        "temp_min_f": float | None,
        "precipitation_chance_pct": float | None,
        "precipitation_amount_in": None,
        "matched_day_name": str | None,
        "matched_night_name": str | None,
        "source": "nws_ndfd",
        "fetched_at": "YYYY-MM-DDTHH:MM:SSZ",
        "forecast_url": "...",
      }
    """
    cache = _cache_path(lat, lng, target_date)
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))

    points = _get(f"{BASE}/points/{lat:.4f},{lng:.4f}")
    forecast_url = points.get("properties", {}).get("forecast")
    if not forecast_url:
        raise RuntimeError(f"NWS /points returned no forecast URL for {lat},{lng}")

    fc = _get(forecast_url)
    periods = fc.get("properties", {}).get("periods", [])

    parsed = _parse_periods(periods, target_date)
    parsed["source"] = "nws_ndfd"
    parsed["fetched_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    parsed["forecast_url"] = forecast_url

    cache.write_text(json.dumps(parsed, indent=2), encoding="utf-8")
    return parsed


if __name__ == "__main__":
    # Smoke test: NYC Central Park, tomorrow local.
    import datetime
    tgt = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    out = fetch_forecast(40.7794, -73.9692, tgt)
    print(json.dumps(out, indent=2))
