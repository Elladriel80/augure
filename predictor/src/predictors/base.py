"""Spécifications de contrats météo et interface Predictor."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Optional, Literal

from src.kalshi.models import Market


# Type de variable météo cible
WeatherVar = Literal[
    "temp_max",   # Température maximum journalière (°F)
    "temp_min",   # Température minimum journalière (°F)
    "precip_in",  # Précipitations cumulées (pouces)
    "snow_in",    # Chute de neige (pouces)
]


@dataclass
class ContractSpec:
    """Spec normalisée d'un contrat Kalshi : 'sur la variable V à la date D, est-ce que [lower ≤ V ≤ upper] ?'"""
    market_ticker: str
    event_ticker: str
    variable: WeatherVar
    location_key: str           # clé dans CITIES (ex: "AUSTIN")
    target_date: date           # jour observé pour résolution
    lower: Optional[float]      # borne inférieure inclusive, None = pas de borne
    upper: Optional[float]      # borne supérieure inclusive, None = pas de borne
    raw_subtitle: str

    def matches(self, value: float) -> bool:
        if self.lower is not None and value < self.lower:
            return False
        if self.upper is not None and value > self.upper:
            return False
        return True

    def describe(self) -> str:
        if self.lower is None:
            return f"{self.variable} <= {self.upper} @ {self.location_key} on {self.target_date}"
        if self.upper is None:
            return f"{self.variable} >= {self.lower} @ {self.location_key} on {self.target_date}"
        return f"{self.lower} <= {self.variable} <= {self.upper} @ {self.location_key} on {self.target_date}"


@dataclass
class Prediction:
    """Sortie d'un predictor pour un contrat."""
    contract: ContractSpec
    prob_yes: float                         # ∈ [0, 1]
    method: str                             # nom du predictor
    inputs: dict                            # données utilisées (pour audit)
    confidence: Optional[float] = None      # mesure de confiance (optionnelle)


class Predictor(ABC):
    """Interface abstraite : prend un contrat, renvoie une probabilité."""

    name: str = "base"

    @abstractmethod
    def predict(self, contract: ContractSpec) -> Prediction:
        ...

    def predict_market(self, market: Market) -> Optional[Prediction]:
        """Helper : parse le market puis prédit. Renvoie None si non parsable."""
        from .parsers import parse_market
        spec = parse_market(market)
        if spec is None:
            return None
        return self.predict(spec)
