"""Feature extraction for the learned predictor.

A feature extractor is a pure function from a forward-capture record
(`predictor/data/predictions/forward_*.json` entry, with `predictions`
dict, `yes_mid`, etc.) to a dict of named numeric features.

Each feature is a separate function so we can easily ADD/DROP features
during the iterative feature engineering loop and track each one's
contribution to model accuracy.

The current registered feature set is exposed as FEATURES_V0 (the
starter set) and incremented to FEATURES_V1, V2, etc. as we validate
new features empirically.

Naming discipline: every feature name MUST evoke an atmospheric or
contextual hypothesis. No f1, f2, x_42 — use names like p_nws_ndfd,
urban_density_5km, forecast_revision_velocity_24h. The catalog of all
features (with hypothesis, source, status, measured Brier delta) lives
in FEATURES.md next to this file.
"""
from __future__ import annotations

import datetime as _dt
import math
from typing import Any, Callable


# ---------- Individual feature extractors ----------

def f_p_climatology(rec: dict[str, Any]) -> float | None:
    """The climatology predictor's P(YES)."""
    return _get_pred(rec, "climatology")


def f_p_forecast_blend(rec: dict[str, Any]) -> float | None:
    """The forecast_blend predictor's P(YES)."""
    return _get_pred(rec, "forecast_blend")


def f_p_ensemble(rec: dict[str, Any]) -> float | None:
    """The meta-ensemble predictor's P(YES)."""
    return _get_pred(rec, "ensemble")


def f_forecast_spread(rec: dict[str, Any]) -> float | None:
    """Spread (max - min) across the per-vendor forecast probabilities.

    Looks inside `predictions.ensemble.inputs.individual_probs` (or
    similar) if available. If not, fall back to abs(blend - climatology)
    as a crude proxy of disagreement.
    """
    ens = rec.get("predictions", {}).get("ensemble", {})
    inputs = ens.get("inputs", {}) if isinstance(ens, dict) else {}
    indiv = inputs.get("individual_probs") or inputs.get("per_model_probs")
    if isinstance(indiv, dict) and indiv:
        vals = [float(v) for v in indiv.values() if v is not None]
        if vals:
            return max(vals) - min(vals)
    # Fallback proxy
    blend = f_p_forecast_blend(rec)
    clim = f_p_climatology(rec)
    if blend is None or clim is None:
        return None
    return abs(blend - clim)


def f_days_ahead(rec: dict[str, Any]) -> float | None:
    """How far ahead (in days) the forecast is — 0 = same day, 7 = a week out.

    Looks first in predictions.forecast_blend.inputs.days_ahead, then
    derives from target_date vs snapshot_at if not present.
    """
    fb = rec.get("predictions", {}).get("forecast_blend", {})
    inputs = fb.get("inputs", {}) if isinstance(fb, dict) else {}
    if "days_ahead" in inputs and inputs["days_ahead"] is not None:
        return float(inputs["days_ahead"])
    # Derive from dates if possible
    target = rec.get("target_date")
    snap = rec.get("snapshot_at") or rec.get("_capture_at")
    if target and snap:
        try:
            from datetime import datetime
            t = datetime.strptime(target, "%Y-%m-%d").date()
            # snap is like "20260508T104500Z"
            s = datetime.strptime(snap[:8], "%Y%m%d").date()
            return float((t - s).days)
        except Exception:
            return None
    return None


# ---------- V1 feature: NWS NDFD vendor forecast ----------

def _normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _prob_in_interval(mu: float, sigma: float,
                       lower: float | None, upper: float | None) -> float:
    if sigma <= 0:
        if lower is not None and mu < lower:
            return 0.0
        if upper is not None and mu > upper:
            return 0.0
        return 1.0
    p_lo = _normal_cdf((lower - mu) / sigma) if lower is not None else 0.0
    p_hi = _normal_cdf((upper - mu) / sigma) if upper is not None else 1.0
    return max(0.0, min(1.0, p_hi - p_lo))


