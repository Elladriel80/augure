# RFC — Portfolio heat & correlation caps pour Aratea Phase 1

- **Auteur** : @Elladriel80
- **Date initiale** : 2026-05-17
- **Statut** : implémenté complet — caps livrés (PR #85), câblage `daily_auto` + reconstruction depuis ledger livrés (PR #<N>)
- **Issu de** : exploration des skills `tradermonty/claude-trading-skills`
  ([research/external-skills/](../external-skills/README.md))
- **Touche** : `predictor/src/simulation/sizing.py`, `predictor/src/simulation/clusters.py`, `predictor/scripts/daily_auto.py`
- **Voir aussi** : §7 « Historique d'implémentation »

## TL;DR

Le sizing per-trade d'Aratea (`kelly_fractional_size`, quart-Kelly + cap 5 %) est
**déjà correctement implémenté** : algébriquement identique à la formule
canonique `tradermonty/position-sizer`, et plus conservateur (α=0.25 vs α=0.5).

Deux garde-fous **manquent** et apparaissent comme principes-clés du skill
externe :

1. **Portfolio heat** — borner la somme des positions ouvertes à 6-8 % du
   bankroll, indépendamment du sizing per-trade.
2. **Correlation caps** — borner l'exposition agrégée à un même *cluster*
   de paris météorologiquement corrélés (même front, même fenêtre, même
   région).

Sans ces deux garde-fous, l'élargissement prévu de `daily_auto` (PR A,
multiplicateur ×25 sur le débit de paris — voir memo
`project_dashboard_refonte_pending.md`) ouvre la porte à des sessions où
5 paris simultanés à 5 % chacun = 25 % du bankroll exposé au **même
événement météo sous-jacent**.

## 1. Contexte

### État actuel de `sizing.py`

```python
def kelly_fractional_size(
    prob_yes, market_yes_price, side,
    kelly_fraction=0.25,
    bankroll=1000.0,
    max_fraction_per_bet=0.05,
) -> float:
    ...
    f_kelly = max(0.0, edge / b)
    f = min(f_kelly * kelly_fraction, max_fraction_per_bet)
    return round(f * bankroll, 2)
```

Per-trade : conforme à l'état de l'art binaire, quart-Kelly, cap 5 %. RAS.

### Ce que le skill externe rappelle

> "Portfolio heat: Total open risk should not exceed 6-8 % of account equity"
> — `position-sizer/SKILL.md`, Key Principle #6

> "Strictest constraint wins" — Key Principle #4 ; `max-position-pct`,
> `max-sector-pct`, et `current-sector-exposure` doivent être appliqués
> conjointement.

### Pourquoi maintenant

- PR A (widen `daily_auto`) ×25 sur le débit. Mémoire
  `project_predictor_infra_mature.md` : goulot actuel = `EVENT_SERIES`
  hardcodé NYC LOWT + EDGE 0.10 + SPREAD 0.05. Une fois élargi, plusieurs
  paris simultanés deviennent la norme.
- Phase A → Phase B : seasonal targets (drought, ouragan x3 triggers,
  4 cibles Tier 1, 6 Tier 2 — memo `project_seasonal_phase_b.md`). Les
  contrats saisonniers ont un horizon de 3-12 mois, donc plusieurs paris
  ouverts **en parallèle pendant plusieurs mois** — la concentration cumule
  dans le temps.

## 2. Proposition

### 2.1 Portfolio heat

Ajouter un wrapper `PortfolioHeat` en amont de `kelly_fractional_size` qui :

- Maintient la somme des `f` (fractions de bankroll engagées) sur les paris
  **non-settled**.
- Refuse un nouveau pari si `Σ f_open + f_nouveau > MAX_PORTFOLIO_HEAT`.
- Valeur cible **MAX_PORTFOLIO_HEAT = 0.10** (10 %, plus généreux que les
  6-8 % equity car nos payoffs binaires sont déjà capés à la baisse — perte
  max par contrat = `px`, pas la position ATR-distance equity).

### 2.2 Correlation caps

Définir un *cluster* de paris météorologiquement corrélés.

Heuristique pragmatique en deux dimensions :

- **Cluster spatial** : régions climatiques NOAA (NE, SE, MW, NW, SW, Plains, AK, HI).
  Deux paris LOWT sur deux villes du même cluster spatial = même cluster.
- **Cluster temporel** : fenêtre de settlement ≤ 3 jours d'écart = même cluster.

Cap par cluster : **MAX_CLUSTER_EXPOSURE = 0.06** (6 %). Soit ~1.2× le
cap par-trade, ce qui laisse 2 positions max corrélées sans bloquer le
flow.

Schéma de données minimal (à ajouter dans la signature paper-trade) :

