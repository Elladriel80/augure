# Valuation report — round `2026-05-genesis` (DRY-RUN)

*Date : 2026-05-08*
*Source : décomposition `phases.md` + state `state.md`*
*Agent : Claude (Anthropic), application directe du prompt versionné `agent/PROMPT.fr.md` v0.2*
*Statut : **DRY-RUN** — voir `DRY_RUN_NOTES.md` pour les caveats. Chiffres indicatifs, à re-générer sur l'historique Git réel avant ratification.*

---

## @Elladriel80

### Artefacts évalués

#### [Phase 0] Setup, design et stratégie

- **Artefacts** : structure repo + environnement Python 3.13, document de stratégie listant 5 angles d'edge, décision motivée NE PAS répliquer LightGBM mainstream, critères d'arrêt explicites
- **Heures estimées** : 6h (4h researcher + 2h senior dev)
- **Profil retenu** : décomposé — 4h researcher quant (160 000 sats/h) + 2h senior dev (130 000 sats/h)
- **Justification heures** : un document de stratégie identifiant 5 angles d'edge mesurés contre la concurrence représente ~3-4h de réflexion structurée + ~1h de mise en forme. Le setup repo + environnement + dépendances ~2h pour un dev senior familier de la stack.
- **Ajustement qualité** : ×1,00
  - Pas de signal explicite de tests/doc à ce stade. Coefficient neutre.
- **Ajustement impact** : ×1,20
  - Le document de stratégie oriente l'ensemble du roadmap. Choix de NE PAS faire LightGBM mainstream est un ajustement actionnable qui élimine d'office la concurrence directe.
- **Valeur** : (4 × 160 000) + (2 × 130 000) = 900 000 sats avant ajustement → 900 000 × 1,00 × 1,20 = **1 080 000 sats**

#### [Phase 1] Client Kalshi (lecture publique)

- **Artefacts** : module client API Kalshi, récupération markets, séries bid/ask, snapshots
- **Heures estimées** : 14h
- **Profil retenu** : senior dev backend (130 000 sats/h)
- **Justification heures** : implémentation d'un client API REST avec parsing snapshots et gestion bid/ask, pour un repo neuf, ≈ 2 jours de travail focalisé. Pas d'auth complexe (lecture publique).
- **Ajustement qualité** : ×1,05
  - Module en production dans tout le pipeline downstream. Pas de tests dédiés mentionnés à ce stade mais validé par usage.
- **Ajustement impact** : ×1,20
  - Bloquant pour tout le reste. Sans ce module, rien ne tourne.
- **Valeur** : 14 × 130 000 × 1,05 × 1,20 = **2 293 200 sats**

#### [Phase 2] Intégration Open-Meteo (forecast + ERA5)

- **Artefacts** : `src/weather/open_meteo.py` initial, multi-modèle, dataclass `DailyForecast`, mécanisme de cache
- **Heures estimées** : 21h
- **Profil retenu** : ML / data engineer (140 000 sats/h)
- **Justification heures** : intégration de deux endpoints (forecast multi-day + historical ERA5) avec dataclass typée et caching ≈ 3 jours. La logique cache nécessite réflexion non triviale (clés, invalidation).
- **Ajustement qualité** : ×1,10
  - Caching montre attention à la performance. Bug latent identifié et corrigé en Phase A.1-bugfix (compté à part).
- **Ajustement impact** : ×1,20
  - Couche data layer core. Sans elle, pas de prediction.
- **Valeur** : 21 × 140 000 × 1,10 × 1,20 = **3 880 800 sats**

#### [Phase 3] Predictors core (climatologie + forecast_blend)

- **Artefacts** : predictor climatologie pure (distribution historique par jour calendaire), predictor `forecast_blend` (blending climato + NWP avec horizon decay)
- **Heures estimées** : 14h
- **Profil retenu** : researcher quant (160 000 sats/h)
- **Justification heures** : design de deux predictors avec sortie probabiliste, plus la logique de blending par horizon (decay exponentiel) ≈ 2 jours pour un quant familier des distributions empiriques.
- **Ajustement qualité** : ×1,10
  - Validé par l'infrastructure backtest (Phase 5) qui mesure la performance.
- **Ajustement impact** : ×1,20
  - Predictor central. Baseline contre laquelle tout le reste se mesure.
- **Valeur** : 14 × 160 000 × 1,10 × 1,20 = **2 956 800 sats**

