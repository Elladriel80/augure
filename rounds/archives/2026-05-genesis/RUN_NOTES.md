# RUN_NOTES — round `2026-05-genesis`

*Notes méthodologiques du run réel daté 2026-05-08.*

## Contexte

Ce round genesis a tourné en **deux passes** :

1. **Dry-run** (avant migration de `kalshi-poc` vers `predictor/`) — basé sur les descriptions de la mémoire projet, sans accès direct au code source. Documenté dans `DRY_RUN_NOTES.md`. Total : 0,273 BTC.
2. **Run réel** (après migration) — l'agent de valuation lit directement les 32 fichiers Python du dossier `predictor/` et applique le rubric. Documenté ici. Total : 0,340 BTC.

Le run réel est **canonique** pour la ratification. Le dry-run est conservé en archive comme calibration de référence et pour traçabilité du processus.

## Méthode du run réel

L'agent de valuation a procédé en 4 étapes :

1. **Énumération** des fichiers via Glob (`**/*.py` dans `predictor/`).
2. **Lecture batch** de 24 fichiers source représentatifs : `src/config.py`, `src/kalshi/{client,models,resolution}.py`, `src/predictors/{base,parsers,climatology,forecast_blend,ensemble}.py`, `src/microstructure/{distribution,biases}.py`, `src/simulation/{sizing,ledger,scoring}.py`, `src/weather/open_meteo.py`, `scripts/{test_resolution,test_microstructure,test_ensemble,forward_predict,score_forward,backtest,daily_run}.py`.
3. **Décomposition** en 11 phases logiques (cf. `phases.md` mis à jour avec arborescence réelle).
4. **Application du rubric** : pour chaque phase, estimation des heures depuis le diff (LoC ajustées par complexité/structure), choix du profil selon nature de l'output, ajustements qualité (tests présents, doc, error handling) et impact (rôle dans le roadmap).

Les fichiers `predict.py`, `simulate.py`, `fetch_markets.py`, `fetch_forecast.py`, `audit_resolution.py`, `analyze_microstructure.py` n'ont **pas été lus individuellement** par l'agent — ils ont été pris en compte indirectement via leur taille (estimation par module parent). Si JS souhaite raffiner la valuation, lecture directe possible et amendement de la PR de ratification ouvrable.

## Évolution vs dry-run — ce qui a bougé

| Phase | Dry-run (sats) | Real run (sats) | Δ | Pourquoi |
|---|---:|---:|---:|---|
| 0. Setup, design | 1 080 000 | 1 080 000 | 0 | Identique |
| 1. Kalshi client | 2 293 200 | 3 088 800 | +35 % | Models.py inclut le dual-format prix (qualité +) ; estimation heures +4h (260 lignes) |
| 2. Open-Meteo | 3 880 800 | 4 989 600 | +29 % | open_meteo.py 420L vs estimation initiale plus modeste ; estimation +6h |
| 3. Predictors core | 2 956 800 | 4 857 600 | +64 % | 4 fichiers / 508L vs 2 fichiers initialement comptabilisés ; estimation +8h |
| 4. Simulation | 2 184 000 | 1 638 000 | -25 % | Code livré plus modeste que mémoire (133L au total) ; estimation -4h |
| 5. Backtest | 1 131 900 | 1 355 200 | +20 % | backtest.py 176L avec garde-fou anti-leakage explicite ; ML profile au lieu de mix |
| B-1. NWS resolution | 4 492 800 | 5 491 200 | +22 % | 394L de qualité documentaire élevée ; estimation +4h ; coef qualité +0,05 |
| B-2. Microstructure | 2 576 000 | 3 312 000 | +29 % | 307L (distribution + biases) avec 6 tests ; estimation +4h |
| A.1. Méta-ensemble | 5 359 200 | 6 252 400 | +17 % | Scripts forward_predict + score_forward substantiels ; estimation senior dev +2h |
| A.1-bf. Bugfix | 1 345 500 | 1 345 500 | 0 | Identique |
| DR. Daily run | 0 | 629 200 | NEW | Phase nouvelle, n'avait pas été comptabilisée au dry-run |
| **Total** | **27 299 400** | **34 039 500** | **+24,7 %** | Dans la zone d'incertitude ±20-25 % flaggée |

## Garde-fous appliqués

- Bornes dures qualité [0,5 ; 1,3] et impact [0,8 ; 1,5] respectées sur toutes les phases.
- Aucun bonus "founder", "loyalty" ou "early-mover" appliqué — conforme RUBRIC §2.
- Travail rétroactif : fenêtre de challenge **30 jours** au lieu de 7 (RUBRIC §10).
- Dilution "valuation > 0,01 BTC" : @Elladriel80 atteint 0,34 BTC, ce qui en dehors du contexte genesis aurait déclenché un vote panel automatique. À ce stade pas de panel — la fenêtre 30 jours sert de substitut.

## Décisions opérationnelles laissées à JS

1. **Ratification du run réel** : si JS valide les chiffres, on ouvre la fenêtre de challenge 30 jours par PR sur le repo augure. Sinon, JS amende les coefficients par phase et le ratificateur (lui-même en phase 1) merge.
2. **Round séparé pour augure-rounds + docs** : le travail de méta-design (RUBRIC, PROMPT, value engine, README monorepo, structure rounds/contracts/docs) n'est PAS dans cette valuation. À traiter dans un round séparé `2026-05-augure-rounds-genesis` ou agréger dans le round régulier `2026-06`. JS tranche.
3. **Travail invisible** : R&D exploratoire, lectures de papers, debug par expérimentation. Non capté par le rubric fact-only. JS peut accepter ce trade-off (cap-table un peu sous-estimée mais système objectif) ou ouvrir un mécanisme complémentaire (mais qui sortirait du fact-only — à éviter).
4. **Audit des fichiers non lus** : `predict.py`, `simulate.py`, `fetch_markets.py`, `fetch_forecast.py`, `audit_resolution.py`, `analyze_microstructure.py` n'ont pas été lus directement. Si JS estime que l'un de ces fichiers contient une masse de travail substantielle non-comptabilisée, l'agent peut les lire et amender.

## Points de friction par rapport au RUBRIC

- **README.md du repo (`predictor/README.md`)** : il est listé en Phase 0 mais reflète l'état initial du POC (mention "MyOwly", checklist "Bootstrap projet" non cochée alors que tout est fait). Il aurait gagné à être mis à jour mais ne l'est pas — coefficient qualité Phase 0 reste à ×1,00 conformément au constat factuel du fichier.
- **Tests** : pas de framework standard (pytest, unittest) — juste des asserts dans des fonctions `test_*` exécutées séquentiellement. Le coefficient qualité reflète la qualité des tests présents (docstrings explicatives, cas-limites, snapshots disque réels), pas l'absence de framework. JS peut considérer une migration pytest comme un travail futur valorisable.
- **Type hints** : présents sur la plupart des modules (Literal, Optional, dataclasses) mais pas exhaustifs. Coefficient qualité moyen ×1,10 cohérent.

## Statut

- [x] Dry-run produit (basé sur mémoire)
- [x] kalshi-poc importé dans `predictor/`
- [x] Run réel produit (basé sur lecture directe)
- [ ] Validation founder (JS)
- [ ] Commit + push de l'archive run sur GitHub
- [ ] Ouverture de la fenêtre de challenge 30 jours
- [ ] Décision sur le round séparé augure-rounds genesis
- [ ] Ratification finale et premier mint multisig (Phase 2 du repo, smart contract requis OU mint manuel via Safe en intermédiaire)
