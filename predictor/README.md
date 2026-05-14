# Aratea Weather Predictor — Kalshi POC

Moteur prédictif d'Aratea — testé en paper-trading sur les contrats Kalshi snow/rain, avant tout déploiement réel. Cette POC valide l'edge prédictif qui motive la suite du projet (DAO, mutuelle paramétrique).

## Objectif

Mesurer un **edge prédictif** sur des contrats météo Kalshi en mode simulation (aucun argent réel engagé).

Critère de succès : Brier score et accuracy meilleurs que les odds Kalshi closing, sur au moins une saison historique complète, sur au moins un type de contrat.

## Architecture

```
                         ┌─────────────────────┐
                         │  Kalshi Public API  │
                         │  (markets + odds)   │
                         └──────────┬──────────┘
                                    │
                                    ▼
   ┌──────────────┐         ┌──────────────┐         ┌──────────────┐
   │  Open-Meteo  │────────▶│   Predictor  │────────▶│  Simulation  │
   │  (forecast + │         │  (climato +  │         │   (ledger    │
   │  historical) │         │   ensemble)  │         │    CSV)      │
   └──────────────┘         └──────────────┘         └──────┬───────┘
                                                            │
                                                            ▼
                                                     ┌──────────────┐
                                                     │   Scoring    │
                                                     │  (Brier, ROI │
                                                     │   simulé)    │
                                                     └──────────────┘
```

**Étage 1 (en cours) :** baseline climatologique + ensemble forecast + paper trading.
**Étage 2 (plus tard) :** LLM en lecture de texte météo (NOAA discussions) → feature pour le predictor.

## Setup

```bash
# Depuis le dossier predictor/
python -m venv .venv
.venv\Scripts\activate   # Windows
.venv/bin/activate       # Linux / macOS

# Installation reproductible (recommandé) :
pip install -r requirements.lock --require-hashes

# Ou installation lâche (versions min seulement) :
pip install -r requirements.txt
```

**Reproductibilité des dépendances.** `requirements.lock` est généré par
[`pip-tools`](https://pip-tools.readthedocs.io/) à partir de
`requirements.txt`. Il épingle chaque dépendance transitive avec ses
hashs SHA-256, ce qui rend l'install reproductible et bloque la
substitution silencieuse d'un paquet vérolé.

Pour régénérer après une modification de `requirements.txt` :

```bash
pip install pip-tools
pip-compile --generate-hashes --output-file=predictor/requirements.lock predictor/requirements.txt
```

## Pipeline d'exécution

```bash
# 1. Récupérer les marchés météo Kalshi ouverts
python scripts/fetch_markets.py

# 2. Pour chaque marché, prédire P(OUI) avec la baseline climatologique
python scripts/predict.py --predictor climatology

# 3. Comparer aux prix marché et logger les paris simulés
python scripts/simulate.py

# 4. Une fois les marchés résolus, scorer les prédictions enregistrées
python scripts/score_forward.py
```

## Structure

```
kalshi-poc/
├── README.md
├── requirements.txt
├── src/
│   ├── kalshi/         # Client API Kalshi
│   ├── weather/        # Open-Meteo, NOAA
│   ├── predictors/     # climatology, ensemble, hybrid
│   └── simulation/     # paper trading + scoring
├── scripts/            # Entrypoints CLI
├── data/
│   ├── markets/        # Snapshots des marchés (JSON)
│   ├── forecasts/      # Prévisions cachées
│   └── ledger/         # Paris simulés (CSV)
└── notebooks/          # Exploration ad-hoc
```

## État actuel

- [ ] Bootstrap projet
- [ ] Client Kalshi (lecture publique)
- [ ] Fetcher Open-Meteo
- [ ] Predictor climatologique
- [ ] Simulateur paper-trading
- [ ] Scoreur de résolutions

## Ce qu'on NE fait PAS dans cette phase

Pas de smart contract, pas de DAO, pas de bot live, pas de produit de mutuelle, pas d'ouverture de compte Kalshi, pas d'argent réel. Tout vient APRÈS la preuve d'edge.
