# predictor/runs_backtest/

Append-only record of every replay run produced by
[`predictor/scripts/backtest.py`](../scripts/backtest.py). Each settled
Kalshi market that the backtester touches is written here as a
self-contained record, mirroring the philosophy of
[`predictor/runs/`](../runs/) for live captures.

Backtest output is intentionally separated from live output so that the
Phase 1 go / no-go gate (`N > 50` resolved live runs, meta beats both the
best individual model and climatology) cannot be silently inflated by
replay volume. Backtest contributes to a *hybrid* effective sample
size, weighted lower than live (see *Hybrid weighting* below).

---

## Layout

```
predictor/runs_backtest/
├── README.md                       this file
├── 2025-12-15/                     one folder per as_of_date
│   ├── 0001/
│   │   └── report.json             schema "2-backtest"
│   ├── 0002/
│   │   └── report.json
│   └── ...
└── 2025-12-16/
    └── ...
```

The companion ledger is at
[`../data/ledger/paper_bets_backtest.csv`](../data/ledger/) — one row per
record for flat dashboard aggregation.

## report.json — schema "2-backtest"

The backtest schema is deliberately a **distinct variant** of the live
schema v2, not a copy with sentinel values. Live-only fields
(`champion_position`, `ledger_bet_id`, `paper`, `snapshot_pre`) are
removed; backtest-only fields (`as_of_date`, `target_date`,
`horizon_days`, `mode`, `snapshot_at_as_of` with archive-availability
note) are added. The dashboard renderer must branch on
`schema_version == "2-backtest"`.

Key fields:

- `type`: always `"backtest"`.
- `mode`: `replay_climatology` for the strict point-in-time path;
  `replay_naive_<predictor>` for opt-in ensemble / forecast_blend runs
  (see *NAIVE mode* below).
- `as_of_date` / `target_date` / `horizon_days`: the replayed prediction
  timing. `as_of_date = target_date - horizon_days`.
- `models[].inputs_summary.point_in_time`: `true` only for `climatology`.
  Always check this before trusting the per-model Brier.
- `markets[].snapshot_at_as_of`: kept structurally but populated with
  `null` and a `note` — Kalshi historical orderbook is not archived in
  this pipeline. Only the settled outcome is known. No `edge_vs_mid` is
  computed in backtest.
- `markets[].resolution.known`: always `true` (the backtester only
  touches settled markets).
- `scoring.by_model[name].brier` / `log_loss`: per-record metrics.

## NAIVE mode — ensemble & forecast_blend

`EnsemblePredictor` and `ForecastBlendPredictor` call the vendor weather
forecast at runtime. For an `as_of_date` in the past, the forecast they
fetch is **today's**, not the one that would have been available on
`as_of_date`. This is not point-in-time.

Running these predictors via backtest therefore requires the explicit
`--include-ensemble` flag, which:

1. Allows the run.
2. Sets `models[0].inputs_summary.naive_uses_current_forecast = true`.
3. Writes a loud warning into the report's `notes`.
4. Marks `mode` as `replay_naive_<predictor>`.

Their Brier scores in this mode are a **soft benchmark**, not a clean
measurement. Use them to compare against `climatology` knowing the
direction is right but the magnitude is biased toward optimism (the
"forecast" had perfect short-term lookahead from the dashboard's
perspective).

A true point-in-time backtest for ensemble would require archiving
vendor forecasts as they are issued — a future capability, not in this
PR.

## paper_bets_backtest.csv

Flat ledger, one row per (record × model), columns:

```
backtest_id, replayed_at_utc, as_of_date, target_date, market_ticker,
event_ticker, series, model, method, prob_model, outcome, brier,
log_loss, mode
```

Useful for SQL-style aggregation in the dashboard (`GROUP BY model,
mode, series, as_of_date_quarter`).

## Hybrid weighting

The Phase 1 gate is `N > 50` resolved **live** runs with the meta
beating both the best single model and climatology. Backtest does not
substitute for live runs but provides an effective-sample boost for
secondary decisions (challenger promotion threshold, feature-set
selection).

The proposed formula:

```
N_effective = N_live + alpha * N_backtest
```

with `alpha = 0.3` as the default discount factor. This number is **not
yet ratified** in [`predictor/runs/CONVENTION.md`](../runs/CONVENTION.md)
§6 — that ratification is a separate PR. Until then, backtest aggregates
shown in the dashboard are informational only and must not be used to
edit `CHAMPION.json` or to declare the Phase 1 gate met.

---

# predictor/runs_backtest/ (FR)

Trace append-only de chaque run de replay produit par
[`predictor/scripts/backtest.py`](../scripts/backtest.py). Chaque market
Kalshi résolu touché par le backtester est écrit ici comme un record
auto-contenu, sur le même principe que
[`predictor/runs/`](../runs/) pour les captures live.

