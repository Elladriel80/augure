# RFC â€” Portfolio heat & correlation caps pour Aratea Phase 1

- **Auteur** : @Elladriel80
- **Date initiale** : 2026-05-17
- **Statut** : implÃ©mentÃ© complet â€” caps livrÃ©s (PR #85), cÃ¢blage `daily_auto` + reconstruction depuis ledger livrÃ©s (PR #94)
- **Issu de** : exploration des skills `tradermonty/claude-trading-skills`
  ([research/external-skills/](../external-skills/README.md))
- **Touche** : `predictor/src/simulation/sizing.py`, `predictor/src/simulation/clusters.py`, `predictor/scripts/daily_auto.py`
- **Voir aussi** : Â§7 Â« Historique d'implÃ©mentation Â»

## TL;DR

Le sizing per-trade d'Aratea (`kelly_fractional_size`, quart-Kelly + cap 5 %) est
**dÃ©jÃ  correctement implÃ©mentÃ©** : algÃ©briquement identique Ã  la formule
canonique `tradermonty/position-sizer`, et plus conservateur (Î±=0.25 vs Î±=0.5).

Deux garde-fous **manquent** et apparaissent comme principes-clÃ©s du skill
externe :

1. **Portfolio heat** â€” borner la somme des positions ouvertes Ã  6-8 % du
   bankroll, indÃ©pendamment du sizing per-trade.
2. **Correlation caps** â€” borner l'exposition agrÃ©gÃ©e Ã  un mÃªme *cluster*
   de paris mÃ©tÃ©orologiquement corrÃ©lÃ©s (mÃªme front, mÃªme fenÃªtre, mÃªme
   rÃ©gion).

Sans ces deux garde-fous, l'Ã©largissement prÃ©vu de `daily_auto` (PR A,
multiplicateur Ã—25 sur le dÃ©bit de paris â€” voir memo
`project_dashboard_refonte_pending.md`) ouvre la porte Ã  des sessions oÃ¹
5 paris simultanÃ©s Ã  5 % chacun = 25 % du bankroll exposÃ© au **mÃªme
Ã©vÃ©nement mÃ©tÃ©o sous-jacent**.

## 1. Contexte

### Ã‰tat actuel de `sizing.py`

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

Per-trade : conforme Ã  l'Ã©tat de l'art binaire, quart-Kelly, cap 5 %. RAS.

### Ce que le skill externe rappelle

> "Portfolio heat: Total open risk should not exceed 6-8 % of account equity"
> â€” `position-sizer/SKILL.md`, Key Principle #6

> "Strictest constraint wins" â€” Key Principle #4 ; `max-position-pct`,
> `max-sector-pct`, et `current-sector-exposure` doivent Ãªtre appliquÃ©s
> conjointement.

### Pourquoi maintenant

- PR A (widen `daily_auto`) Ã—25 sur le dÃ©bit. MÃ©moire
  `project_predictor_infra_mature.md` : goulot actuel = `EVENT_SERIES`
  hardcodÃ© NYC LOWT + EDGE 0.10 + SPREAD 0.05. Une fois Ã©largi, plusieurs
  paris simultanÃ©s deviennent la norme.
- Phase A â†’ Phase B : seasonal targets (drought, ouragan x3 triggers,
  4 cibles Tier 1, 6 Tier 2 â€” memo `project_seasonal_phase_b.md`). Les
  contrats saisonniers ont un horizon de 3-12 mois, donc plusieurs paris
  ouverts **en parallÃ¨le pendant plusieurs mois** â€” la concentration cumule
  dans le temps.

## 2. Proposition

### 2.1 Portfolio heat

Ajouter un wrapper `PortfolioHeat` en amont de `kelly_fractional_size` qui :

- Maintient la somme des `f` (fractions de bankroll engagÃ©es) sur les paris
  **non-settled**.
- Refuse un nouveau pari si `Î£ f_open + f_nouveau > MAX_PORTFOLIO_HEAT`.
- Valeur cible **MAX_PORTFOLIO_HEAT = 0.10** (10 %, plus gÃ©nÃ©reux que les
  6-8 % equity car nos payoffs binaires sont dÃ©jÃ  capÃ©s Ã  la baisse â€” perte
  max par contrat = `px`, pas la position ATR-distance equity).

