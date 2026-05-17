# Sizing — caps per-trade, portfolio heat, correlation

Ce document justifie les trois constantes qui plafonnent le sizing des paris
paper-trade Phase 1.

Source : [RFC portfolio heat & correlation caps](../../research/rfc/RFC-portfolio-heat-and-correlation-caps.md)
(2026-05-17).

## Vue d'ensemble

L'ordre d'application est *strictest constraint wins* — on prend le **min**
des trois caps avant de redescendre dans le sizer Kelly fractionnel
(`kelly_fractional_size`).

```
f_kelly_fractional = (edge / b) * α            # α = 0.25 (quart-Kelly)
f_per_trade_cap    = min(f_kelly_fractional, MAX_FRACTION_PER_BET)   # 5 %
f_heat_cap         = max(0, MAX_PORTFOLIO_HEAT  - Σ f_open)          # 10 %
f_cluster_cap      = max(0, MAX_CLUSTER_EXPOSURE - Σ f_cluster_open) # 6 %
f_final            = min(f_per_trade_cap, f_heat_cap, f_cluster_cap)
```

Si `f_final == 0`, le pari est **refusé** strictement — pas de
redimensionnement à epsilon, jamais. La liquidité partielle introduirait du
bruit dans l'évaluation du tournoi predictor (kalshi_mid vs learned_v2 vs
climato).

## `MAX_FRACTION_PER_BET = 0.05`

Cap absolu par pari, en place depuis l'origine du sizer per-trade.

- **Quart-Kelly à 5 %** est l'état de l'art binaire pour les marchés
  prédictifs : Kelly théorique sur un pari binaire converge vite vers la
  ruine si l'estimateur de `p_yes` dérive de quelques points.
- Le multiplicateur α = 0.25 vient absorber l'erreur d'estimation du
  predictor (typiquement 5-10 points de BSS d'écart entre learned_v2 et la
  vraie loi). Promotion vers α = 0.5 conditionnée à N ≥ 100 settled +
  meta-predictor stable sur kalshi_mid ET climato (hors-scope de cette PR).

## `MAX_PORTFOLIO_HEAT = 0.10`

Plafond global sur la somme des fractions engagées sur paris **non-settled**.

- **10 % plutôt que 6-8 %** comme recommandé par l'industrie (cf.
  `position-sizer/SKILL.md` : "Portfolio heat: Total open risk should not
  exceed 6-8 % of account equity"). Justification : sur Kalshi nos pertes
  max par contrat sont bornées par `px` (le prix d'achat YES), pas par la
  distance entry-stop d'un trade ATR-équivalent. La perte maximale d'un
  portefeuille à 10 % de heat est donc strictement < 10 % du bankroll,
  alors que la même heat dans le contexte equities/futures peut taper
  beaucoup plus.
- **Pourquoi pas plus** : à 5 paris simultanés à 5 % chacun (= 25 %), une
  série de defeats corrélés sur le même front météo grille le quart du
  bankroll en une journée. 10 % limite à 2 défaites simultanées plein-cap.

## `MAX_CLUSTER_EXPOSURE = 0.06`

Plafond par *cluster spatio-temporel* de paris météo corrélés.

- **Cluster = (région NOAA) × (fenêtre settlement ≤ 3 jours)**. Le mapping
  ville → région est dans `src/simulation/clusters.py` (`CITY_TO_NOAA`).
- **6 % ≈ 1.2 × cap per-trade** : laisse explicitement 2 paris max
  corrélés (5 % + 1 %, ou 3 % + 3 %) sans bloquer complètement le flow.
  Tout 3ᵉ pari sur le même cluster est refusé.
- **Granularité NOAA 8-régions** (NE, SE, MW, NW, SW, PLAINS, AK, HI)
  plutôt que états ou clusters géographiques fins : compromis pratique.
  La grille fine ajoute des décisions de mapping arbitraires (à quel
  cluster appartient Memphis ? El Paso ?) sans réduire significativement
  la corrélation observée — les fronts synoptiques nord-américains
  débordent largement des frontières d'État.
- **Fenêtre 3 jours** : capture le passage d'un même front cyclonique
  (durée typique 24-72 h). 5 jours capturerait le régime synoptique plus
  large mais bloquerait trop de paris saisonniers. À revoir si on observe
  de la sous-corrélation résiduelle au-delà du J+3.

## Cas particuliers

- **Markets sans ville** (`KXHMONTHRANGE…`, `KXHURCTOT…`,
  `KXHURCTOTMAJ…`) : `spatial_cluster_for_ticker` lève `ValueError`. Pour
  les trader, il faudra étendre `CITY_TO_NOAA` (ou créer un cluster
  "NATIONAL") après décision explicite — pas via un fallback silencieux.
- **Persistance** : `PortfolioHeat` est in-memory dans cette PR. Un crash
  perd l'état des paris ouverts. Sérialisation disque viendra avec le
  câblage `daily_auto.py`.

## Tests

- `predictor/tests/test_clusters.py` — parser daily/monthly, mapping NOAA,
  bornes de fenêtre.
- `predictor/tests/test_portfolio_heat.py` — heat cap, cluster cap,
  clusters indépendants, settle, refus pur, strictest-wins (3 cas).
