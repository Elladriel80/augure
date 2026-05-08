"""Fetchers de données météo (Open-Meteo, gratuit, sans clé API)."""
from .open_meteo import (
    OpenMeteoClient,
    CITIES,
    DailyObservation,
    DailyForecast,
    AVAILABLE_MODELS,
    DEFAULT_ENSEMBLE,
)

__all__ = [
    "OpenMeteoClient", "CITIES",
    "DailyObservation", "DailyForecast",
    "AVAILABLE_MODELS", "DEFAULT_ENSEMBLE",
]
