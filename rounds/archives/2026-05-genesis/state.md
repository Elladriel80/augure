# Project state — context for the valuation agent

*Date : 2026-05-08*
*Round : `2026-05-genesis`*

## Projet

**Augure** : projet open-source de prediction markets météo + assurance paramétrique décentralisée. Vision long terme : DAO avec moat prédictif ML communautaire et DePIN data layer.

**Phase actuelle** : POC Kalshi. Objectif = valider quantitativement un edge prédictif sur les marchés Kalshi météo avant de construire l'infrastructure DAO. Pas de produit final visé en POC ; livrable = preuve d'edge.

**Statut équipe** : solo (Elladriel80 / @Elladriel80). Le projet rouvre à investisseurs externes et contributeurs open-source via le repo `augure-rounds`.

## Roadmap macro

1. **POC Kalshi** *(en cours)* — valider l'edge prédictif. Critère go/no-go : ensemble IA bat le best single model et bat la climato sur N>50 events.
2. **DAO Augure** — risk-pool tokenisé façon Nexus Mutual, contrats émis via AMM/orderbook on-chain, pricing via le moteur prédictif.
3. **DePIN data layer** — stations physiques rémunérées en token (WeatherXM partner ou réseau propre).
4. **Single token unifié** — staking underwriter, rewards data providers, rewards modelers, gouvernance.

## Stratégie de prédiction (pour valider l'impact des contributions)

Cinq angles d'edge identifiés et hiérarchisés :

1. **Méta-ensemble IA** *(priorité, en cours Phase A.1)* — combiner GraphCast, Aurora, FourCastNet, Pangu, GenCast, Aifs avec ECMWF/GFS. Apprendre dynamiquement quel modèle bat les autres par région/saison/type d'événement.
2. **Edge résolution administrative NWS** *(livré Phase B-1)* — bizarreries des règles Kalshi (station primary/backup, arrondis, corrections post-pub).
3. **Microstructure / biais comportementaux Kalshi** *(testé Phase B-2, hypothèse rejetée)* — tail underpricing, recency bias, weekend illiquidity. Edge mesurable empiriquement.
4. **Crowdsourced data + LLM lecteur** — PWS networks (WU, Netatmo), Twitter/X, traffic cams. Repoussé.
5. **Soil moisture / MJO / vortex stratosphérique** — long-horizon predictors sous-utilisés. Repoussé.

## Métriques clés observées

- Baseline climato pure (16 events Austin) : top-1 accuracy 31 %, Brier skill score −0,21. Confirme la nécessité de NWP+ML.
- Vig Kalshi moyenne payée au mid : +0,16 % (très efficient). Pas d'edge gratuit en microstructure.
- Spread inter-modèles ensemble (Austin 26MAY09) : 5 °C entre les 5 modèles disponibles. Terrain réel pour l'ensemble.

## État technique du repo `kalshi-poc` à la date du round

- Stack Python 3.13, requests, lightgbm-ready
- Modules livrés : Kalshi client (lecture), Open-Meteo (forecast + ERA5), predictors (climato + forecast_blend + ensemble), simulator paper-trading + ledger, backtest scoring, résolution NWS (18 stations + 9 tests), microstructure (6 tests), méta-ensemble Open-Meteo frugal
- À venir : Phase A.2 (Aurora/Pangu/FourCastNet via HuggingFace + GPU cloud, conditionné au signal A.1), task #12 méta-ensemble étendu, refacto issuer Kalshi-read / DAO-write

## Implications pour la valuation

- Tout artefact qui contribue mesurablement à l'angle 1 (méta-ensemble) reçoit l'**ajustement impact ×1.3 à ×1.5** (différenciant projet, débloque Phase A.2).
- Les artefacts de l'angle 3 (microstructure) qui ont produit un **résultat négatif actionnable** (hypothèse rejetée → pivot stratégique) reçoivent l'ajustement standard ×1.0. Le négatif n'est pas une perte, c'est de l'information.
- Les fixes runtime (bugs cache, parsing Market, simulate) reçoivent un coefficient qualité positif si tests de régression ajoutés, impact standard ×1.0 (sauve l'existant sans débloquer du nouveau).
- Travail de stratégie / design (Phase 0) reçoit ajustement impact ×1.2 — il oriente toutes les phases suivantes.
