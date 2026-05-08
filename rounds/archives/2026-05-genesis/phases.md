# Genesis round — phase decomposition

*Round identifier : `2026-05-genesis`*
*Source repo (pre-open-source) : `kalshi-poc` (private)*
*Decomposition date : 2026-05-08*

## Méthode

Le repo `kalshi-poc` n'a pas d'historique de PRs (travail solo, commits directs sur `main`). La décomposition logique se fait sur la base des **modules livrés et fonctionnels** observables dans le code source et l'arborescence de tests. Chaque phase regroupe un ensemble cohérent de fichiers, dépendances et tests qui forment une livraison fonctionnelle indépendante.

Cette décomposition est l'input unique de l'agent de valuation pour le round genesis. Elle est figée par cette PR pour être reproductible.

---

## Phase 0 — Setup, design et stratégie

**Artefacts observables**
- Structure du repo, environnement Python 3.13, dépendances (requests, lightgbm-ready)
- Document de stratégie identifiant 5 angles d'edge possibles : méta-ensemble IA, edge résolution NWS, microstructure Kalshi, crowdsourced data + LLM, soil moisture / MJO / vortex stratosphérique
- Décision motivée de NE PAS répliquer LightGBM mainstream (concurrence Speedwell, Cumulus, Descartes)
- Critères d'arrêt explicites en cas d'absence d'edge

**Profil dominant** : researcher quant (choix méthodologiques) + senior dev (setup technique)

---

## Phase 1 — Client Kalshi (lecture publique)

**Artefacts observables**
- Module client API Kalshi (lecture publique, sans auth)
- Récupération markets, séries temporelles bid/ask, snapshots
- Module : `src/kalshi/` (fonctions de base avant `resolution.py`)

**Profil dominant** : senior dev backend

---

## Phase 2 — Intégration Open-Meteo (forecast + ERA5)

**Artefacts observables**
- Module `src/weather/open_meteo.py` (version initiale)
- Forecast multi-jour + accès historique ERA5
- Mécanisme de cache pour éviter requêtes redondantes
- Dataclass `DailyForecast`

**Profil dominant** : ML/data engineer

---

## Phase 3 — Predictors core (climatologie + forecast_blend)

**Artefacts observables**
- Predictor climatologie pure (baseline, distribution historique par jour calendaire)
- Predictor `forecast_blend` (blending climato + NWP avec horizon decay)
- Modules : `src/predictors/climatology.py`, `src/predictors/forecast_blend.py`

**Profil dominant** : researcher quant

---

## Phase 4 — Simulateur + paper-trading + ledger

**Artefacts observables**
- Simulateur de paper-trading sur données Kalshi
- Ledger des trades simulés (positions, P&L)
- Module : `src/simulate.py` (avec bug initial divide by 200, corrigé en Phase A.1-bugfix)

**Profil dominant** : senior dev backend

---

## Phase 5 — Backtest scoring infrastructure

**Artefacts observables**
- Calcul accuracy top-1, Brier score, log loss
- Brier skill score vs baseline climato
- Module : `scripts/backtest.py` (version initiale)

**Profil dominant** : ML engineer

**Premier résultat baseline empirique** : climato pure sur 16 events Austin → top-1 31%, Brier skill score -0.21. Confirme la nécessité de NWP+ML.

---

## Phase B-1 — Résolution administrative NWS

**Artefacts observables**
- `src/kalshi/resolution.py` : catalogue de **18 stations NWS** (CLI codes + ICAO + lat/lon/wfo)
- Extraction règle depuis `cap_strike` / `floor_strike` / `strike_type`
- Arrondi NWS *round half up* (75.5 → 76)
- Convention Trace = OUI pour rain seuil 0
- `scripts/audit_resolution.py` : scan tous les snapshots, rapport stations + cas-limites
- `scripts/test_resolution.py` : **9 tests asserts** sur Austin / NYC / Chicago / Rain / Trace
- Insight clé : Kalshi 'TLV' = Las Vegas (CLILAS) pas Tel Aviv ; Chicago Rain mensuel = Midway (CLIMDW) pas O'Hare