La sortie backtest est volontairement séparée du live pour que le gate
Phase 1 (`N > 50` runs live résolus, meta bat le meilleur modèle individuel
et la climatologie) ne puisse pas être gonflé silencieusement par du
volume replay. Le backtest alimente une taille d'échantillon *hybride*
pondérée plus bas que le live (voir *Pondération hybride* ci-dessous).

## Disposition

```
predictor/runs_backtest/
├── README.md                       ce fichier
├── 2025-12-15/                     un dossier par as_of_date
│   ├── 0001/
│   │   └── report.json             schema "2-backtest"
│   ├── 0002/
│   │   └── report.json
│   └── ...
└── 2025-12-16/
    └── ...
```

Le ledger associé est dans
[`../data/ledger/paper_bets_backtest.csv`](../data/ledger/) — une ligne
par record pour l'agrégation à plat côté dashboard.

## report.json — schema "2-backtest"

Le schema backtest est volontairement une **variante distincte** du
schema v2 live, pas une copie avec valeurs sentinelles. Les champs
live-only (`champion_position`, `ledger_bet_id`, `paper`,
`snapshot_pre`) sont retirés ; les champs backtest-only (`as_of_date`,
`target_date`, `horizon_days`, `mode`, `snapshot_at_as_of` avec note
sur la disponibilité d'archive) sont ajoutés. Le renderer du dashboard
doit faire un branchement sur `schema_version == "2-backtest"`.

Champs clés :

- `type` : toujours `"backtest"`.
- `mode` : `replay_climatology` pour le chemin strict point-in-time ;
  `replay_naive_<predictor>` pour les runs ensemble / forecast_blend en
  opt-in (voir *Mode NAIVE* ci-dessous).
- `as_of_date` / `target_date` / `horizon_days` : timing de la prédiction
  rejouée. `as_of_date = target_date - horizon_days`.
- `models[].inputs_summary.point_in_time` : `true` uniquement pour
  `climatology`. Toujours vérifier avant de faire confiance au Brier
  par modèle.
- `markets[].snapshot_at_as_of` : conservé structurellement mais peuplé
  avec `null` et une `note` — l'orderbook historique Kalshi n'est pas
  archivé dans ce pipeline. Seul l'outcome réglé est connu. Pas de
  `edge_vs_mid` calculé en backtest.
- `markets[].resolution.known` : toujours `true` (le backtester ne
  touche que des markets réglés).
- `scoring.by_model[nom].brier` / `log_loss` : métriques par record.

## Mode NAIVE — ensemble & forecast_blend

`EnsemblePredictor` et `ForecastBlendPredictor` appellent le forecast
météo du fournisseur à l'exécution. Pour une `as_of_date` dans le passé,
le forecast récupéré est **celui d'aujourd'hui**, pas celui qui aurait
été disponible à `as_of_date`. Ce n'est pas point-in-time.

Lancer ces predictors via backtest nécessite donc le flag explicite
`--include-ensemble`, qui :

1. Autorise le run.
2. Met `models[0].inputs_summary.naive_uses_current_forecast = true`.
3. Écrit un warning bruyant dans les `notes` du report.
4. Marque `mode` comme `replay_naive_<predictor>`.

Leurs scores de Brier dans ce mode sont un **benchmark mou**, pas une
mesure propre. À utiliser pour comparer contre `climatology` en sachant
que la direction est juste mais la magnitude biaisée vers l'optimisme
(le "forecast" avait un look-ahead court-terme parfait du point de vue
du dashboard).

Un vrai backtest point-in-time pour ensemble nécessiterait d'archiver
les forecasts fournisseurs à mesure qu'ils sont émis — capacité future,
hors de cette PR.

## paper_bets_backtest.csv

Ledger à plat, une ligne par (record × modèle), colonnes :

```
backtest_id, replayed_at_utc, as_of_date, target_date, market_ticker,
event_ticker, series, model, method, prob_model, outcome, brier,
log_loss, mode
```

Utile pour l'agrégation type SQL côté dashboard (`GROUP BY model,
mode, series, as_of_date_quarter`).

## Pondération hybride

Le gate Phase 1 est `N > 50` runs live résolus avec la meta battant le
meilleur modèle individuel et la climatologie. Le backtest ne substitue
pas au live mais fournit un boost d'échantillon effectif pour des
décisions secondaires (seuil de promotion des challengers, sélection
des feature sets).

Formule proposée :

```
N_effective = N_live + alpha * N_backtest
```

avec `alpha = 0.3` comme facteur de discount par défaut. Ce nombre
**n'est pas encore ratifié** dans
[`predictor/runs/CONVENTION.md`](../runs/CONVENTION.md) §6 — cette
ratification est une PR séparée. Jusque-là, les agrégats backtest
montrés dans le dashboard sont informationnels uniquement et ne doivent
pas être utilisés pour éditer `CHAMPION.json` ou déclarer le gate
Phase 1 atteint.