def _sigma_from_climato(rec: dict[str, Any]) -> float | None:
    """Estimate sigma the same way ForecastBlendPredictor does: range/4."""
    clim = rec.get("predictions", {}).get("climatology", {})
    inputs = clim.get("inputs", {}) if isinstance(clim, dict) else {}
    vmin, vmax = inputs.get("value_min"), inputs.get("value_max")
    if vmin is None or vmax is None or vmax <= vmin:
        # forecast_blend inputs sometimes carry sigma_climato directly
        fb = rec.get("predictions", {}).get("forecast_blend", {})
        fb_inputs = fb.get("inputs", {}) if isinstance(fb, dict) else {}
        sc = fb_inputs.get("sigma_climato")
        if sc is not None:
            return float(sc)
        return None
    return max(1.0, (float(vmax) - float(vmin)) / 4.0)


def f_p_nws_ndfd(rec: dict[str, Any]) -> float | None:
    """P(YES) computed from the NWS NDFD official forecast.

    Hypothesis: Kalshi weather markets resolve on the NWS Climatological
    Report. A forecast from the same agency that issues the truth should
    dominate generic vendor blends.

    NDFD is forward-only (no historical archives), so for any record with
    target_date < today this returns None and the row is dropped. The
    feature gains coverage as forward captures accumulate going forward.
    """
    target = rec.get("target_date")
    variable = rec.get("variable")
    lower, upper = rec.get("lower"), rec.get("upper")
    location_key = rec.get("location_key")
    if not (target and variable and location_key):
        return None

    # NDFD only covers ~7 days forward. Skip everything outside that window
    # to avoid wasted requests and confusing cache pollution.
    try:
        t = _dt.date.fromisoformat(target)
    except Exception:
        return None
    today = _dt.date.today()
    days_ahead = (t - today).days
    if days_ahead < 0 or days_ahead > 6:
        return None

    # Resolve station coordinates from the project's CITIES table.
    try:
        from src.weather import CITIES  # local import to keep import graph shallow
    except Exception:
        return None
    city = CITIES.get(location_key)
    if not city:
        return None

    # Variable to NDFD field.
    try:
        from src.forecast.nws_ndfd import fetch_forecast
    except Exception:
        return None
    try:
        fc = fetch_forecast(city["lat"], city["lon"], target)
    except Exception:
        return None

    if variable == "temp_max":
        mu = fc.get("temp_max_f")
    elif variable == "temp_min":
        mu = fc.get("temp_min_f")
    elif variable == "precip_in":
        # precipitation_amount_in not yet available from NDFD periods endpoint
        return None
    elif variable == "snow_in":
        return None
    else:
        return None

    if mu is None:
        return None

    sigma = _sigma_from_climato(rec)
    if sigma is None:
        return None

    # Same integer-rounding correction as forecast_blend for temperature bounds.
    is_temp = variable in ("temp_max", "temp_min")
    eff_lower = (lower - 0.5) if (is_temp and lower is not None) else lower
    eff_upper = (upper + 0.5) if (is_temp and upper is not None) else upper
    return _prob_in_interval(float(mu), float(sigma), eff_lower, eff_upper)


# ---------- Registry ----------

# A feature spec is (name, extractor_fn). Order matters for the model's
# coefficient inspection.

FEATURES_V0: list[tuple[str, Callable[[dict[str, Any]], float | None]]] = [
    ("p_climatology",   f_p_climatology),
    ("p_forecast_blend", f_p_forecast_blend),
    ("p_ensemble",       f_p_ensemble),
    ("forecast_spread",  f_forecast_spread),
    ("days_ahead",       f_days_ahead),
]

# V1: adds NWS NDFD vendor probability. Note that p_nws_ndfd is None on
# rows whose target_date is in the past — historical captures predate the
# NDFD integration. V1's effective row count will be very small until
# daily forward captures start carrying NDFD natively.
FEATURES_V1: list[tuple[str, Callable[[dict[str, Any]], float | None]]] = (
    FEATURES_V0 + [
        ("p_nws_ndfd", f_p_nws_ndfd),
    ]
)


# ---------- V2 features: static geographic context per station ----------

def _geo_value(rec: dict[str, Any], key: str) -> float | None:
    """Look up a static geographic value for the record's location_key.

    Returns None if the station hasn't been built into stations.json yet
    or if the value is missing — so the row is dropped instead of
    silently zero-imputed.
    """
    loc = rec.get("location_key")
    if not loc:
        return None
    try:
        from src.learning.geographic import lookup_for_location_key
    except Exception:
        return None
    s = lookup_for_location_key(loc)
    if not s:
        return None
    v = s.get(key)
    return float(v) if v is not None else None