#### [Phase 4] Simulateur + paper-trading + ledger

- **Artefacts** : simulateur paper-trading sur snapshots Kalshi, ledger positions/P&L
- **Heures estimées** : 14h
- **Profil retenu** : senior dev backend (130 000 sats/h)
- **Justification heures** : design d'un simulateur avec gestion bid/ask, slippage implicite, et journal des trades ≈ 2 jours.
- **Ajustement qualité** : ×1,00
  - Bug identifié plus tard (divide by 200 hérité de l'API legacy cents-vs-dollars). Coefficient neutre — le bug n'était pas évidemment évitable au moment de l'écriture, et il sera explicitement compté dans la Phase A.1-bugfix avec coefficient qualité positif (régression test ajoutée). Ne pas double-pénaliser.
- **Ajustement impact** : ×1,20
  - Core du POC : sans simulateur, pas de mesure d'edge ex ante.
- **Valeur** : 14 × 130 000 × 1,00 × 1,20 = **2 184 000 sats**

#### [Phase 5] Backtest scoring infrastructure

- **Artefacts** : calcul accuracy top-1, Brier, log loss, Brier skill score vs baseline
- **Heures estimées** : 7h
- **Profil retenu** : ML engineer (140 000 sats/h)
- **Justification heures** : implémentation des trois métriques classiques de probabilistic scoring sur un pipeline existant ≈ 1 jour.
- **Ajustement qualité** : ×1,05
- **Ajustement impact** : ×1,10
  - Permet la mesure mais ne débloque pas une étape majeure du roadmap. Élevé mais pas bloquant.
- **Valeur** : 7 × 140 000 × 1,05 × 1,10 = **1 131 900 sats**

#### [Phase B-1] Résolution administrative NWS

- **Artefacts** : `src/kalshi/resolution.py` avec catalogue **18 stations NWS** (CLI codes + ICAO + lat/lon/wfo), extraction règle `cap_strike`/`floor_strike`/`strike_type`, arrondi *round half up* NWS, convention Trace=OUI ; `scripts/audit_resolution.py` ; `scripts/test_resolution.py` avec **9 asserts** Austin/NYC/Chicago/Rain/Trace
- **Heures estimées** : 18h
- **Profil retenu** : researcher quant (160 000 sats/h) — domain knowledge des règles NWS et mapping stations relève de l'expertise météo, pas pure ingénierie
- **Justification heures** : recherche manuelle des 18 stations correctes (corrigeant des pièges réels comme TLV=Las Vegas et Chicago Rain=Midway) ≈ 4-6h de travail rigoureux. Implémentation parser règle + arrondi NWS ≈ 4h. Audit script + 9 tests ≈ 6-8h. Total ~18h.
- **Ajustement qualité** : ×1,20
  - Tests significatifs (9 asserts couvrant cas standards + cas-limites Trace + station alternative), audit script, documentation des conventions NWS dans le code. Très haut de la fourchette qualité.
- **Ajustement impact** : ×1,30
  - Resolves a critical risk : sans résolution NWS correcte, tout le scoring backtest est faux et l'edge mesuré est illusoire. Découverte d'erreurs latentes (TLV, Chicago Rain) montre que l'enjeu était réel.
- **Valeur** : 18 × 160 000 × 1,20 × 1,30 = **4 492 800 sats**

#### [Phase B-2] Analyse microstructure Kalshi

- **Artefacts** : `src/microstructure/distribution.py` (extraction bins, vig, distribution implicite), `src/microstructure/biases.py` (`event_biases()` + `tail_underpricing_vs_climato()`), `scripts/analyze_microstructure.py`, `scripts/test_microstructure.py` avec **6 tests**
- **Heures estimées** : 14h
- **Profil retenu** : researcher quant (160 000 sats/h)
- **Justification heures** : design des métriques microstructure (vig, skew, modal_oi_share, tail_mass) ≈ 1 jour. Implémentation + 6 tests ≈ 1 jour. Total ~14h.
- **Ajustement qualité** : ×1,15
  - 6 tests couvrant cas dégénérés (singleton Rain). Code propre et modulaire (séparation distribution / biases).
- **Ajustement impact** : ×1,00
  - Hypothèse "tail underpricing structurel" testée empiriquement et **rejetée** (29/32 events). Le résultat négatif a une valeur stratégique réelle (ne pas bâtir une stratégie autour) mais ne débloque pas une étape positive du roadmap. Coefficient neutre, ni récompense pour le succès, ni pénalité pour la conclusion défavorable. Le négatif EST de l'information.
- **Valeur** : 14 × 160 000 × 1,15 × 1,00 = **2 576 000 sats**

#### [Phase A.1] Méta-ensemble IA (version frugale Open-Meteo)

- **Artefacts** :
  - Extension `open_meteo.py` : `forecast_multi_model()`, `AVAILABLE_MODELS`, `DEFAULT_ENSEMBLE` avec 5 modèles confirmés (`ecmwf_ifs025`, `ecmwf_aifs025_single`, `gfs_graphcast025`, `gfs_global`, `jma_gsm`)
  - `src/predictors/ensemble.py` : `EnsemblePredictor` avec mode uniform + hook poids, propagation `sigma_total = quadrature(sigma_inter_models, 0.5 × sigma_climato)`, blend horizon `~exp(-d/8)`
  - `scripts/test_ensemble.py` quick-check live
  - `scripts/forward_predict.py` capture quotidienne (anti-data-leakage)
  - `scripts/backtest.py --predictor ensemble`
- **Heures estimées** : 24h, décomposées en 3 profils :
  - 6h ML/data engineer (extension multi-modèle Open-Meteo) — 140 000 sats/h
  - 10h researcher quant (logique d'ensemble, propagation sigma, horizon blending) — 160 000 sats/h
  - 8h senior dev (forward-predict, backtest CLI) — 130 000 sats/h
- **Profils retenus** : décomposés ci-dessus
- **Justification heures** : exploration des modèles disponibles via API ≈ 4h + intégration ≈ 2h. Conception de l'ensemble + propagation sigma + blend horizon ≈ 1,5 jour de réflexion quant. Forward-predict + amendement backtest ≈ 1 jour senior dev. Total ~3-4 jours soit 24h.
- **Ajustement qualité** : ×1,10
  - Tests présents (`test_ensemble.py`), pipeline forward-test sans data leakage = signal de discipline méthodologique. Cohérent avec haut de la fourchette standard.
- **Ajustement impact** : ×1,40
  - Vrai différenciant projet (priorité 1 du roadmap). Débloque le critère go/no-go vers Phase A.2 (modèles HuggingFace + GPU cloud). Sans cet ensemble fonctionnel, tout le projet est bloqué à la baseline climato qui montre déjà ne pas suffire (Brier skill -0,21).
- **Valeur pré-ajustement** : (6 × 140 000) + (10 × 160 000) + (8 × 130 000) = 840 000 + 1 600 000 + 1 040 000 = 3 480 000 sats
- **Valeur** : 3 480 000 × 1,10 × 1,40 = **5 359 200 sats**

#### [Phase A.1-bugfix] Stabilisation runtime

- **Artefacts** :
  - `_has_usable_series()` dans `cached_or_fetch` (cache Open-Meteo écrivait silencieusement les réponses vides)
  - `Market.from_api()` auto-détection format `yes_bid_dollars`/`yes_ask_dollars` vs legacy cents
  - `simulate.py` correction division /200 → /2.0
- **Heures estimées** : 9h (3 bugs × 3h moyenne incluant régression test)
- **Profil retenu** : senior dev backend (130 000 sats/h)
- **Justification heures** : un bug runtime sur un système en production demande typiquement 2-4h pour reproduire, fixer, et écrire le test de régression. Trois bugs × ~3h = 9h.
- **Ajustement qualité** : ×1,15
  - Régression tests ajoutés explicitement. Garde-fou dur (`_has_usable_series`) plutôt que patch superficiel. Signal clair de discipline correctrice.
- **Ajustement impact** : ×1,00
  - Sauvegarde l'existant (sans ces fixes, l'ensemble du pipeline produit des résultats faux). Ne débloque pas une nouvelle étape du roadmap, mais évite que tout le travail antérieur soit invalidé. Standard.
- **Valeur** : 9 × 130 000 × 1,15 × 1,00 = **1 345 500 sats**

---

### Total apporteur @Elladriel80

| Phase | Valeur (sats) |
|---|---:|
| 0. Setup, design, stratégie | 1 080 000 |
| 1. Client Kalshi | 2 293 200 |
| 2. Intégration Open-Meteo | 3 880 800 |
| 3. Predictors core | 2 956 800 |
| 4. Simulateur + ledger | 2 184 000 |
| 5. Backtest scoring | 1 131 900 |
| B-1. Résolution NWS | 4 492 800 |
| B-2. Microstructure | 2 576 000 |
| A.1. Méta-ensemble | 5 359 200 |
| A.1-bugfix. Stabilisation | 1 345 500 |
| **TOTAL** | **27 299 400 sats** |

= **0,27299 BTC**

(référence indicative au cours actuel BTC/EUR ~95 000 € : ~25 935 € — l'EUR n'entre PAS dans le mint)

---

## Synthèse round

### Tableau récapitulatif

| Apporteur | Valeur totale (sats) | Valeur totale (BTC) | Tokens à mint @ NAV 1000 sats/token |
|---|---:|---:|---:|
| @Elladriel80 | 27 299 400 | 0,27299 | 27 299 |
| **TOTAL ROUND** | **27 299 400** | **0,27299** | **27 299** |

NAV initiale assumée pour le calcul : 1 AUG-POC = 1000 sats (= 0,00001 BTC). Cette NAV est ajustable — voir `DRY_RUN_NOTES.md`.

### Vérification garde-fous

- **Cap mensuel global** ≤ 10 % du supply circulant : NON applicable au round genesis (supply = 0 avant ce round, par construction).
- **Cap par apporteur** ≤ 30 % du mint mensuel : NON applicable au round genesis (un seul apporteur).
- **Valuation > 0,01 BTC** : OUI, 0,273 BTC pour @Elladriel80. **Trigger automatique du vote panel** — mais sans panel à ce stade (pas encore de holders). En l'état du rubric, le round genesis est ratifié par fenêtre de challenge étendue 30 jours, ouverte aux prospects investisseurs avant souscription. Correspond bien à `STATUS: AUTO_PANEL_VOTE` du prompt, à interpréter ici comme "challenge window 30 jours obligatoire avant ratification".

### Liste des incertitudes signalées au ratificateur

1. **Ce rapport est un DRY-RUN sur la base des descriptions de la mémoire projet, pas sur l'historique Git réel.** Les heures estimées et les détails artefactuels par phase peuvent diverger de la réalité du repo `kalshi-poc` (typiquement de ±20 %). Le rapport définitif doit être re-généré quand le repo est accessible à l'agent.
2. **Phase 4 (Simulateur)** : choix de coefficient qualité ×1,00 plutôt que pénalisant (×0,9 pour bug shipping) parce que le bug `/200` est isolé et corrigé en Phase A.1-bugfix avec qualité positive. À débattre si on considère qu'il fallait pénaliser au moment de l'écriture initiale.
3. **Phase B-2 (Microstructure)** : impact ×1,00 (négatif actionnable) plutôt que ×1,2 (élevé). Une lecture alternative considère que rejeter une hypothèse fausse a un impact stratégique fort ; ce choix conservateur peut être contesté.
4. **Phase A.1 (Méta-ensemble)** : impact ×1,4 plutôt que ×1,5 — l'ensemble est livré et fonctionnel mais le critère go/no-go (battre best single model + climato sur N>50) n'est PAS encore démontré (forward-test en cours, pas assez d'events résolus). À ré-évaluer après collecte forward-test.
5. **Décomposition heures Phase A.1** : la décomposition 6h/10h/8h en trois profils est opinionnée. Une lecture monoprofil "researcher quant" sur l'ensemble donnerait : 24 × 160 000 × 1,10 × 1,40 = 5 913 600 sats (vs 5 359 200 actuel). Différence ≈ 10 %, non négligeable.
6. **NAV initiale 1000 sats/token** : choix arbitraire. Affecte le nombre de tokens minté mais pas la valeur en BTC. Voir `DRY_RUN_NOTES.md`.
7. **Travail invisible non capté** : la mémoire projet documente principalement les modules livrés. Heures de R&D exploratoire (lecture papers Aurora/Pangu, prototypes abandonnés, debug DM) ne sont pas représentées. Conformes au rubric (fact-only) mais à mentionner.

---

*Fin du rapport. Ce dry-run est un input de calibration. La ratification réelle attend (a) accès au repo `kalshi-poc` pour vérification, (b) ouverture de la fenêtre de challenge 30 jours aux prospects investisseurs.*
