"""Configuration globale du POC."""
from pathlib import Path

# Racine du projet
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Dossiers de données
DATA_DIR = PROJECT_ROOT / "data"
MARKETS_DIR = DATA_DIR / "markets"
FORECASTS_DIR = DATA_DIR / "forecasts"
LEDGER_DIR = DATA_DIR / "ledger"

for d in (MARKETS_DIR, FORECASTS_DIR, LEDGER_DIR):
    d.mkdir(parents=True, exist_ok=True)

# Kalshi public API
KALSHI_API_BASE = "https://api.elections.kalshi.com/trade-api/v2"

# Categories météo qu'on cible (identifiants Kalshi)
WEATHER_SERIES_TICKERS = [
    # On les découvrira via fetch_markets.py
]

# User-Agent pour les appels API.
# Identifie le predictor auprès des upstreams (Open-Meteo, Kalshi,
# NWS NDFD) avec un nom et une URL contactable, comme demandé par les
# bonnes pratiques de chacun. NE PAS y inclure d'identifiants
# personnels — la chaîne ressort dans les logs serveur côté upstream.
USER_AGENT = "augure-predictor/0.1 (+https://github.com/Elladriel80/augure)"

# Paramètres de simulation
SIMULATION = {
    "min_edge_to_bet": 0.05,        # 5% de divergence minimum entre proba modèle et prix marché
    "kelly_fraction": 0.25,          # Kelly fractionnel: 25% du Kelly théorique
    "max_position_per_market": 0.05, # 5% du bankroll max par marché
    "starting_bankroll": 1000.0,     # USD virtuel
}