```python
@dataclass
class BetContext:
    bet_id: str
    market_ticker: str            # ex. KXLOWTNYC-26MAY17
    spatial_cluster: str          # ex. "NE"
    settlement_date: date
    fraction_engaged: float       # f calculée par sizing
```

### 2.3 Ordre d'application (Strictest constraint wins)

```
f_kelly_raw      = edge / b
f_kelly_fractional = f_kelly_raw * α              # α = 0.25
f_per_trade_cap  = min(f_kelly_fractional, MAX_FRACTION_PER_BET)   # 0.05
f_heat_cap       = max(0, MAX_PORTFOLIO_HEAT - Σ f_open)            # 0.10 - reste
f_cluster_cap    = max(0, MAX_CLUSTER_EXPOSURE - Σ f_cluster_open)  # 0.06 - reste
f_final          = min(f_per_trade_cap, f_heat_cap, f_cluster_cap)
```

Si `f_final == 0`, le pari est **refusé** (pas redimensionné à epsilon) — la
liquidité partielle introduit du bruit dans le tournoi predictor.

## 3. Tests

```python
# test_portfolio_heat.py
def test_heat_cap_blocks_6th_bet_at_5pct():
    # 5 paris à 5% déjà ouverts → heat = 25%
    # 6e pari proposé à 5% → doit être refusé (heat cap 10%)
    ...

def test_cluster_cap_blocks_correlated_bets():
    # NYC LOWT + Boston LOWT + Philly LOWT, même fenêtre 3j
    # = même cluster NE-spring-front
    # Cap 6% doit bloquer le 3e
    ...

def test_strictest_wins():
    # Configurer un cas où chaque cap est le binding constraint
    ...
```

## 4. Décisions ouvertes

1. **MAX_PORTFOLIO_HEAT à 10 % ou 6-8 %** comme tradermonty ? Justification
   de 10 % : perte max par contrat = `px`, pas la distance entry-stop.
   Sur Kalshi nos pertes max sont déjà bornées plus serré.
2. **Granularité du cluster spatial** : NOAA regions (8 clusters) ou plus fin
   (états, villes-clusters de 200 km) ? Démarrer simple = 8 NOAA regions.
3. **Settlement window 3 j ou 5 j** ? 3 j capture le même front cyclonique,
   5 j capture le régime synoptique. Avis : commencer à 3, élargir si on
   observe sous-corrélation résiduelle.
4. **Comportement quand `f_final = 0`** : refus pur ou redimensionnement
   à `MAX_FRACTION_PER_BET / 2` ? Avis : refus pur, pour ne pas polluer le
   tournoi.

## 5. Conditions d'adoption

- Tests unitaires verts sur les 3 cas ci-dessus
- Backtest sur les 14 jours de données existantes : vérifier que les caps
  n'auraient rien filtré rétroactivement (Phase 1 actuelle est mono-pari/jour
  donc heat ≈ 0). Le RFC anticipe PR A, il ne change rien tant que PR A
  n'est pas mergée.
- Documentation dans `docs/sizing.md` (à créer) : pourquoi 10 % et 6 %,
  pourquoi NOAA regions, pourquoi 3 jours.

## 6. Hors-périmètre

- Promotion d'α de 0.25 vers 0.5 (half-Kelly). À revoir uniquement quand
  N≥100 settled + BSS gate franchi de manière stable. Pour l'instant le
  quart-Kelly est défendable.
- Migration vers Bâle-3 risk-weighted (memo `project_financial_model_v04.md`) :
  reste conditionnée à N≥50-100 et N≥30 par catégorie. Pas avant.

## Références

- [research/external-skills/position-sizer-extract.md](../external-skills/position-sizer-extract.md)
- `Aratea/predictor/src/simulation/sizing.py` (état actuel)
- Memo `project_financial_model_v04.md` (sizing 5 %/pari, full collat 1:1)
- Memo `project_predictor_infra_mature.md` (goulot daily_auto, PR A widen)
- Memo `project_seasonal_phase_b.md` (Tier 1 / Tier 2 saisonnier)

## 7. Historique d'implémentation

Le RFC original a été rédigé avant toute implémentation. Cette section trace
les PRs qui le réalisent, dans l'ordre.

### PR #85 — caps in-memory (mergée le 2026-05-17)

Périmètre livré :

- Module `predictor/src/simulation/clusters.py` (parser ticker Kalshi +
  mapping NOAA 8-régions + `BetContext`)
- Classe `PortfolioHeat` in-memory dans `sizing.py` avec `MAX_PORTFOLIO_HEAT=0.10`,
  `MAX_CLUSTER_EXPOSURE=0.06`, fenêtre 3 jours
- Wrapper `capped_kelly_size()` qui applique l'ordre d'application décrit §2.3
- 36 tests verts (20 sur `clusters`, 11 sur `portfolio_heat`, 5 ajoutés au
  passage sur `sizing.py`)
