"""EnsemblePredictor — combine plusieurs modèles Open-Meteo (numériques + IA).

Phase A.1.2. Logique :
1. Requête N modèles en un appel (forecast_multi_model).
2. mu = moyenne (uniform ou pondérée par perf historique récente) des modèles.
3. sigma_inter = std des prévisions des modèles (= proxy d'incertitude epistémique).
4. sigma_total = sqrt(sigma_inter² + sigma_climato²) — combine désaccord modèles
   et variabilité climatique résiduelle.
5. P(YES) sous N(mu, sigma_total²) avec correction d'arrondi NWS.

L'idée centrale : quand les modèles convergent (sigma_inter ≈ 0), on est confiant
et la prédiction est piquée. Quand ils divergent (jour orageux, transition de masse
d'air), sigma_inter explose, P(YES) se rapproche de 0.5 — exactement ce qu'on veut.

L'edge potentiel vs Kalshi : le marché tend à pricer un point unique. L'ensemble
tient compte du fait qu'au-delà de J+5, GFS et ECMWF peuvent diverger de 5°C.
"""
from __future__ import annotations

import math
import statistics
from datetime import date
from typing import Optional

from src.weather import (
    OpenMeteoClient,
    CITIES,
    DEFAULT_ENSEMBLE,
    AVAILABLE_MODELS,
)
from src.weather.open_meteo import DailyForecast
from .base import ContractSpec, Prediction, Predictor
from .climatology import ClimatologyPredictor


def _normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _prob_in_interval(mu: float, sigma: float, lower: Optional[float], upper: Optional[float]) -> float:
    if sigma <= 0:
        if lower is not None and mu < lower:
            return 0.0
        if upper is not None and mu > upper:
            return 0.0
        return 1.0
    p_lower = _normal_cdf((lower - mu) / sigma) if lower is not None else 0.0
    p_upper = _normal_cdf((upper - mu) / sigma) if upper is not None else 1.0
    return max(0.0, min(1.0, p_upper - p_lower))


def _value_for_var(fc: DailyForecast, var: str) -> Optional[float]:
    if var == "temp_max":
        return fc.temperature_max_f
    if var == "temp_min":
        return fc.temperature_min_f
    if var == "precip_in":
        return fc.precipitation_inches
    if var == "snow_in":
        return fc.snowfall_inches
    return None


