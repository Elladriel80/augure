"""Static geographic features per NWS station.

These features do not change day-to-day — they describe the *physical
context* of each weather station: how built-up around it, how much water
nearby, how high, how far from the coast, what latitude. They are
station-level constants joined to each market record via location_key.

Hypotheses being tested:
  - Urban areas trap nighttime warmth (urban heat island) → biases the
    relationship between forecast and observed lows.
  - Large water bodies dampen temperature extremes by thermal mass.
  - Forest cover shades the surface and increases evapotranspiration.
  - High elevation = thinner air, larger diurnal swing.
  - Distance to coast governs maritime vs continental regime.
  - Absolute latitude controls insolation and seasonal amplitude.

These are HYPOTHESES — the learned model will measure each one's actual
Brier contribution per training run.

Sources:
  - OSM Overpass API (free, throttled to 1 req / 2 sec).
  - USGS EPQS Elevation Point Query Service (free, no auth).
  - Natural Earth 1:50m coastline (downloaded once, gitignored).

Built once with:
  python predictor/src/learning/geographic.py --build

Output:  predictor/data/geographic/stations.json (committed — static).
"""
from __future__ import annotations

import json
import math
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import DATA_DIR  # noqa: E402
from src.kalshi.resolution import NWS_STATIONS  # noqa: E402

GEO_DIR = DATA_DIR / "geographic"
GEO_DIR.mkdir(parents=True, exist_ok=True)
STATIONS_JSON = GEO_DIR / "stations.json"
COASTLINE_GEOJSON = GEO_DIR / "ne_50m_coastline.geojson"
COASTLINE_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/"
    "geojson/ne_50m_coastline.geojson"
)

USER_AGENT = "Augure-Predictor/1.0 (+https://github.com/Elladriel80/augure)"

# Throttle for Overpass; the public instance asks for ~1 req every 2 sec.
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OVERPASS_THROTTLE = 2.0
_overpass_last_call = 0.0


