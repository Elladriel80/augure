# Feature registry — learned predictor

> Augure is not just a Kalshi paper trader. It is a **weather-factor
> discovery engine**. Each row in the table below is a *named hypothesis*
> about what drives the gap between forecast and observation. Each
> training run measures the actual Brier contribution per name. Bets are
> the empirical validation loop.

## Discipline

Every feature on this list MUST have:

1. **A name that evokes a hypothesis.** No `f1`, `x_42`, `meta_8`. Use
   `urban_density_5km`, `forecast_revision_velocity_24h`,
   `evapotranspiration_water_proxy_10km`.
2. **A one-or-two-sentence causal hypothesis.** What atmospheric or
   contextual mechanism are we testing?
3. **An identified source.** URL of the API, path to the dataset, or
   "derived from existing predictions".
4. **A `date_added`.** ISO date.
5. **A measured `brier_delta`.** Filled by `train_learned.py` after each
   run via leave-one-out on the active feature set. Negative is good
   (the model is more accurate *with* this feature present).
6. **A `status`.** One of:
   - `experimental` — added, not yet validated by a training run.
   - `active` — measured Brier improvement, kept in the registry.
   - `dropped` — measured no contribution or negative contribution,
     removed from the spec but kept here for institutional memory.
   - `retired` — superseded by a better feature; kept for context.

## Registry

| name | hypothesis | source | date_added | brier_delta | status |
|---|---|---|---|---|---|
| `p_climatology` | Historical base rate of (variable in [lower, upper]) over the same date-of-year window from the past 15 years. The dumb-but-honest prior every forecast must beat. | derived from `predictors/climatology.py` (Open-Meteo historical) | 2026-05-09 | +0.0020 | active |
| `p_forecast_blend` | Open-Meteo deterministic forecast around target_date, blended with climatology by horizon. Hypothesis: state-of-art deterministic forecast carries calibrated short-horizon signal. | derived from `predictors/forecast_blend.py` | 2026-05-09 | +0.0043 | active |
| `p_ensemble` | Mean of four vendor probabilities (ECMWF + GraphCast + GFS + JMA). Hypothesis: vendor disagreement washes out, the mean is the wisest single bet. (Bench 2026-05-11 N=138: ensemble Brier 0.1429 vs kalshi_mid 0.0845 — the average **lost** to the market, so we need to learn weights instead of averaging blindly.) | derived from `predictors/ensemble.py` | 2026-05-09 | +0.0078 | active |
| `forecast_spread` | Max − min of the per-vendor probabilities (proxy of model disagreement). Hypothesis: when vendors disagree, the prediction is less trustworthy and the market mid carries more weight than the model. | derived from `predictions.ensemble.inputs.individual_probs` | 2026-05-09 | -0.0000 | experimental |
| `days_ahead` | Days between snapshot and target_date. Hypothesis: forecast skill decays with horizon, learned weights should interact non-linearly with this. | derived from `predictions.forecast_blend.inputs.days_ahead` | 2026-05-09 | +0.0000 | experimental |
| `p_nws_ndfd` | P(YES) computed from the NWS NDFD official forecast, gaussian around NDFD temp with sigma from climatology range. Hypothesis: the agency that *resolves* Kalshi weather markets (NWS Climatological Report Daily) should issue the highest-signal forecast available. | `https://api.weather.gov` via `src/forecast/nws_ndfd.py` | 2026-05-11 | TBD (forward-only — no historical coverage yet) | experimental |
| `urban_density_5km` | OSM `way["building"]` count within 5 km of the station. Hypothesis: urban heat island raises overnight lows above what a non-urban climatology predicts → biases low-temp markets in cities. Units: building count (not %-area; see README for why). | OSM Overpass API | 2026-05-11 | -0.0000 | experimental |
| `water_pct_10km` | OSM `natural=water` + `waterway=*` feature count within 10 km. Hypothesis: large water bodies dampen diurnal swings via thermal inertia → tightens the [lower, upper] hit probability for both highs and lows. Units: feature count (kept the `_pct_` name from the spec for continuity). | OSM Overpass API | 2026-05-11 | +0.0000 | experimental |
| `forest_pct_5km` | OSM `natural=wood` + `landuse=forest` feature count within 5 km. Hypothesis: canopy cover lowers daytime highs (shade + evapotranspiration) and limits radiative night cooling (canopy traps). Units: feature count. | OSM Overpass API | 2026-05-11 | +0.0003 | experimental |
| `elevation_m` | USGS EPQS elevation at the station point. Hypothesis: thinner air at altitude amplifies the diurnal swing (Denver KDEN ~1638 m vs. Miami KMIA ~2 m at the extremes of our station set). | USGS EPQS `https://epqs.nationalmap.gov/v1/json` | 2026-05-11 | +0.0001 | experimental |
| `distance_to_coast_km` | Haversine distance to the nearest Natural Earth 1:50m coastline vertex. Hypothesis: maritime regime (Boston, Miami, SFO) damps extremes; continental regime (Denver, Oklahoma City) amplifies them. | Natural Earth `ne_50m_coastline.geojson` | 2026-05-11 | +0.0000 | experimental |
| `latitude` | Station latitude (degrees, signed). Hypothesis: insolation, daylight length, and seasonal amplitude scale with `cos(latitude)` — explicit feature lets the learner discover the interaction with the date-of-year encoded in climatology. | NWS_STATIONS table | 2026-05-11 | +0.0000 | experimental |

## Feature sets

- `FEATURES_V0` (5 features) — the starter set, derived purely from
  existing predictor outputs. Trains on the full historical resolved
  set (~138 rows as of 2026-05-11).
- `FEATURES_V1` (V0 + 1) — adds `p_nws_ndfd`. NDFD has no historical
  archive, so the V1 training set is effectively empty until forward
  captures with NDFD accumulate. Use `--feature-set v1` once that lands.
- `FEATURES_V2` (V0 + 6) — V0 plus the static geographic context
  features. Static = available retroactively on every row, so the V2
  training set matches V0's row count. This is the set wired into the
  first end-to-end training run.

## Updates

`predictor/scripts/train_learned.py` writes a run record to
`predictor/runs_learning/<timestamp_utc>/run.json` and then patches the
`brier_delta` and `status` columns above for every feature in the
training spec. The methodology used to compute `brier_delta` (LOO vs.
standardized coefficient magnitude) is documented in the same run.json
under `methodology`.