### 2.2 Correlation caps

DÃ©finir un *cluster* de paris mÃ©tÃ©orologiquement corrÃ©lÃ©s.

Heuristique pragmatique en deux dimensions :

- **Cluster spatial** : rÃ©gions climatiques NOAA (NE, SE, MW, NW, SW, Plains, AK, HI).
  Deux paris LOWT sur deux villes du mÃªme cluster spatial = mÃªme cluster.
- **Cluster temporel** : fenÃªtre de settlement â‰¤ 3 jours d'Ã©cart = mÃªme cluster.

Cap par cluster : **MAX_CLUSTER_EXPOSURE = 0.06** (6 %). Soit ~1.2Ã— le
cap par-trade, ce qui laisse 2 positions max corrÃ©lÃ©es sans bloquer le
flow.

SchÃ©ma de donnÃ©es minimal (Ã  ajouter dans la signature paper-trade) :

```python
@dataclass
class BetContext:
    bet_id: str
    market_ticker: str            # ex. KXLOWTNYC-26MAY17
    spatial_cluster: str          # ex. "NE"
    settlement_date: date
    fraction_engaged: float       # f calculÃ©e par sizing
```

### 2.3 Ordre d'application (Strictest constraint wins)

```
f_kelly_raw      = edge / b
f_kelly_fractional = f_kelly_raw * Î±              # Î± = 0.25
f_per_trade_cap  = min(f_kelly_fractional, MAX_FRACTION_PER_BET)   # 0.05
f_heat_cap       = max(0, MAX_PORTFOLIO_HEAT - Î£ f_open)            # 0.10 - reste
f_cluster_cap    = max(0, MAX_CLUSTER_EXPOSURE - Î£ f_cluster_open)  # 0.06 - reste
f_final          = min(f_per_trade_cap, f_heat_cap, f_cluster_cap)
```

Si `f_final == 0`, le pari est **refusÃ©** (pas redimensionnÃ© Ã  epsilon) â€” la
liquiditÃ© partielle introduit du bruit dans le tournoi predictor.

## 3. Tests

```python
# test_portfolio_heat.py
def test_heat_cap_blocks_6th_bet_at_5pct():
    # 5 paris Ã  5% dÃ©jÃ  ouverts â†’ heat = 25%
    # 6e pari proposÃ© Ã  5% â†’ doit Ãªtre refusÃ© (heat cap 10%)
    ...

def test_cluster_cap_blocks_correlated_bets():
    # NYC LOWT + Boston LOWT + Philly LOWT, mÃªme fenÃªtre 3j
    # = mÃªme cluster NE-spring-front
    # Cap 6% doit bloquer le 3e
    ...

def test_strictest_wins():
    # Configurer un cas oÃ¹ chaque cap est le binding constraint
    ...
```

## 4. DÃ©cisions ouvertes

1. **MAX_PORTFOLIO_HEAT Ã  10 % ou 6-8 %** comme tradermonty ? Justification
   de 10 % : perte max par contrat = `px`, pas la distance entry-stop.
   Sur Kalshi nos pertes max sont dÃ©jÃ  bornÃ©es plus serrÃ©.
2. **GranularitÃ© du cluster spatial** : NOAA regions (8 clusters) ou plus fin
   (Ã©tats, villes-clusters de 200 km) ? DÃ©marrer simple = 8 NOAA regions.
3. **Settlement window 3 j ou 5 j** ? 3 j capture le mÃªme front cyclonique,
   5 j capture le rÃ©gime synoptique. Avis : commencer Ã  3, Ã©largir si on
   observe sous-corrÃ©lation rÃ©siduelle.
4. **Comportement quand `f_final = 0`** : refus pur ou redimensionnement
   Ã  `MAX_FRACTION_PER_BET / 2` ? Avis : refus pur, pour ne pas polluer le
   tournoi.

## 5. Conditions d'adoption

