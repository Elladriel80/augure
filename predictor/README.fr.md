> [Read in English](README.md)

# predictor

Le moteur de prédiction d'Augure. La Phase 1 est le **POC Kalshi** — valider qu'un méta-ensemble de modèles météo peut produire un edge prédictif mesurable sur les marchés Kalshi température et pluie.

## Statut

Phase 1 — POC Kalshi *(actif)*.

Le code de ce dossier est en cours de migration depuis le repo privé `kalshi-poc`. Tant que la migration n'est pas terminée (le founder importe les modules existants), ce dossier contient seulement ce README et un plan d'arborescence.

## Arbo prévue

```
predictor/
├── src/
│   ├── kalshi/             ← client REST + règles de résolution NWS
│   ├── weather/            ← intégration multi-modèle Open-Meteo (forecast + ERA5)
│   ├── microstructure/     ← analyse structure marchés Kalshi (bins, vig, biais)
│   └── predictors/         ← climatologie, forecast_blend, ensemble
├── scripts/
│   ├── forward_predict.py  ← capture quotidienne des prédictions (anti-data-leakage)
│   ├── backtest.py         ← scoring rétroactif (accuracy, Brier, log loss)
│   ├── audit_resolution.py ← audit du mapping stations NWS
│   └── analyze_microstructure.py
└── tests/
    ├── test_resolution.py        ← 9 asserts sur arrondi NWS, Trace, codes stations
    ├── test_microstructure.py    ← 6 asserts sur extraction bins et biais
    └── test_ensemble.py          ← quick-check live sur le panel HIGH du jour
```

## Stratégie

Augure ne réplique PAS le mainstream LightGBM sur NWP+climato. La concurrence (Speedwell, Cumulus, Descartes) est mature sur cette approche. Le predictor explore cinq angles moins courus :

1. **Méta-ensemble de modèles IA météo** *(priorité, en cours)* — combiner GraphCast (DeepMind), Aurora (Microsoft), FourCastNet (Nvidia), Pangu (Huawei), GenCast, AIFS avec ECMWF/GFS. Apprendre dynamiquement quel modèle bat les autres par région/saison/type d'événement.
2. **Edge résolution administrative NWS** *(livré)* — bizarreries des règles Kalshi (station primary/backup, arrondis, corrections post-publication).
3. **Microstructure / biais comportementaux Kalshi** *(testé, hypothèse rejetée)* — tail underpricing, recency bias, weekend illiquidity. Mesurable empiriquement.
4. **Crowdsourced data + LLM lecteur** — PWS networks (Weather Underground, Netatmo), Twitter/X, traffic cams. LLM extrait du signal en features.
5. **Soil moisture / MJO / vortex stratosphérique** — long-horizon predictors sous-utilisés sur Kalshi.

## Critère d'arrêt

Si l'edge prédictif ne se matérialise pas sur N>50 events forward-testés, le POC conclut honnêtement. Soit pivot stratégique, soit on enterre proprement. L'information acquise n'est pas un échec — c'est le livrable.

## Contribuer à `predictor/`

Voir [`/CONTRIBUTING.fr.md`](../CONTRIBUTING.fr.md). En résumé : ouvre des PRs qui ajoutent features, predictors, datasets, ou tests. Le rubric de valuation choisira le profil adéquat (researcher quant pour la logique predictor, ML engineer pour l'intégration data, senior dev pour l'infrastructure) selon la nature de ton output.

Zones prioritaires (coefficient impact ×1,4-1,5) :
- Phase A.2 : intégration Aurora / Pangu / FourCastNet / GenCast via HuggingFace + GPU cloud.
- Validation empirique de l'ensemble vs best single model et vs climato sur N>50 events.
- Couche crowdsourced data (angle n°4).