def _http_get_json(url: str, max_retries: int = 4, timeout: int = 30) -> Any:
    """Plain stdlib JSON GET with backoff."""
    backoff = 2.0
    for attempt in range(max_retries + 1):
        req = urllib.request.Request(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and attempt < max_retries:
                time.sleep(backoff)
                backoff *= 2
                continue
            raise
        except urllib.error.URLError:
            if attempt < max_retries:
                time.sleep(backoff)
                backoff *= 2
                continue
            raise


def _overpass_post(query: str, max_retries: int = 4, timeout: int = 60) -> dict:
    """POST an Overpass QL query, with throttle and exp backoff."""
    global _overpass_last_call
    delta = time.monotonic() - _overpass_last_call
    if delta < OVERPASS_THROTTLE:
        time.sleep(OVERPASS_THROTTLE - delta)

    backoff = 4.0
    last_err: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        _overpass_last_call = time.monotonic()
        req = urllib.request.Request(
            OVERPASS_URL,
            data=query.encode("utf-8"),
            headers={
                "User-Agent": USER_AGENT,
                "Content-Type": "text/plain; charset=utf-8",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code in (429, 502, 503, 504) and attempt < max_retries:
                time.sleep(backoff)
                backoff *= 2
                continue
            raise
        except urllib.error.URLError as e:
            last_err = e
            if attempt < max_retries:
                time.sleep(backoff)
                backoff *= 2
                continue
            raise
    if last_err:
        raise last_err
    raise RuntimeError("unreachable")


def _overpass_count(lat: float, lon: float, radius_m: int, ql_filter: str) -> int:
    """Return the count of OSM ways/relations matching ql_filter in radius_m."""
    query = (
        '[out:json][timeout:60];'
        f'(\n'
        f'  way{ql_filter}(around:{radius_m},{lat:.6f},{lon:.6f});\n'
        f'  relation{ql_filter}(around:{radius_m},{lat:.6f},{lon:.6f});\n'
        f');\nout count;'
    )
    data = _overpass_post(query)
    # Overpass 'out count;' returns one element with tags ways/relations/total
    elems = data.get("elements", [])
    if not elems:
        return 0
    tags = elems[0].get("tags", {})
    try:
        return int(tags.get("total", 0))
    except (TypeError, ValueError):
        return 0


def _usgs_elevation_m(lat: float, lon: float) -> Optional[float]:
    """USGS EPQS — elevation in meters at a point. Returns None on failure."""
    url = (
        "https://epqs.nationalmap.gov/v1/json"
        f"?x={lon:.6f}&y={lat:.6f}&units=Meters&wkid=4326&includeDate=false"
    )
    try:
        data = _http_get_json(url)
    except Exception:
        return None
    # Schema: {"value": "12.34", ...} — sometimes a float, sometimes a string.
    v = data.get("value")
    if v is None:
        # Older field name fallback
        ue = data.get("USGS_Elevation_Point_Query_Service", {})
        v = (ue.get("Elevation_Query") or {}).get("Elevation")
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# ---------- Distance to coast (Natural Earth 50m) ----------

def _ensure_coastline() -> dict:
    """Download Natural Earth 50m coastline once, return parsed GeoJSON."""
    if not COASTLINE_GEOJSON.exists():
        print(f"  -> downloading Natural Earth coastline to {COASTLINE_GEOJSON}")
        req = urllib.request.Request(
            COASTLINE_URL, headers={"User-Agent": USER_AGENT}
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            COASTLINE_GEOJSON.write_bytes(r.read())
    return json.loads(COASTLINE_GEOJSON.read_text(encoding="utf-8"))


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = (math.sin(dphi / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(dl / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(a))


def _iter_coastline_points(geo: dict):
    """Yield (lon, lat) tuples for every vertex of every coastline LineString."""
    for feat in geo.get("features", []):
        geom = feat.get("geometry") or {}
        gtype = geom.get("type")
        coords = geom.get("coordinates") or []
        if gtype == "LineString":
            for lon, lat in coords:
                yield lon, lat
        elif gtype == "MultiLineString":
            for line in coords:
                for lon, lat in line:
                    yield lon, lat


def _distance_to_coast_km(lat: float, lon: float, geo: dict) -> float:
    """Min haversine distance to the nearest coastline vertex.

    50m resolution gives ~1-10 km positional error for points within a few
    hundred km of the coast — acceptable for a static contextual feature.
    For inland points (Denver, Oklahoma City) the absolute value matters
    less than the relative ordering across stations.
    """
    best = float("inf")
    for clon, clat in _iter_coastline_points(geo):
        d = _haversine_km(lat, lon, clat, clon)
        if d < best:
            best = d
    return best


# ---------- Build pipeline ----------

def build(stations: dict[str, Any] | None = None,
          overwrite: bool = False) -> dict[str, Any]:
    """Compute the 6 static features for every NWS station; write JSON.

    Keyed by ICAO (e.g. "KNYC"). Skipped if already present unless
    `overwrite=True`.
    """
    stations = stations if stations is not None else {
        icao: {"lat": s.lat, "lon": s.lon, "name": s.name}
        for s in NWS_STATIONS.values()
        for icao in (s.icao,)
    }
    existing: dict[str, Any] = {}
    if STATIONS_JSON.exists() and not overwrite:
        existing = json.loads(STATIONS_JSON.read_text(encoding="utf-8"))

    coastline = _ensure_coastline()

    out: dict[str, Any] = dict(existing)
    for icao, meta in stations.items():
        if icao in out and not overwrite:
            print(f"  [skip] {icao} (already in cache)")
            continue
        lat, lon = meta["lat"], meta["lon"]
        print(f"  [build] {icao} ({meta.get('name')}) at {lat},{lon}")
        try:
            urban = _overpass_count(lat, lon, 5_000, '["building"]')
            water = _overpass_count(
                lat, lon, 10_000,
                '["natural"="water"]'
            ) + _overpass_count(
                lat, lon, 10_000,
                '["waterway"]'
            )
            forest = _overpass_count(
                lat, lon, 5_000,
                '["natural"="wood"]'
            ) + _overpass_count(
                lat, lon, 5_000,
                '["landuse"="forest"]'
            )
        except Exception as e:
            print(f"    [warn] Overpass failure for {icao}: {e}")
            urban = water = forest = None

        elev = _usgs_elevation_m(lat, lon)
        try:
            dcoast = _distance_to_coast_km(lat, lon, coastline)
        except Exception as e:
            print(f"    [warn] coastline distance failure for {icao}: {e}")
            dcoast = None

        out[icao] = {
            "icao": icao,
            "name": meta.get("name"),
            "lat": lat,
            "lon": lon,
            "urban_density_5km": urban,
            "water_pct_10km": water,
            "forest_pct_5km": forest,
            "elevation_m": elev,
            "distance_to_coast_km": dcoast,
            "latitude": lat,
            "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        # Save after each station so a crash mid-loop doesn't lose progress.
        STATIONS_JSON.write_text(
            json.dumps(out, indent=2, sort_keys=True), encoding="utf-8"
        )
    return out


# ---------- Lookup for use by features.py ----------

# location_key (CITIES) -> station ICAO. Mirrors the de facto Kalshi
# resolution station for each city used in forward captures.
LOCATION_KEY_TO_ICAO: dict[str, str] = {
    "AUSTIN":        "KAUS",
    "BOSTON":        "KBOS",
    "CHICAGO":       "KORD",
    "DENVER":        "KDEN",
    "HOUSTON":       "KIAH",
    "LOSANGELES":    "KLAX",
    "MIAMI":         "KMIA",
    "NYC":           "KNYC",
    "PHILADELPHIA":  "KPHL",
    "SANANTONIO":    "KSAT",
    "SANFRANCISCO": "KSFO",
}


_loaded: Optional[dict[str, Any]] = None


def load() -> dict[str, Any]:
    """Lazy-load the geographic features JSON. Empty dict if not built."""
    global _loaded
    if _loaded is None:
        if STATIONS_JSON.exists():
            _loaded = json.loads(STATIONS_JSON.read_text(encoding="utf-8"))
        else:
            _loaded = {}
    return _loaded


def lookup_for_location_key(location_key: str) -> Optional[dict[str, Any]]:
    icao = LOCATION_KEY_TO_ICAO.get(location_key)
    if not icao:
        return None
    return load().get(icao)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--build", action="store_true",
                   help="Build/refresh stations.json")
    p.add_argument("--overwrite", action="store_true",
                   help="Recompute even stations already in cache.")
    p.add_argument("--icao", help="Only process this one ICAO (debugging).")
    args = p.parse_args()

    if args.build:
        if args.icao:
            s = next((v for v in NWS_STATIONS.values() if v.icao == args.icao),
                     None)
            if s is None:
                raise SystemExit(f"unknown ICAO {args.icao}")
            stations = {s.icao: {"lat": s.lat, "lon": s.lon, "name": s.name}}
        else:
            stations = {s.icao: {"lat": s.lat, "lon": s.lon, "name": s.name}
                        for s in NWS_STATIONS.values()}
        out = build(stations, overwrite=args.overwrite)
        print(f"\nwrote {STATIONS_JSON} with {len(out)} stations.")
    else:
        print("nothing to do. pass --build to compute and save.")
