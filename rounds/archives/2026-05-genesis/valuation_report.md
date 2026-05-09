# Valuation report — round `2026-05-genesis` (REAL RUN)

*Date : 2026-05-08*
*Source : décomposition `phases.md` + lecture directe des fichiers source dans `augure/predictor/`*
*Agent de valuation : application directe du prompt versionné `rounds/agent/PROMPT.fr.md` v0.2*
*Statut : **RUN RÉEL** — basé sur les artefacts Git effectivement présents dans `augure/predictor/`. Le DRY_RUN_NOTES.md précédent a été conservé pour traçabilité de la méthode.*

---

## @Elladriel80

### Artefacts évalués

#### [Phase 0] Setup, design et stratégie

- **Artefacts** : `predictor/README.md` (92L), `predictor/requirements.txt` (5 deps), `predictor/src/config.py` (33L) ; document de stratégie 5 angles d'edge ; décision motivée NE PAS répliquer LightGBM mainstream
- **Heures estimées** : 6h (4h researcher + 2h senior dev)
- **Profils retenus** : 4h researcher quant (160 000 sats/h) + 2h senior dev (130 000 sats/h)
- **Justification heures** : document de stratégie identifiant 5 angles d'edge mesurés contre la concurrence ≈ 4h ; setup repo + environnement + dépendances + config minimaliste ≈ 2h pour un dev senior familier de la stack.
- **Ajustement qualité** : ×1,00 (baseline, pas de signal explicite)
- **Ajustement impact** : ×1,20 (oriente l'ensemble du roadmap, choix de NE PAS faire LightGBM mainstream est actionnable et différenciant)
- **Valeur** : (4 × 160 000) + (2 × 130 000) = 900 000 sats avant ajustement → 900 000 × 1,00 × 1,20 = **1 080 000 sats**

#### [Phase 1] Client Kalshi (lecture publique)

- **Artefacts** : `kalshi/client.py` (128L) + `kalshi/models.py` (132L). Total 260 lignes.
- **Heures estimées** : 18h
- **Profil retenu** : senior dev backend (130 000 sats/h)
- **Justification heures** : implémentation d'un client API REST avec pagination cursor-based, retries 429 avec backoff exponentiel, filtre catégorie + mots-clés ≈ 1,5 jour. Models avec dual format prix (cents int legacy vs dollars string), dataclasses propres, validation ≈ 1 jour. Total ~2,5 jours = 18h.
- **Ajustement qualité** : ×1,10
  - Auto-détection format prix dans `_price_to_dollars()` = signal qualité explicite
  - Models structurés avec `from_api()` + properties calculées (implied_prob_yes, is_resolved)
  - Error handling propre dans `_get` avec retries
- **Ajustement impact** : ×1,20 (core : sans ce module, rien ne tourne en aval)
- **Valeur** : 18 × 130 000 × 1,10 × 1,20 = **3 088 800 sats**

#### [Phase 2] Intégration Open-Meteo (forecast + historique)

- **Artefacts** : `weather/open_meteo.py` (420 lignes — substantiel)
- **Heures estimées** : 27h
- **Profil retenu** : ML/data engineer (140 000 sats/h)
- **Justification heures** : 11 villes mappées avec coordonnées NWS-aligned ≈ 1-2h ; AVAILABLE_MODELS catalogue 5 modèles + dataclasses DailyObservation/DailyForecast avec conversions ≈ 4h ; endpoints forecast/ensemble/multi_model/historical ≈ 1,5 jour ; parsing post-fixe modèle (`_parse_multi_model_daily`) ≈ 4h ; cache disque ≈ 4h. Total ~3,5-4 jours = 27h.
- **Ajustement qualité** : ×1,10
  - Caching avec dataclasses propres
  - Multi-model parser robuste (gère absence de variable selon modèle)
  - User-Agent + retries 429
- **Ajustement impact** : ×1,20 (core data layer)
- **Valeur** : 27 × 140 000 × 1,10 × 1,20 = **4 989 600 sats**

#### [Phase 3] Predictors core (base + parsers + climato + forecast_blend)

- **Artefacts** : `predictors/base.py` (73L) + `parsers.py` (143L) + `climatology.py` (131L) + `forecast_blend.py` (161L). Total **508 lignes**.
- **Heures estimées** : 22h
- **Profil retenu** : researcher quant (160 000 sats/h) — math probabiliste + domain météo
- **Justification heures** : interface abstraite + dataclasses ≈ 2h ; parsers (SERIES_MAP, parse_kalshi_date, **7 patterns regex** subtitles) ≈ 6h ; ClimatologyPredictor avec fenêtre saisonnière + Laplace smoothing + arrondi NWS + confidence ≈ 6h ; ForecastBlendPredictor avec CDF normale + blend horizon exponentiel + gestion cas dégénérés ≈ 8h. Total ~22h.
- **Ajustement qualité** : ×1,15
  - Laplace smoothing 0.5 (anti-extrême)
  - Intégration arrondi NWS dès la baseline climato
  - Sigma estimé depuis amplitude historique avec proxy normal
  - Type hints Literal, fallback chain robust (out_of_range, forecast_error, date_not_in_forecast, value_missing → fallback climato avec raison loggée)
- **Ajustement impact** : ×1,20 (core predictor, baseline contre laquelle tout le reste se mesure)
- **Valeur** : 22 × 160 000 × 1,15 × 1,20 = **4 857 600 sats**

#### [Phase 4] Simulation paper-trading

- **Artefacts** : `simulation/sizing.py` (45L) + `simulation/ledger.py` (88L). Total 133 lignes.
- **Heures estimées** : 10h
- **Profil retenu** : senior dev backend (130 000 sats/h)
- **Justification heures** : Kelly fractionnel propre avec gestion YES/NO symétrique et clamping ≈ 4h ; Ledger CSV append-only avec read_all/write_all et cast types ≈ 6h. Total ~10h.
- **Ajustement qualité** : ×1,05
  - Clamping prob [1e-6, 1-1e-6] et px [0.01, 0.99] anti-cas dégénérés
  - PaperBet dataclass avec champs résolution séparés
  - CSV avec headers explicites
- **Ajustement impact** : ×1,20 (core trading sim — sans elle pas de mesure d'edge ex ante)
- **Valeur** : 10 × 130 000 × 1,05 × 1,20 = **1 638 000 sats**

#### [Phase 5] Backtest scoring infrastructure

- **Artefacts** : `simulation/scoring.py` (76L) + `scripts/backtest.py` (176L). Total 252 lignes.
- **Heures estimées** : 8h
- **Profil retenu** : ML engineer (140 000 sats/h)
- **Justification heures** : métriques (brier, log_loss avec eps clamp, aggregate_metrics avec brier skill score, top-1 accuracy) ≈ 3h ; backtest CLI riche avec garde-fou predictor + normalisation events mutex + breakdown per-series + JSON output ≈ 5h. Total ~8h.
- **Ajustement qualité** : ×1,10
  - Brier skill score (vs base rate constant) — référence métrique pertinente
  - Top-1 accuracy pour mutually exclusive events
  - **Garde-fou explicite** dans backtest.py : avertit que forecast_blend / ensemble appellent un forecast actuel donc inadaptés en historique (anti-data-leakage)
- **Ajustement impact** : ×1,10 (mesure mais ne débloque pas une nouvelle étape)
- **Valeur** : 8 × 140 000 × 1,10 × 1,10 = **1 355 200 sats**

#### [Phase B-1] Résolution administrative NWS

- **Artefacts** : `kalshi/resolution.py` (**394 lignes**) + `scripts/audit_resolution.py` + `scripts/test_resolution.py` (198L, **9 tests**)
- **Heures estimées** : 22h
- **Profil retenu** : researcher quant (160 000 sats/h) — domain knowledge NWS Surface Observation Manual
- **Justification heures** : recherche manuelle des 18 stations correctes + leurs codes ICAO/coords/wfo + corrections d'erreurs latentes (TLV = Las Vegas, Chicago Rain = Midway) ≈ 6h ; mapping series_prefix → station avec 40 entries documentées ≈ 2h ; extraction station avec **3 patterns regex** + 24 mappings nom → station + chain de fallback ≈ 5h ; arrondi NWS round-half-up explicit (distinct du banker's rounding Python) + verdict déterministe `would_resolve_yes` avec gestion strike_type less/greater/between + convention Trace ≈ 4h ; audit script + 9 tests asserts avec docstrings explicatives ≈ 5h. Total ~22h.
- **Ajustement qualité** : ×1,20 (haut de la fourchette)
  - 9 tests parlants et bien isolés (rounding, infer, station extraction, résolution sur snapshots disque réels)
  - Tests documentent l'intention métier (knife-edge à 75.5°F, trace=YES uniquement seuil 0)
  - Audit script complémentaire
  - Documentation in-code de qualité (docstrings expliquant le "why" : edge attendu, distinction round-half-up, conventions Trace)
  - Chain de fallback robust (CLI explicite > pattern textuel > nom partiel > préfixe série)
- **Ajustement impact** : ×1,30
  - Résout un risque critique : sans résolution NWS correcte, tout le scoring backtest est faux et l'edge mesuré illusoire
  - Découverte d'erreurs latentes (TLV ≠ Tel Aviv, Chicago Rain mensuel ≠ O'Hare) montre que l'enjeu était réel