class EnsemblePredictor(Predictor):
    """Combine N modèles Open-Meteo + dispersion climato. Mode uniform par défaut."""

    name = "ensemble"

    def __init__(
        self,
        weather_client: Optional[OpenMeteoClient] = None,
        models: Optional[list[str]] = None,
        years_back: int = 15,
        window_days: int = 5,
        weights: Optional[dict[str, float]] = None,  # None = uniform
        max_horizon_days: int = 10,
    ):
        self.weather = weather_client or OpenMeteoClient()
        self.models = models or DEFAULT_ENSEMBLE
        self.weights = weights
        self.climato = ClimatologyPredictor(self.weather, years_back, window_days)
        self.max_horizon = max_horizon_days

        unknown = [m for m in self.models if m not in AVAILABLE_MODELS]
        if unknown:
            raise ValueError(f"Modèles inconnus : {unknown}")

    def _model_weights(self) -> dict[str, float]:
        if self.weights:
            total = sum(self.weights.get(m, 0.0) for m in self.models)
            if total <= 0:
                # fallback uniforme si poids invalides
                return {m: 1.0 / len(self.models) for m in self.models}
            return {m: self.weights.get(m, 0.0) / total for m in self.models}
        return {m: 1.0 / len(self.models) for m in self.models}

    def predict(self, contract: ContractSpec) -> Prediction:
        city = CITIES.get(contract.location_key)
        if city is None:
            raise KeyError(f"Ville non mappée: {contract.location_key}")

        # Climatologie pour sigma + fallback
        clim = self.climato.predict(contract)
        clim_inputs = clim.inputs
        vmin = clim_inputs.get("value_min")
        vmax = clim_inputs.get("value_max")
        sigma_climato = (
            max(1.0, (vmax - vmin) / 4.0)
            if (vmin is not None and vmax is not None and vmax > vmin)
            else 5.0
        )

        today = date.today()
        days_ahead = (contract.target_date - today).days
        if days_ahead < 0 or days_ahead > self.max_horizon:
            return Prediction(
                contract=contract,
                prob_yes=clim.prob_yes,
                method=self.name + "[climato_only]",
                inputs={
                    "reason": "out_of_horizon",
                    "days_ahead": days_ahead,
                    **clim_inputs,
                },
                confidence=clim.confidence,
            )

        try:
            multi = self.weather.forecast_multi_model(
                city["lat"], city["lon"],
                models=self.models,
                days=min(self.max_horizon, max(1, days_ahead + 1)),
                timezone=city["tz"],
            )
        except Exception as e:
            return Prediction(
                contract=contract,
                prob_yes=clim.prob_yes,
                method=self.name + "[climato_only]",
                inputs={"reason": f"forecast_error: {e}", **clim_inputs},
                confidence=clim.confidence,
            )

        # Récupère la valeur de la variable pour la date cible, par modèle
        per_model_value: dict[str, float] = {}
        for model, forecasts in multi.items():
            for fc in forecasts:
                if fc.date == contract.target_date:
                    v = _value_for_var(fc, contract.variable)
                    if v is not None:
                        per_model_value[model] = v
                    break

        if not per_model_value:
            return Prediction(
                contract=contract,
                prob_yes=clim.prob_yes,
                method=self.name + "[climato_only]",
                inputs={"reason": "no_model_returned_value", **clim_inputs},
                confidence=clim.confidence,
            )

        weights = self._model_weights()
        # mu pondéré (uniquement sur modèles ayant retourné une valeur)
        active_w_total = sum(weights[m] for m in per_model_value)
        if active_w_total <= 0:
            mu = statistics.fmean(per_model_value.values())
        else:
            mu = sum(per_model_value[m] * weights[m] for m in per_model_value) / active_w_total

        # sigma_inter = écart-type des modèles (epistémique)
        if len(per_model_value) >= 2:
            sigma_inter = statistics.pstdev(per_model_value.values())
        else:
            sigma_inter = 0.0

        # Combinaison quadratique : la variance totale = epistémique + résiduelle climato
        # On ne reprend qu'une fraction de sigma_climato (les modèles capturent déjà
        # une grande partie de la dynamique journalière).
        sigma_total = math.sqrt(sigma_inter ** 2 + (0.5 * sigma_climato) ** 2)

        # Correction d'arrondi NWS : pour les températures, élargit l'intervalle
        # de ±0.5°F (l'arrondi entier capture les valeurs entre n-0.5 et n+0.5).
        is_temp = contract.variable in ("temp_max", "temp_min")
        eff_lower = (contract.lower - 0.5) if (is_temp and contract.lower is not None) else contract.lower
        eff_upper = (contract.upper + 0.5) if (is_temp and contract.upper is not None) else contract.upper
        p_forecast = _prob_in_interval(mu, sigma_total, eff_lower, eff_upper)

        # Blend horizon : à J+0 on fait 100% modèles ; à J+max on bascule vers climato
        blend_w = math.exp(-days_ahead / 8.0)
        prob = blend_w * p_forecast + (1 - blend_w) * clim.prob_yes

        return Prediction(
            contract=contract,
            prob_yes=prob,
            method=self.name,
            inputs={
                "per_model_value": per_model_value,
                "weights": {m: weights[m] for m in per_model_value},
                "mu": mu,
                "sigma_inter_models": sigma_inter,
                "sigma_climato": sigma_climato,
                "sigma_total": sigma_total,
                "p_forecast": p_forecast,
                "p_climato": clim.prob_yes,
                "blend_weight_forecast": blend_w,
                "days_ahead": days_ahead,
                "n_models_active": len(per_model_value),
                **{f"climato_{k}": v for k, v in clim_inputs.items()},
            },
            confidence=clim.confidence,
        )
