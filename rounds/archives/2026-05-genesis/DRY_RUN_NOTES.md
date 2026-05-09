# DRY_RUN_NOTES — round `2026-05-genesis` *(SUPERSEDED)*

> **Ce document est le compte-rendu du dry-run initial fait avant la migration de `kalshi-poc` dans `augure/predictor/`.**
>
> **Il a été remplacé par `RUN_NOTES.md` (méthode du run réel) et le `valuation_report.md` actuel reflète désormais le run réel — total 0,34040 BTC vs 0,27299 BTC du dry-run.**
>
> Conservé pour traçabilité du processus et calibration de référence. Ne pas utiliser pour la ratification.

---

## Pourquoi c'était un dry-run

1. **Pas d'accès direct à `kalshi-poc`** au moment du run. L'agent de valuation avait travaillé sur la base des descriptions consolidées dans la mémoire projet (`project_kalshi_poc.md`), pas sur les artefacts Git réels.
2. **Pas de pipeline GitHub Actions.** Le script `collect_github_activity.py` était un squelette ; il n'a pas tourné pour produire `raw.json`.
3. **Pas de panel Top-X holders.** Supply = 0 → pas de holders.

## Ce que ce dry-run a apporté

- **Calibration du système** : ordres de grandeur, ratios entre phases, choix d'ajustements qualité/impact comme référence pour les rounds suivants.
- **Test du prompt et du rubric** : exposer des cas concrets (résultat négatif Phase B-2, bugfix avec qualité positive Phase A.1-bugfix, décomposition multi-profils Phase A.1) a montré comment l'agent appliquait les règles avant le run réel. Aucune décision n'a divergé matériellement entre dry-run et run réel — les coefficients étaient correctement calibrés.
- **Première cap-table de référence** : le total dry-run (0,273 BTC) s'est révélé sous-estimé de ~25 % par rapport au run réel (0,340 BTC), dans la zone d'incertitude ±20-25 % explicitement flaggée.

## Évolution vers le run réel

Le run réel (cf. `RUN_NOTES.md`) a apporté :

- Lecture directe de 24 fichiers source `.py` du dossier `predictor/`.
- Découverte de fichiers / modules non comptabilisés au dry-run :
  - `predictors/parsers.py` (143 lignes)
  - `predictors/base.py` (73 lignes)
  - `simulation/sizing.py`, `simulation/ledger.py` séparés (133 lignes au total — moins que mémoire suggérait)
  - `scripts/daily_run.py` orchestrateur (84 lignes — phase nouvelle)
- Confirmation de la qualité supérieure de `kalshi/resolution.py` (394 lignes vs estimation initiale) → coefficient qualité Phase B-1 durci de ×1,15 à ×1,20.
- Confirmation de la sophistication de `weather/open_meteo.py` (420 lignes) → estimation Phase 2 +6h.

## Décision

Le **run réel est la valuation canonique**. Ce DRY_RUN reste en archive uniquement pour traçabilité méthodologique.
