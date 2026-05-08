"""Predictor hybride : prévision Open-Meteo (déterministe) + climatologie pour la dispersion."""
from __future__ import annotations
import math
from datetime import date
from typing import Optional

from src.weather import OpenMeteoClient, CITIES
from .base import ContractSpec, Prediction, Predictor
from .climatology import ClimatologyPredictor


def _normal_cdf(x: float) -> float:
    """CDF de la loi normale standard."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _prob_in_interval(mu: float, sigma: float, lower: Optional[float], upper: Optional[float]) -> float:
    """P(lower ≤ X ≤ upper) sous N(mu, sigma²)."""
    if sigma <= 0:
        # Cas dégénéré: variance nulle
        if lower is not None and mu < lower:
            return 0.0
        if upper is not None and mu > upper:
            return 0.0
        return 1.0
    p_lower = _normal_cdf((lower - mu) / sigma) if lower is not None else 0.0
    p_upper = _normal_cdf((upper - mu) / sigma) if upper is not None else 1.0
    return max(0.0, min(1.0, p_upper - p_lower))


class ForecastBlendPredictor(Predictor):
    """Combine prévision Open-Meteo (mu) + dispersion climatologique (sigma).

    Hypothèse : la valeur observée ~ N(forecast, sigma_climato²) où sigma_climato
    est l'écart-type des observations historiques sur la fenêtre saisonnière.
    Pondère ensuite avec la climatologie pure pour les horizons longs (où la
    prévision n'est plus fiable).
    """

    name = "forecast_blend"

    def __init__(
        self,
        weather_client: Optional[OpenMeteoClient] = None,
        years_back: int = 15,
        window_days: int = 5,
    ):
        self.weather = weather_client or OpenMeteoClient()
        self.years_back = years_back
        self.window_days = window_days
        self.climato = ClimatologyPredictor(self.weather, years_back, window_days)

    def predict(self, contract: ContractSpec) -> Prediction:
        city = CITIES.get(contract.location_key)
        if city is None:
            raise KeyError(f"Ville non mappée: {contract.location_key}")

        # 1) Climatologie (sigma + fallback)
        clim = self.climato.predict(contract)
        clim_inputs = clim.inputs
        # Sigma estimé depuis l'amplitude historique (proxy normal : ±2σ ≈ range)
        vmin = clim_inputs.get("value_min")
        vmax = clim_inputs.get("value_max")
        if vmin is not None and vmax is not None and vmax > vmin:
            sigma = max(1.0, (vmax - vmin) / 4.0)
        else:
            sigma = 5.0

        # 2) Forecast Open-Meteo pour la date cible
        today = date.today()
        days_ahead = (contract.target_date - today).days

        if days_ahead < 0 or days_ahead > 16:
            # Pas de prévision exploitable → on tombe sur la climatologie
            return Prediction(
                contract=contract,
                prob_yes=clim.prob_yes,
                method=self.name + "[climato_only]",
                inputs={"reason": "out_of_forecast_range", "days_ahead": days_ahead, **clim_inputs},
                confidence=clim.confidence,
            )

        try:
            fc = self.weather.forecast(
                city["lat"], city["lon"],
                days=min(16, max(1, days_ahead + 1)),
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

        daily = fc.get("daily", {})
        times = daily.get("time", [])
        try:
            idx = times.index(contract.target_date.isoformat())
        except ValueError:
            return Prediction(
                contract=contract,
                prob_yes=clim.prob_yes,
                method=self.name + "[climato_only]",
                inputs={"reason": "date_not_in_forecast", **clim_inputs},
                confidence=clim.confidence,
            )

        # Mu selon variable
        if contract.variable == "temp_max":
            mu = daily.get("temperature_2m_max", [None])[idx]
        elif contract.variable == "temp_min":
            mu = daily.get("temperature_2m_min", [None])[idx]
        elif contract.variable == "precip_in":
            mm = daily.get("precipitation_sum", [None])[idx]
            mu = mm / 25.4 if mm is not None else None
        elif contract.variable == "snow_in":
            cm = daily.get("snowfall_sum", [None])[idx]
            mu = cm / 2.54 if cm is not None else None
        else:
            mu = None

        if mu is None:
            return Prediction(
                contract=contract,
                prob_yes=clim.prob_yes,
                method=self.name + "[climato_only]",
                inputs={"reason": "forecast_value_missing", **clim_inputs},
                confidence=clim.confidence,
            )

        # 3) P(YES) sous N(mu, sigma) — élargit les bornes de ±0.5 pour
        # intégrer l'effet d'arrondi entier (variables température).
        is_temp = contract.variable in ("temp_max", "temp_min")
        eff_lower = (contract.lower - 0.5) if (is_temp and contract.lower is not None) else contract.lower
        eff_upper = (contract.upper + 0.5) if (is_temp and contract.upper is not None) else contract.upper
        p_forecast = _prob_in_interval(mu, sigma, eff_lower, eff_upper)

        # 4) Blend forecast/climato selon horizon : pondération exponentielle
        # 0 jour → 100% forecast, 14 jours → ~30% forecast
        blend_w = math.exp(-days_ahead / 8.0)  # à 8j on est à 1/e ≈ 37%
        prob = blend_w * p_forecast + (1 - blend_w) * clim.prob_yes

        return Prediction(
            contract=contract,
            prob_yes=prob,
            method=self.name,
            inputs={
                "forecast_mu": mu,
                "sigma_climato": sigma,
                "p_forecast": p_forecast,
                "p_climato": clim.prob_yes,
                "blend_weight_forecast": blend_w,
                "days_ahead": days_ahead,
                **{f"climato_{k}": v for k, v in clim_inputs.items()},
            },
            confidence=clim.confidence,
        )