- **Valeur** : 22 × 160 000 × 1,20 × 1,30 = **5 491 200 sats**

#### [Phase B-2] Analyse microstructure Kalshi

- **Artefacts** : `microstructure/distribution.py` (119L) + `microstructure/biases.py` (188L) + `scripts/analyze_microstructure.py` + `scripts/test_microstructure.py` (125L, **6 tests**)
- **Heures estimées** : 18h
- **Profil retenu** : researcher quant (160 000 sats/h)
- **Justification heures** : design et implémentation des métriques microstructure (BinQuote dataclass, sum_yes_mid, implied_distribution normalisée, midpoints adaptés au strike_type, implied_mean_std) ≈ 6h ; biases composés (vig_residual, spreads médian/extreme/central, spread_skew, modal_oi_share, tail_mass, notes auto-générées) + tail_underpricing_vs_climato ≈ 8h ; tests + analyze script ≈ 4h. Total ~18h.
- **Ajustement qualité** : ×1,15
  - 6 tests sur cas dégénérés (singleton Rain NYC géré explicitement)
  - Tri par midpoint pour distribution ordonnée
  - Notes auto-générées sur cas suspects (vig importante, sum_mid sous 1)
  - Code propre et modulaire (séparation distribution / biases)
- **Ajustement impact** : ×1,00
  - Hypothèse "tail underpricing structurel" testée empiriquement et **rejetée** (29/32 events). Le résultat négatif a une valeur stratégique réelle (pivot stratégique : ne pas bâtir une stratégie autour du vig sur les extrêmes) mais ne débloque pas une étape positive du roadmap. Coefficient neutre — le négatif EST de l'information.
