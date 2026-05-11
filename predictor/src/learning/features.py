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
"""
from __future__ import annotations

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

# V1, V2 etc. will be defined here as we validate new features.
# Example pattern for the future:
#
#   FEATURES_V1 = FEATURES_V0 + [
#       ("kalshi_mid", f_kalshi_mid),
#   ]


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