def f_urban_density_5km(rec: dict[str, Any]) -> float | None:
    """OSM building feature count within 5 km of the station.

    Proxy for the urban heat island. Dense urban cores retain nighttime
    warmth and bias the low-temperature distribution upward vs. the
    climatology built from older / less built-up neighbouring stations.
    Count rather than %-area because computing %-area would require
    polygon geometry parsing (shapely) which is out of scope here.
    """
    return _geo_value(rec, "urban_density_5km")


def f_water_pct_10km(rec: dict[str, Any]) -> float | None:
    """Count of OSM water features (natural=water + waterway) within 10 km.

    Proxy for water-thermal-mass dampening of diurnal swings. Stations
    near large water bodies should see narrower temp ranges. Naming
    keeps the V2 "_pct_" suffix from the spec for continuity but the
    units are counts; see FEATURES.md.
    """
    return _geo_value(rec, "water_pct_10km")


def f_forest_pct_5km(rec: dict[str, Any]) -> float | None:
    """Count of OSM forest patches (natural=wood + landuse=forest) within 5 km.

    Proxy for surface shading and evapotranspiration. Forest cover
    cools daytime highs (shade + evap) and limits radiative night
    cooling (canopy traps).
    """
    return _geo_value(rec, "forest_pct_5km")


def f_elevation_m(rec: dict[str, Any]) -> float | None:
    """USGS elevation in meters at the station point.

    Thinner air at high altitude amplifies the diurnal swing — bigger
    daily max-min spread, larger sensitivity to insolation. Denver vs.
    Miami sits at opposite ends of this axis.
    """
    return _geo_value(rec, "elevation_m")


def f_distance_to_coast_km(rec: dict[str, Any]) -> float | None:
    """Haversine distance in km to the nearest Natural Earth 50m coastline vertex.

    Continental stations (Denver, Oklahoma City) see big seasonal swings
    and weak inertia; maritime stations (Boston, Miami) carry far more
    thermal mass from the adjacent ocean and have damped extremes.
    """
    return _geo_value(rec, "distance_to_coast_km")


def f_latitude(rec: dict[str, Any]) -> float | None:
    """Station absolute latitude.

    Controls insolation, daylight length, seasonal amplitude. Trivial
    feature but worth including explicitly so the model can learn the
    season-vs-latitude interaction without us baking it into climatology.
    """
    return _geo_value(rec, "latitude")


# V2: V0 baseline + the 6 static geographic context features.
# p_nws_ndfd is intentionally *not* in V2: NDFD has no historical archive,
# so adding it forces every old row to drop and the training set vanishes.
# It gets its own training pass (--feature-set v1) once forward captures
# accumulate NDFD readings.
FEATURES_V2: list[tuple[str, Callable[[dict[str, Any]], float | None]]] = (
    FEATURES_V0 + [
        ("urban_density_5km",     f_urban_density_5km),
        ("water_pct_10km",        f_water_pct_10km),
        ("forest_pct_5km",        f_forest_pct_5km),
        ("elevation_m",           f_elevation_m),
        ("distance_to_coast_km",  f_distance_to_coast_km),
        ("latitude",              f_latitude),
    ]
)


# Convenience map for --feature-set CLI flag.
FEATURE_SETS: dict[str, list[tuple[str, Callable[[dict[str, Any]], float | None]]]] = {
    "v0": FEATURES_V0,
    "v1": FEATURES_V1,
    "v2": FEATURES_V2,
}


# ---------- Helpers ----------

def _get_pred(rec: dict[str, Any], predictor_name: str) -> float | None:
    pred = rec.get("predictions", {}).get(predictor_name, {})
    p = pred.get("prob_yes") if isinstance(pred, dict) else None
    return float(p) if p is not None else None


def extract(rec: dict[str, Any],
            spec: list[tuple[str, Callable]]) -> dict[str, float] | None:
    """Run all extractors against `rec`. Returns None if any feature is
    missing (so the row is dropped from training rather than silently
    imputed with 0/mean)."""
    out: dict[str, float] = {}
    for name, fn in spec:
        v = fn(rec)
        if v is None:
            return None
        out[name] = v
    return out