- **Valeur** : 18 × 160 000 × 1,15 × 1,00 = **3 312 000 sats**

#### [Phase A.1] Méta-ensemble IA + pipeline forward-test

- **Artefacts** :
  - `predictors/ensemble.py` (213L) : EnsemblePredictor mode uniform + hook poids, sigma_inter (epistémique) + sigma_climato (résiduel) en quadrature, correction arrondi NWS ±0.5°F, blend horizon exp, validation modèles inconnus, fallbacks complets
  - Extension `weather/open_meteo.py` (~50 lignes) : forecast_multi_model + AVAILABLE_MODELS + DEFAULT_ENSEMBLE + parser
  - `scripts/test_ensemble.py` (80L) : table comparative live mkt vs predictors + sigma + mu
  - `scripts/forward_predict.py` (148L) : capture quotidienne avec CLI + filtrage série + snapshot JSON
  - `scripts/score_forward.py` (192L) : score les forward captures contre résolutions Kalshi + comparaison vs kalshi_mid (référence)
- **Heures estimées** : 28h, décomposées en 3 profils :
  - 6h ML/data engineer (extension multi-modèle Open-Meteo) — 140 000 sats/h
  - 12h researcher quant (logique d'ensemble, propagation sigma, blend horizon) — 160 000 sats/h
  - 10h senior dev (forward_predict + score_forward + intégration Kalshi pour résolutions) — 130 000 sats/h
- **Justification heures** : exploration des 5 modèles disponibles via API + intégration ≈ 6h ; ensemble logic avec sigma propagation correcte + blend horizon ≈ 1,5 jour quant ; forward_predict + score_forward + dédup anti-leakage + comparaison kalshi_mid ≈ 10h senior dev. Total ~3,5-4 jours soit 28h.
- **Ajustement qualité** : ×1,10
  - Tests présents (test_ensemble.py)
  - Pipeline forward-test sans data leakage (`score_forward.py` dédup au PREMIER capture par ticker)
  - **Comparaison vs kalshi_mid intégrée** : la vraie référence (le marché lui-même) est mesurée systématiquement
  - Discipline méthodologique notable : commentaire explicite "la SEULE manière honnête de backtester sans data leakage"
- **Ajustement impact** : ×1,40
  - Vrai différenciant projet (priorité 1 du roadmap d'après mémoire et docs)
  - Débloque le critère go/no-go vers Phase A.2 (Aurora/Pangu/FourCastNet via HuggingFace + GPU cloud, conditionné au signal A.1)
  - Sans cet ensemble fonctionnel + pipeline forward-test, le projet est bloqué à la baseline climato qui montre déjà ne pas suffire (Brier skill score -0,21)
- **Valeur pré-ajustement** : (6 × 140 000) + (12 × 160 000) + (10 × 130 000) = 840 000 + 1 920 000 + 1 300 000 = **4 060 000 sats**
- **Valeur** : 4 060 000 × 1,10 × 1,40 = **6 252 400 sats**

#### [Phase A.1-bugfix] Stabilisation runtime

- **Artefacts** :
  - Garde-fou `_has_usable_series()` dans `cached_or_fetch` de `open_meteo.py` (lignes 396-411) — refuse cache vide, supprime cache vide existant
  - Fonction `_price_to_dollars()` dans `kalshi/models.py` — auto-détection dual format API
  - Correction `simulate.py` /2.0 (anciennement /200)
- **Heures estimées** : 9h (3 bugs × 3h moyenne incluant régression test)
- **Profil retenu** : senior dev backend (130 000 sats/h)
- **Justification heures** : un bug runtime sur un système en production demande typiquement 2-4h pour reproduire, fixer, et écrire le test/garde-fou. Trois bugs × ~3h = 9h.
- **Ajustement qualité** : ×1,15
  - Garde-fou structurel `_has_usable_series` (vérifie daily.time ET hourly.time pour tous les endpoints) plutôt que patch superficiel
  - Auto-détection format prix robuste à l'évolution future de l'API
  - Tests régression visibles dans test_resolution.py (rounding cases qui auraient capté la régression)
- **Ajustement impact** : ×1,00
  - Sauvegarde l'existant : sans ces fixes, l'ensemble du pipeline produit des résultats faux. Ne débloque pas une nouvelle étape mais évite l'invalidation de tout le travail antérieur. Standard.
- **Valeur** : 9 × 130 000 × 1,15 × 1,00 = **1 345 500 sats**

#### [Phase Daily Run] Orchestrateur opérationnel

- **Artefacts** : `scripts/daily_run.py` (84L) — routine idempotente fetch_markets → forward_predict → score_forward, timeouts 30 min/step, traceback, exit code agrégé
- **Heures estimées** : 4h
- **Profil retenu** : senior dev backend (130 000 sats/h)
- **Justification heures** : assemblage propre avec gestion timeouts + tracebacks + reporting structuré ≈ 4h.
- **Ajustement qualité** : ×1,10 (idempotent, timeouts, error handling propre, exit code utilisable par cron/scheduler)
- **Ajustement impact** : ×1,10 (permet le forward-test régulier requis pour atteindre N>50 events ; testé en production sur Cowork scheduled tasks)
- **Valeur** : 4 × 130 000 × 1,10 × 1,10 = **629 200 sats**

---

### Total apporteur @Elladriel80

| # | Phase | Valeur (sats) |
|---|---|---:|
| 0 | Setup, design, stratégie | 1 080 000 |
| 1 | Client Kalshi | 3 088 800 |
| 2 | Intégration Open-Meteo | 4 989 600 |
| 3 | Predictors core | 4 857 600 |
| 4 | Simulation paper-trading | 1 638 000 |
| 5 | Backtest scoring | 1 355 200 |
| B-1 | Résolution NWS | 5 491 200 |
| B-2 | Microstructure | 3 312 000 |
| A.1 | Méta-ensemble + forward-test | 6 252 400 |
| A.1-bf | Stabilisation runtime | 1 345 500 |
| DR | Daily run orchestrator | 629 200 |
| | **TOTAL** | **34 039 500 sats** |

= **0,34040 BTC**

(référence indicative au cours actuel BTC/EUR ~95 000 € : ~32 338 € — l'EUR n'entre PAS dans le mint)

---

## Synthèse round

### Tableau récapitulatif

| Apporteur | Valeur totale (sats) | Valeur totale (BTC) | Tokens à mint @ NAV 1 sat = 1 token |
|---|---:|---:|---:|
| @Elladriel80 | 34 039 500 | 0,34040 | 34 039 500 |
| **TOTAL ROUND** | **34 039 500** | **0,34040** | **34 039 500** |

NAV initiale : **1 sat = 1 token** (validée 2026-05-08).

### Vérification garde-fous

- **Cap mensuel global** ≤ 10 % du supply circulant : **NON applicable** au round genesis (supply = 0 avant ce round, par construction).
- **Cap par apporteur** ≤ 30 % du mint mensuel : **NON applicable** (un seul apporteur).
- **Valuation > 0,01 BTC pour un apporteur** : **OUI**, 0,34 BTC pour @Elladriel80. Trigger automatique du vote panel — mais aucun panel à ce stade (pas encore de holders). Substitué par la **fenêtre de challenge étendue 30 jours** ouverte aux prospects investisseurs avant souscription.

### Liste des incertitudes signalées au ratificateur

1. **Pas d'historique granulaire de PRs** dans `predictor/` (importé en commit unique). La décomposition en phases est opinionnée et basée sur la structure modulaire finale + la mémoire projet. Une revue de JS sur la décomposition est utile.
2. **Phase 4 (Simulation)** revue à la baisse vs dry-run (de 14h → 10h) : le code livré est plus modeste que ce que la mémoire suggérait (sizing.py 45 lignes, ledger.py 88 lignes). Le simulate.py script n'a pas été lu en détail mais probablement < 100 lignes additionnelles.
3. **Phase 2 (Open-Meteo)** revue à la hausse (de 21h → 27h) : open_meteo.py fait 420 lignes avec 11 villes + 5 modèles + multi-model parser substantiel. Plus dense que la mémoire indiquait.
4. **Phase 3 (Predictors core)** revue à la hausse (de 14h → 22h) : 4 fichiers totalisant 508 lignes vs estimation initiale plus modeste. Inclut `parsers.py` (143 lignes) et `base.py` (73 lignes) que je n'avais pas explicitement comptabilisés au dry-run.
5. **Phase B-1 (NWS resolution)** revue à la hausse (de 18h → 22h) : 394 lignes de code domain-aware avec qualité documentaire élevée + 9 tests substantiels. Coefficient qualité durci à ×1,20.
6. **Phase A.1** : décomposition 6h ML + 12h quant + 10h senior dev (vs 6+10+8 du dry-run). Les scripts forward_predict + score_forward sont substantiels (148L + 192L) et incluent une discipline anti-leakage explicite + comparaison vs kalshi_mid → +2h senior dev.
7. **Phase Daily Run** ajoutée vs dry-run (4h × 130k × 1,10 × 1,10 = 629k sats). N'avait pas été comptabilisée explicitement au dry-run.
8. **Travail invisible non capté** : R&D exploratoire (lecture papers Aurora/Pangu, prototypes abandonnés, debug DM), lectures de specs Kalshi/NWS, réunions stratégiques. Non comptabilisé conformément au RUBRIC fact-only. À assumer ou compenser via un round séparé "augure-rounds" pour les artefacts du repo de gouvernance.
9. **Évolution vs dry-run** : total 34 040 000 sats (real run) vs 27 299 400 sats (dry-run), soit **+24,7 %**. Dans la zone d'incertitude ±20-25 % flaggée au dry-run.

---

*Fin du rapport. Ce real run est un input pour la ratification finale du round genesis. Action en attente : ouverture de la fenêtre de challenge 30 jours aux prospects investisseurs.*