- Tests unitaires verts sur les 3 cas ci-dessus
- Backtest sur les 14 jours de donnÃ©es existantes : vÃ©rifier que les caps
  n'auraient rien filtrÃ© rÃ©troactivement (Phase 1 actuelle est mono-pari/jour
  donc heat â‰ˆ 0). Le RFC anticipe PR A, il ne change rien tant que PR A
  n'est pas mergÃ©e.
- Documentation dans `docs/sizing.md` (Ã  crÃ©er) : pourquoi 10 % et 6 %,
  pourquoi NOAA regions, pourquoi 3 jours.

## 6. Hors-pÃ©rimÃ¨tre

- Promotion d'Î± de 0.25 vers 0.5 (half-Kelly). Ã€ revoir uniquement quand
  Nâ‰¥100 settled + BSS gate franchi de maniÃ¨re stable. Pour l'instant le
  quart-Kelly est dÃ©fendable.
- Migration vers BÃ¢le-3 risk-weighted (memo `project_financial_model_v04.md`) :
  reste conditionnÃ©e Ã  Nâ‰¥50-100 et Nâ‰¥30 par catÃ©gorie. Pas avant.

## RÃ©fÃ©rences

- [research/external-skills/position-sizer-extract.md](../external-skills/position-sizer-extract.md)
- `Aratea/predictor/src/simulation/sizing.py` (Ã©tat actuel)
- Memo `project_financial_model_v04.md` (sizing 5 %/pari, full collat 1:1)
- Memo `project_predictor_infra_mature.md` (goulot daily_auto, PR A widen)
- Memo `project_seasonal_phase_b.md` (Tier 1 / Tier 2 saisonnier)

## 7. Historique d'implÃ©mentation

Le RFC original a Ã©tÃ© rÃ©digÃ© avant toute implÃ©mentation. Cette section trace
les PRs qui le rÃ©alisent, dans l'ordre.

### PR #85 â€” caps in-memory (mergÃ©e le 2026-05-17)

PÃ©rimÃ¨tre livrÃ© :

- Module `predictor/src/simulation/clusters.py` (parser ticker Kalshi +
  mapping NOAA 8-rÃ©gions + `BetContext`)
- Classe `PortfolioHeat` in-memory dans `sizing.py` avec `MAX_PORTFOLIO_HEAT=0.10`,
  `MAX_CLUSTER_EXPOSURE=0.06`, fenÃªtre 3 jours
- Wrapper `capped_kelly_size()` qui applique l'ordre d'application dÃ©crit Â§2.3
- 36 tests verts (20 sur `clusters`, 11 sur `portfolio_heat`, 5 ajoutÃ©s au
  passage sur `sizing.py`)
- Documentation `predictor/docs/sizing.md`

Trois piÃ¨ges du format ticker Kalshi documentÃ©s au passage dans la mÃ©moire
projet (HIGHT vs HIGH par longueur de prÃ©fixe, LV â‰  TLV via le `T` du
market type, MIA vs MIAM via longueur du segment date 7 vs 5).

Arbitrage HOU â†’ SE confirmÃ© : cohÃ©rent avec la trajectoire Phase B
cyclonique (NOLA / MIA / HOU = cluster Gulf monolithique). La corrÃ©lation
Plains saisonniÃ¨re est de second ordre.

### PR #94 â€” cÃ¢blage `daily_auto` + reconstruction depuis ledger (mergÃ©e le 2026-05-17)

PÃ©rimÃ¨tre livrÃ© :

- `PortfolioHeat.from_ledger(ledger_path, bankroll, *, on_unknown_ticker)` :
  reconstruit l'Ã©tat des paris non-settled depuis `paper_bets.csv` Ã  chaque
  run. Utilise `Ledger.read_all()` existant â€” une seule source de parsing CSV.
- Helper privÃ© `_bet_context_from_paper_bet` : skip si settled, ValueError
  si ville non mappÃ©e, utilise `event_ticker` (sans strike) pour le
  clustering â€” pas `market_ticker`.
- Guard `bet_id` unique sur `register()` â€” `ValueError` sur duplicate.
  Idempotent sur un ledger append-only, mais protÃ¨ge contre un bug futur.