**Profil dominant** : researcher quant (domain knowledge NWS station mapping)

---

## Phase B-2 — Analyse microstructure Kalshi

**Artefacts observables**
- `src/microstructure/distribution.py` : extraction bins ordonnés, vig (somme YES_mid), distribution implicite normalisée, mean/std implicites
- `src/microstructure/biases.py` : `event_biases()` produisant vig_residual, spread médian, skew (extrême - central), modal_oi_share, tail_mass + `tail_underpricing_vs_climato()`
- `scripts/analyze_microstructure.py` : rapport texte + JSON par event
- `scripts/test_microstructure.py` : **6 tests** sur Austin (6 bins) + Rain NYC (singleton)

**Profil dominant** : researcher quant

**Résultat empirique** : sur audit 32 events temp mutex, vig moyenne payée au mid = +0,16 % (Kalshi très efficient). 29/32 events ont des bins extrêmes plus serrés que le centre — **hypothèse "tail underpricing structurel" rejetée**. Conclusion actionnable : ne pas bâtir une stratégie de "ramassage du vig sur les extrêmes". L'edge doit venir de la prédiction, pas de la microstructure pure.

---

## Phase A.1 — Méta-ensemble IA (version frugale Open-Meteo)

**Artefacts observables**
- Extension `src/weather/open_meteo.py` : `forecast_multi_model()`, `AVAILABLE_MODELS`, `DEFAULT_ENSEMBLE`
- 5 modèles confirmés disponibles via API gratuite Open-Meteo : `ecmwf_ifs025` (numérique), `ecmwf_aifs025_single` (IA ECMWF), `gfs_graphcast025` (DeepMind), `gfs_global` (NOAA), `jma_gsm` (JMA)
- `src/predictors/ensemble.py` : `EnsemblePredictor` (mode uniform + hook poids), `sigma_total = quadrature(sigma_inter_models, 0.5 × sigma_climato)`, blend horizon `~exp(-d/8)`
- `scripts/test_ensemble.py` : quick-check live sur panel HIGH du jour
- `scripts/forward_predict.py` : capture quotidienne des prédictions des 3 predictors (climato, forecast_blend, ensemble) pour scoring sans data leakage
- `scripts/backtest.py` : option `--predictor ensemble` ajoutée

**Test live observable** : Austin 26MAY09 → spread inter-modèles 25,3 / 25,7 / 25,8 / 27,4 / 30,3 °C, soit 5 °C de désaccord — terrain de jeu réel pour l'ensemble.

**Profils dominants** (décomposition) :
- ML/data engineer (extension multi-modèle, ~6h)
- Researcher quant (logique d'ensemble, propagation sigma, ~10h)
- Senior dev (forward-predict, backtest CLI, ~8h)

---

## Phase A.1-bugfix — Stabilisation runtime

**Artefacts observables**
- Garde-fou `_has_usable_series()` ajouté dans `cached_or_fetch` (cache Open-Meteo écrivait silencieusement les réponses vides → "0 obs cachés à vie")
- `Market.from_api()` : auto-détection format `yes_bid_dollars`/`yes_ask_dollars` (string décimal) vs `yes_bid`/`yes_ask` (cents int legacy), normalisation en floats [0.0, 1.0]
- `simulate.py` : correction division par 200 (ancien cents → dollars) en /2.0

**Profil dominant** : senior dev

**Pourquoi compté en phase distincte** : ces fixes ont émergé en runtime après le code initial. Cohérent avec la règle rubric d'attribuer un coefficient qualité explicite (positif ici parce que régressions fixées avec tests).

---

## Hors-scope du round genesis

Les artefacts suivants sont produits par JS mais NE rentrent PAS dans cette valuation kalshi-poc :

- Conception du modèle de tokens AUG-POC (docs `token_model_augure_poc.md`, `value_engine.md`).
- Création du repo public `augure-rounds` (RUBRIC, HOURLY_RATES, PROMPT bilingues, scripts).

Ces artefacts pourront faire l'objet d'un round séparé `2026-05-augure-rounds-genesis`, ou être intégrés au premier round mensuel régulier après ouverture du projet.
