> [Lire en français](README.fr.md)

# predictor

The prediction engine of Augure. Phase 1 is the **Kalshi POC** — validating that a meta-ensemble of weather models can produce a measurable predictive edge on the Kalshi temperature and rain markets.

## Status

Phase 1 — POC Kalshi *(active)*.

The code in this directory is being moved here from the previously private `kalshi-poc` repository. Until that move is complete (founder is uploading the existing modules), this directory contains only the README and a brief module map.

## Planned module layout

```
predictor/
├── src/
│   ├── kalshi/             ← REST client + NWS resolution rules
│   ├── weather/            ← Open-Meteo multi-model integration (forecast + ERA5)
│   ├── microstructure/     ← Kalshi market structure analysis (bins, vig, biases)
│   └── predictors/         ← climatology, forecast_blend, ensemble
├── scripts/
│   ├── forward_predict.py  ← daily prediction capture (anti-data-leakage)
│   ├── backtest.py         ← retroactive scoring (accuracy, Brier, log loss)
│   ├── audit_resolution.py ← NWS station mapping audit
│   └── analyze_microstructure.py
└── tests/
    ├── test_resolution.py        ← 9 asserts on NWS rounding, Trace, station codes
    ├── test_microstructure.py    ← 6 asserts on bin extraction and biases
    └── test_ensemble.py          ← live quick-check on the day's HIGH panel
```

## Strategy

Augure does not replicate mainstream LightGBM-on-NWP+climatology. The competitive landscape (Speedwell, Cumulus, Descartes) is mature on that approach. The predictor explores five less-trodden angles:

1. **Meta-ensemble of AI weather models** *(priority, in progress)* — combine GraphCast (DeepMind), Aurora (Microsoft), FourCastNet (Nvidia), Pangu (Huawei), GenCast, AIFS with ECMWF/GFS. Learn dynamically which model beats the others by region/season/event type.
2. **NWS administrative resolution edge** *(shipped)* — Kalshi resolution quirks (primary/backup station, rounding, post-publication corrections).
3. **Microstructure / behavioral biases on Kalshi** *(tested, hypothesis rejected)* — tail underpricing, recency bias, weekend illiquidity. Empirically measurable.
4. **Crowdsourced data + LLM reader** — PWS networks (Weather Underground, Netatmo), Twitter/X, traffic cams. LLM extracts signal as features.
5. **Soil moisture / MJO / stratospheric vortex** — long-horizon predictors underused on Kalshi.

## Stop criterion

If the predictive edge does not materialize on N>50 forward-tested events, the POC concludes honestly. Either the strategy pivots, or the project is buried cleanly. Information acquired is not failure — it is the deliverable.

## How to contribute to `predictor/`

See [`/CONTRIBUTING.md`](../CONTRIBUTING.md). In short: open PRs that add features, predictors, datasets, or tests. The valuation rubric will pick the appropriate profile (researcher quant for predictor logic, ML engineer for data integration, senior dev for infrastructure) based on the nature of your output.

Priority areas (high impact coefficient ×1.4–1.5):
- Phase A.2 : integrate Aurora / Pangu / FourCastNet / GenCast via HuggingFace + GPU cloud.
- Empirical validation of the ensemble vs best single model and vs climatology on N>50 events.
- Crowdsourced data layer (angle #4).