- Documentation `predictor/docs/sizing.md`

Trois pièges du format ticker Kalshi documentés au passage dans la mémoire
projet (HIGHT vs HIGH par longueur de préfixe, LV ≠ TLV via le `T` du
market type, MIA vs MIAM via longueur du segment date 7 vs 5).

Arbitrage HOU → SE confirmé : cohérent avec la trajectoire Phase B
cyclonique (NOLA / MIA / HOU = cluster Gulf monolithique). La corrélation
Plains saisonnière est de second ordre.

### PR #<N> — câblage `daily_auto` + reconstruction depuis ledger (mergée le 2026-05-<JJ>)

Périmètre livré :

- `PortfolioHeat.from_ledger(ledger_path, bankroll, *, on_unknown_ticker)` :
  reconstruit l'état des paris non-settled depuis `paper_bets.csv` à chaque
  run. Utilise `Ledger.read_all()` existant — une seule source de parsing CSV.
- Helper privé `_bet_context_from_paper_bet` : skip si settled, ValueError
  si ville non mappée, utilise `event_ticker` (sans strike) pour le
  clustering — pas `market_ticker`.
- Guard `bet_id` unique sur `register()` — `ValueError` sur duplicate.
  Idempotent sur un ledger append-only, mais protège contre un bug futur.
- Dans `daily_auto.py` :
  - `_compute_current_bankroll()` : marqué-au-market =
    `SIMULATION["starting_bankroll"] + sum(P&L settled)`. **Fail-fast**
    `RuntimeError` si `< $200` (signal de corruption ledger / bug settle).
  - `_size_with_caps()` : wrapper testable autour de `capped_kelly_size`.
  - Suppression pure de `_adaptive_size_usd` + `SIZE_USD_BASE` +
    `ARATEA_SIZE_USD` (sizing edge-based remplacé par Kelly capé, refus
    pur si caps saturés, aucun redimensionnement à epsilon).
  - `portfolio.register(bet_ctx)` APRÈS confirmation d'écriture au ledger :
    invariant "registered = écrit au disque" préservé.
  - `try/except ValueError` defensive autour de `_size_with_caps` :
    symétrique au validateur `unknown_series` existant, log la ville
    extraite + skip si clustering échoue mid-loop.
  - `report.json` notes incluent `Kelly capped size=$X` +
    `portfolio_heat_after_register=X.X%` (heat prédictive).
- 17 tests supplémentaires (9 `test_portfolio_from_ledger.py` + 1 register
  duplicate + 7 `test_daily_auto_caps_wiring.py`). 53 tests verts au total.

Décisions de design notables :

- **Pas de persistance disque séparée** : la PR « persistance `state.json`
  versionné » envisagée initialement est **abandonnée**. Le ledger
  `paper_bets.csv` est déjà la source de vérité du workflow paper-trade ;
  maintenir un fichier d'état séparé dupliquerait l'information et
  ouvrirait la porte à des désync sans bénéfice net. Reconstruction
  depuis ledger = ~30 lignes, idempotente, pas de versioning de schéma à
  maintenir.
- **Bankroll marqué-au-market** plutôt que statique : la fraction 5 %
  per-trade s'ajuste au capital réel. La fraction des paris pré-câblage
  reflète l'engagement comptable réel (stake_usd / current_bankroll), pas
  une fiction re-sizée. Conséquence assumée : si l'historique sature la
  heat (ex. 2 paris à $100 sur bankroll $909 = 22 %), aucun nouveau pari
  ne sera pris tant que les anciens n'auront pas settle. Gel temporaire =
  comportement correct des caps.
- **Refus pur** non-négociable : `amount_usd == 0` → skip, jamais de
  mini-bet à epsilon, pour ne pas polluer l'évaluation du tournoi
  predictor avec du bruit de remplissage partiel.

### PR A — widen `daily_auto` (déjà mergée en amont, PR #82 + PR #93)

Élargissement du débit de capture (11 events × 3 bins env-overridable,
puis 16 events × 3 bins après le fix multi-series HIGHT). À noter : PR A
avait été planifiée *après* le câblage des caps, mais a finalement mergé
*avant* — PR #<N> remplit le rôle de safeguard rétrospectif. Le débit
théorique est passé de ~1 capture/jour à ~48 captures/jour, les caps
arrivent juste à temps pour absorber cette accélération.

### Évolutions différées hors RFC

Cf. §6 — promotion α 0.25 → 0.5 et migration Bâle-3 risk-weighted restent
conditionnées aux gates statistiques (N≥100 settled / N≥30 par catégorie).
À ré-arbitrer dans un RFC dédié quand les données seront là.