- Dans `daily_auto.py` :
  - `_compute_current_bankroll()` : marquÃ©-au-market =
    `SIMULATION["starting_bankroll"] + sum(P&L settled)`. **Fail-fast**
    `RuntimeError` si `< $200` (signal de corruption ledger / bug settle).
  - `_size_with_caps()` : wrapper testable autour de `capped_kelly_size`.
  - Suppression pure de `_adaptive_size_usd` + `SIZE_USD_BASE` +
    `ARATEA_SIZE_USD` (sizing edge-based remplacÃ© par Kelly capÃ©, refus
    pur si caps saturÃ©s, aucun redimensionnement Ã  epsilon).
  - `portfolio.register(bet_ctx)` APRÃˆS confirmation d'Ã©criture au ledger :
    invariant "registered = Ã©crit au disque" prÃ©servÃ©.
  - `try/except ValueError` defensive autour de `_size_with_caps` :
    symÃ©trique au validateur `unknown_series` existant, log la ville
    extraite + skip si clustering Ã©choue mid-loop.
  - `report.json` notes incluent `Kelly capped size=$X` +
    `portfolio_heat_after_register=X.X%` (heat prÃ©dictive).
- 17 tests supplÃ©mentaires (9 `test_portfolio_from_ledger.py` + 1 register
  duplicate + 7 `test_daily_auto_caps_wiring.py`). 53 tests verts au total.

DÃ©cisions de design notables :

- **Pas de persistance disque sÃ©parÃ©e** : la PR Â« persistance `state.json`
  versionnÃ© Â» envisagÃ©e initialement est **abandonnÃ©e**. Le ledger
  `paper_bets.csv` est dÃ©jÃ  la source de vÃ©ritÃ© du workflow paper-trade ;
  maintenir un fichier d'Ã©tat sÃ©parÃ© dupliquerait l'information et
  ouvrirait la porte Ã  des dÃ©sync sans bÃ©nÃ©fice net. Reconstruction
  depuis ledger = ~30 lignes, idempotente, pas de versioning de schÃ©ma Ã 
  maintenir.
- **Bankroll marquÃ©-au-market** plutÃ´t que statique : la fraction 5 %
  per-trade s'ajuste au capital rÃ©el. La fraction des paris prÃ©-cÃ¢blage
  reflÃ¨te l'engagement comptable rÃ©el (stake_usd / current_bankroll), pas
  une fiction re-sizÃ©e. ConsÃ©quence assumÃ©e : si l'historique sature la
  heat (ex. 2 paris Ã  $100 sur bankroll $909 = 22 %), aucun nouveau pari
  ne sera pris tant que les anciens n'auront pas settle. Gel temporaire =
  comportement correct des caps.
- **Refus pur** non-nÃ©gociable : `amount_usd == 0` â†’ skip, jamais de
  mini-bet Ã  epsilon, pour ne pas polluer l'Ã©valuation du tournoi
  predictor avec du bruit de remplissage partiel.

### PR A â€” widen `daily_auto` (dÃ©jÃ  mergÃ©e en amont, PR #82 + PR #93)

Ã‰largissement du dÃ©bit de capture (11 events Ã— 3 bins env-overridable,
puis 16 events Ã— 3 bins aprÃ¨s le fix multi-series HIGHT). Ã€ noter : PR A
avait Ã©tÃ© planifiÃ©e *aprÃ¨s* le cÃ¢blage des caps, mais a finalement mergÃ©
*avant* â€” PR #94 remplit le rÃ´le de safeguard rÃ©trospectif. Le dÃ©bit
thÃ©orique est passÃ© de ~1 capture/jour Ã  ~48 captures/jour, les caps
arrivent juste Ã  temps pour absorber cette accÃ©lÃ©ration.

### Ã‰volutions diffÃ©rÃ©es hors RFC

Cf. Â§6 â€” promotion Î± 0.25 â†’ 0.5 et migration BÃ¢le-3 risk-weighted restent
conditionnÃ©es aux gates statistiques (Nâ‰¥100 settled / Nâ‰¥30 par catÃ©gorie).
Ã€ rÃ©-arbitrer dans un RFC dÃ©diÃ© quand les donnÃ©es seront lÃ .
