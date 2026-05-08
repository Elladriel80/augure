"""Predictor climatologique : P(OUI) = fréquence historique sur N années à la même date du calendrier."""
from __future__ import annotations
from datetime import date, timedelta
from typing import Optional

from src.weather import OpenMeteoClient, CITIES
from src.weather.open_meteo import DailyObservation
from .base import ContractSpec, Prediction, Predictor


def _within_seasonal_window(d: date, target: date, window_days: int) -> bool:
    """True si d est dans une fenêtre de ±window_days autour du (mois, jour) cible,
    quelle que soit l'année."""
    # Distance circulaire en jours-de-l'année
    doy_d = d.timetuple().tm_yday
    doy_t = target.timetuple().tm_yday
    diff = abs(doy_d - doy_t)
    diff = min(diff, 366 - diff)
    return diff <= window_days


def _value_for_var(obs: DailyObservation, var: str) -> Optional[float]:
    """Extrait la valeur de la variable cible depuis une observation."""
    if var == "temp_max":
        return obs.temperature_max_f
    if var == "temp_min":
        return obs.temperature_min
    if var == "precip_in":
        return obs.precipitation_inches
    if var == "snow_in":
        return obs.snowfall_inches
    return None


class ClimatologyPredictor(Predictor):
    """Pour le contrat 'V dans [lower, upper] @ ville le jour D' :
    on regarde la même date calendrier (jour, mois) sur N années passées
    et on calcule la fraction d'observations où la condition était vraie.

    Avec lissage Laplace pour éviter les probas extrêmes 0 ou 1 sur petit échantillon.
    """

    name = "climatology"

    def __init__(
        self,
        weather_client: Optional[OpenMeteoClient] = None,
        years_back: int = 30,
        window_days: int = 3,           # fenêtre ±N jours autour de la date
        laplace_smoothing: float = 0.5,
    ):
        self.weather = weather_client or OpenMeteoClient()
        self.years_back = years_back
        self.window_days = window_days
        self.laplace = laplace_smoothing

    def predict(self, contract: ContractSpec) -> Prediction:
        city = CITIES.get(contract.location_key)
        if city is None:
            raise KeyError(f"Ville non mappée: {contract.location_key}")

        target = contract.target_date
        # Une seule requête multi-année : on récupère TOUT l'historique
        # de la première année passée à la dernière, puis on filtre par
        # fenêtre calendrier ±window_days autour de (mois, jour) cible.
        oldest_year = target.year - self.years_back
        most_recent = target.year - 1
        start = date(oldest_year, 1, 1)
        end = date(most_recent, 12, 31)
        try:
            all_obs = self.weather.historical_observations(
                city["lat"], city["lon"], start, end, timezone=city["tz"]
            )
        except Exception:
            all_obs = []

        # Filtre par fenêtre calendrier autour du (mois, jour) cible
        observations: list[DailyObservation] = []
        years_used = set()
        for obs in all_obs:
            if _within_seasonal_window(obs.date, target, self.window_days):
                observations.append(obs)
                years_used.add(obs.date.year)
        years_used = sorted(years_used)

        # Filtre les obs ayant une valeur exploitable et compte les "OUI"
        # Pour les variables température, on arrondit à l'entier (NWS publie en entier).
        n_total = 0
        n_yes = 0
        values = []
        is_temp = contract.variable in ("temp_max", "temp_min")
        for obs in observations:
            v = _value_for_var(obs, contract.variable)
            if v is None:
                continue
            n_total += 1
            values.append(v)
            v_test = round(v) if is_temp else v
            if contract.matches(v_test):
                n_yes += 1

        if n_total == 0:
            # Pas de données : on renvoie 0.5 avec confidence très basse
            return Prediction(
                contract=contract,
                prob_yes=0.5,
                method=self.name,
                inputs={"n_obs": 0, "years_used": years_used},
                confidence=0.0,
            )

        # Laplace smoothing
        prob = (n_yes + self.laplace) / (n_total + 2 * self.laplace)
        confidence = min(1.0, n_total / 60.0)  # ~30 ans × 3 jours = 90 obs max

        return Prediction(
            contract=contract,
            prob_yes=prob,
            method=self.name,
            inputs={
                "n_obs": n_total,
                "n_yes": n_yes,
                "years_used": years_used,
                "window_days": self.window_days,
                "value_min": min(values) if values else None,
                "value_max": max(values) if values else None,
                "value_mean": sum(values) / len(values) if values else None,
            },
            confidence=confidence,
        )
