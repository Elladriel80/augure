"""Backtest : run le predictor sur des events Kalshi DÉJÀ RÉSOLUS et mesure l'accuracy.

Pour chaque event settled :
- pour chaque market (bin), prédit P(OUI) avec UNIQUEMENT des données antérieures
  à la date de résolution (pas de leakage)
- compare à l'outcome réel (yes/no) du market
- agrège accuracy, Brier score, log loss

Deux sorties :
1. `data/backtests/backtest_<predictor>_<ts>.json` — rapport global agrégé (legacy).
2. `runs_backtest/<as_of_date>/<seq>/report.json` — un fichier par market backtest,
   schema v2-backtest distinct, aligné conceptuellement avec runs/<NNN>/report.json
   du live mais sans champs orphelins (champion_position, ledger_bet_id, etc.).
   + `data/ledger/paper_bets_backtest.csv` ledger plat pour agrégats dashboard.

Le ledger backtest est conçu pour permettre le calcul d'un N_effective hybride
pondéré : `N_eff = N_live + alpha * N_backtest` (α=0.3 par défaut, à figer
dans `runs/CONVENTION.md` §6 par PR séparé).

Note sur le perimeter point-in-time strict :
- `climatology` est strict (years_back glissant, exclut as_of_date).
- `ensemble` et `forecast_blend` appellent un forecast CURRENT (pas archivé pour
  des dates historiques) — utilisable en backtest uniquement en mode "naive"
  via --include-ensemble, qui ajoute un warning loud et marque le mode dans le
  report.

Usage:
    python scripts/backtest.py [--series KXHIGHAUS,KXLOWTAUS] [--limit 30]
    python scripts/backtest.py --include-ensemble  # ajoute ensemble (NAIVE, voir doc)
    python scripts/backtest.py --no-per-record     # désactive runs_backtest/ + ledger
"""
from __future__ import annotations
import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from src.kalshi import KalshiClient
from src.kalshi.models import Event
from src.predictors import (
    ClimatologyPredictor,
    ForecastBlendPredictor,
    parse_market,
)
from src.predictors.ensemble import EnsemblePredictor
from src.predictors.parsers import SERIES_MAP
from src.simulation.scoring import aggregate_metrics, event_top1_accuracy


DEFAULT_SERIES = list(SERIES_MAP.keys())[:6]  # 6 séries par défaut pour ne pas spammer

# Per-record output paths (additive: legacy global JSON is still written)
RUNS_BACKTEST_DIR = ROOT / "runs_backtest"
LEDGER_BACKTEST_PATH = ROOT / "data" / "ledger" / "paper_bets_backtest.csv"

# Default horizon between as_of_date and target_date for daily Kalshi weather.
# Kalshi daily temp markets settle the day after the observation; in practice
# you'd capture ~24h ahead of settle.
DEFAULT_HORIZON_DAYS = 1


def _ledger_fieldnames() -> list[str]:
    return [
        "backtest_id",
        "replayed_at_utc",
        "as_of_date",
        "target_date",
        "market_ticker",
        "event_ticker",
        "series",
        "model",
        "method",
        "prob_model",
        "outcome",
        "brier",
        "log_loss",
        "mode",
    ]


def _next_backtest_id(as_of_date: str) -> str:
    """Sequential id under runs_backtest/<as_of_date>/. Format: '0001', '0002', ...

    Scoped per-day so re-runs on the same as_of_date keep the numbering local.
    """
    day_dir = RUNS_BACKTEST_DIR / as_of_date
    if not day_dir.exists():
        return "0001"
    existing = []
    for d in day_dir.iterdir():
        if not d.is_dir():
            continue
        try:
            existing.append(int(d.name))
        except ValueError:
            continue
    next_n = (max(existing) + 1) if existing else 1
    return f"{next_n:04d}"


def _safe_log_loss(p: float, outcome: int) -> Optional[float]:
    """Per-record log loss, clamped to avoid log(0)."""
    import math
    eps = 1e-12
    p_clamped = max(eps, min(1.0 - eps, p))
    if outcome == 1:
        return -math.log(p_clamped)
    return -math.log(1.0 - p_clamped)


def _brier(p: float, outcome: int) -> float:
    return float((p - outcome) ** 2)


def _write_backtest_report(
    as_of_date: str,
    target_date: str,
    ev,
    market,
    spec,
    series_ticker: str,
    p_model: float,
    outcome: int,
    predictor_name: str,
    method: str,
    mode: str,
    horizon_days: int,
    ensemble_naive_warning: bool,
) -> str:
    """Write runs_backtest/<as_of_date>/<seq>/report.json (schema v2-backtest).

    Returns the assigned backtest_id (e.g. 'backtest_20251215_0001').
    """
    seq = _next_backtest_id(as_of_date)
    run_dir = RUNS_BACKTEST_DIR / as_of_date / seq
    run_dir.mkdir(parents=True, exist_ok=True)
    ts_replay = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    backtest_id = f"backtest_{as_of_date.replace('-', '')}_{seq}"

    brier = _brier(p_model, outcome)
    ll = _safe_log_loss(p_model, outcome)

    notes_parts = [
        f"Backtest replay at as_of_date={as_of_date}, target_date={target_date}, "
        f"horizon={horizon_days}d.",
        f"Predictor {predictor_name} (method={method}).",
    ]
    if ensemble_naive_warning:
        notes_parts.append(
            "WARNING: ensemble/forecast_blend run in NAIVE mode — these methods "
            "call a CURRENT vendor forecast, not an archived as_of_date forecast. "
            "Treat their backtest Brier as a soft signal, not a clean "
            "point-in-time measurement."
        )
    notes = " ".join(notes_parts)

    report = {
        "schema_version": "2-backtest",
        "run_id": backtest_id,
        "type": "backtest",
        "mode": mode,
        "ts_replay_utc": ts_replay,
        "as_of_date": as_of_date,
        "target_date": target_date,
        "horizon_days": horizon_days,
        "event": {
            "ticker": ev.event_ticker,
            "title": getattr(ev, "title", None),
            "series": series_ticker,
            "target_market_ticker": market.ticker,
            "resolution_source": "Kalshi settled market.result (NWS-tied)",
        },
        "models": [
            {
                "name": predictor_name,
                "role": "backtest",
                "method": method,
                "p_yes": float(p_model),
                "feature_set": None,
                "trained_at": None,
                "inputs_summary": {
                    "method": method,
                    "point_in_time": method == "climatology",
                    "cutoff_date_exclusive": as_of_date if method == "climatology" else None,
                    "naive_uses_current_forecast": method != "climatology",
                },
            }
        ],
        "markets": [
            {
                "platform": "kalshi",
                "ticker": market.ticker,
                "spec": spec.describe(),
                "subtitle": getattr(market, "subtitle", None),
                "snapshot_at_as_of": {
                    "yes_bid": None,
                    "yes_ask": None,
                    "yes_mid": None,
                    "note": ("Kalshi historical orderbook not archived in this "
                             "backtest pipeline; only settled outcome is known. "
                             "No edge_vs_mid computed."),
                },
                "predictions_by_model": {predictor_name: float(p_model)},
                "resolution": {
                    "known": True,
                    "outcome": "yes" if outcome == 1 else "no",
                    "outcome_int": outcome,
                    "winning_bin_ticker": (
                        market.ticker if outcome == 1 else None
                    ),
                    "settled_at": None,
                },
            }
        ],
        "scoring": {
            "by_model": {
                predictor_name: {
                    "role": "backtest",
                    "method": method,
                    "p_yes": float(p_model),
                    "brier": float(brier),
                    "log_loss": (None if ll is None else float(ll)),
                    "won": bool(outcome == 1 and p_model >= 0.5)
                            or bool(outcome == 0 and p_model < 0.5),
                }
            }
        },
        "notes": notes,
    }
    (run_dir / "report.json").write_text(
        json.dumps(report, indent=2, default=str), encoding="utf-8"
    )
    return backtest_id


def _append_backtest_ledger_row(row: dict) -> None:
    """Append one row to paper_bets_backtest.csv, creating header if missing."""
    fieldnames = _ledger_fieldnames()
    write_header = not LEDGER_BACKTEST_PATH.exists()
    LEDGER_BACKTEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER_BACKTEST_PATH.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        for k in fieldnames:
            row.setdefault(k, "")
        writer.writerow(row)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--series", type=str, default=",".join(DEFAULT_SERIES),
        help="Tickers de séries à backtester (séparés par virgules)",
    )
    parser.add_argument("--predictor", choices=["climatology", "forecast_blend", "ensemble"],
                        default="climatology",
                        help="climatology = strict point-in-time (recommandé). "
                             "forecast_blend / ensemble = mode NAIVE car appellent "
                             "le forecast CURRENT, pas archivé pour as_of_date — "
                             "à n'utiliser qu'avec --include-ensemble explicite.")
    parser.add_argument("--limit", type=int, default=20,
                        help="Limite d'events settled par série")
    parser.add_argument("--years-back", type=int, default=15)
    parser.add_argument("--include-ensemble", action="store_true",
                        help="Autorise --predictor forecast_blend ou ensemble. "
                             "Sans ce flag, ces predictors lèvent une erreur "
                             "pour éviter un backtest non point-in-time silencieux.")
    parser.add_argument("--no-per-record", action="store_true",
                        help="Désactive l'écriture runs_backtest/<as_of>/<id>/ "
                             "et le ledger paper_bets_backtest.csv. Utile pour "
                             "un dry-run agrégat sans polluer le filesystem.")
    parser.add_argument("--horizon-days", type=int, default=DEFAULT_HORIZON_DAYS,
                        help=f"Décalage as_of_date = target_date - horizon_days. "
                             f"Défaut {DEFAULT_HORIZON_DAYS} (Kalshi daily temp).")
    args = parser.parse_args()

    # Hard gate: forecast_blend / ensemble are not strict point-in-time.
    if args.predictor != "climatology" and not args.include_ensemble:
        print(f"!! --predictor {args.predictor} is NOT point-in-time for historical "
              f"backtests (it calls the CURRENT vendor forecast).")
        print("   Pass --include-ensemble explicitly if you want a NAIVE backtest "
              "for benchmark comparison only. Otherwise use --predictor climatology.")
        return 2

    ensemble_naive_warning = args.predictor != "climatology"
    write_per_record = not args.no_per_record
    if write_per_record:
        print(f">> Per-record output: runs_backtest/<as_of>/<id>/report.json + "
              f"ledger {LEDGER_BACKTEST_PATH.name}")
    else:
        print(">> Per-record output DISABLED (--no-per-record). Global JSON only.")

    series_list = [s.strip() for s in args.series.split(",") if s.strip()]
    print(f">> Séries: {series_list}")
    print(f">> Predictor: {args.predictor} | years_back: {args.years_back}")

    if args.predictor == "climatology":
        predictor = ClimatologyPredictor(years_back=args.years_back)
    elif args.predictor == "forecast_blend":
        predictor = ForecastBlendPredictor(years_back=args.years_back)
    else:  # ensemble
        predictor = EnsemblePredictor(years_back=args.years_back)

    client = KalshiClient()
    all_records = []      # liste de dicts pour aggregate_metrics
    event_groups = []     # liste de listes pour top-1 accuracy
    per_series = defaultdict(list)

    for series_ticker in series_list:
        print(f"\n>> Pulling settled events for {series_ticker}...")
        try:
            events = list(client.list_events(
                series_ticker=series_ticker, status="settled", with_nested_markets=True,
            ))
        except Exception as e:
            print(f"   !! erreur: {e}")
            continue
        events = events[: args.limit]
        print(f"   {len(events)} events à backtester")

        for ev in events:
            event_records = []
            # Parallel list of refs to (ev, market, spec, series_ticker) so we can
            # write per-record reports AFTER the mutual-exclusivity normalization
            # below without losing the object handles.
            event_record_refs: list[tuple] = []
            for market in ev.markets:
                if market.result not in ("yes", "no"):
                    continue
                # Align with daily_auto._select_target_bins: only consider central
                # bins (strike_type == "between"). Tail bins ("X° or below",
                # "X° or above") represent cumulative probability mass and would
                # dominate the per-event mutual-exclusivity normalization below —
                # collapsing top-1 onto a tail and exploding the Brier on central
                # outcomes (observed BSS = -0.31 on 2026-05-17 smoke before this
                # filter was added).
                raw = next(
                    (r for r in (ev.raw.get("markets") or [])
                     if r.get("ticker") == market.ticker),
                    None,
                )
                if raw is None or raw.get("strike_type") != "between":
                    continue
                spec = parse_market(market)
                if spec is None:
                    continue
                try:
                    pred = predictor.predict(spec)
                except Exception as e:
                    print(f"   [err] {market.ticker} — {e}")
                    continue
                outcome = 1 if market.result == "yes" else 0
                rec = {
                    "ticker": market.ticker,
                    "event_ticker": ev.event_ticker,
                    "spec": spec.describe(),
                    "subtitle": market.subtitle,
                    "prob_yes": pred.prob_yes,
                    "outcome": outcome,
                    "method": pred.method,
                    "series": series_ticker,
                }
                event_records.append(rec)
                event_record_refs.append((ev, market, spec, series_ticker))

            # Normaliser par event mutuellement exclusif
            if event_records and ev.mutually_exclusive:
                s = sum(r["prob_yes"] for r in event_records)
                if s > 0:
                    for r in event_records:
                        r["prob_yes"] = r["prob_yes"] / s

            # Write per-record backtest report + ledger row (post-normalization,
            # so the prob_yes persisted matches what the global aggregator sees).
            if event_records and write_per_record:
                mode = (
                    "replay_climatology"
                    if args.predictor == "climatology"
                    else f"replay_naive_{args.predictor}"
                )
                ts_now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                for rec, (ev_ref, market_ref, spec_ref, series_ref) in zip(
                    event_records, event_record_refs
                ):
                    # Compute as_of_date = target_date - horizon_days (default 1d).
                    try:
                        target_date_obj = spec_ref.target_date
                        if hasattr(target_date_obj, "isoformat"):
                            target_date_iso = target_date_obj.isoformat()
                            as_of_date_iso = (
                                target_date_obj - timedelta(days=args.horizon_days)
                            ).isoformat()
                        else:
                            target_date_iso = str(target_date_obj)
                            as_of_date_iso = target_date_iso  # fallback, no shift
                    except Exception:
                        target_date_iso = "unknown"
                        as_of_date_iso = "unknown"

                    brier_val = _brier(rec["prob_yes"], rec["outcome"])
                    ll_val = _safe_log_loss(rec["prob_yes"], rec["outcome"])
                    try:
                        backtest_id = _write_backtest_report(
                            as_of_date=as_of_date_iso,
                            target_date=target_date_iso,
                            ev=ev_ref,
                            market=market_ref,
                            spec=spec_ref,
                            series_ticker=series_ref,
                            p_model=rec["prob_yes"],
                            outcome=rec["outcome"],
                            predictor_name=args.predictor,
                            method=rec["method"],
                            mode=mode,
                            horizon_days=args.horizon_days,
                            ensemble_naive_warning=ensemble_naive_warning,
                        )
                    except Exception as e:
                        print(f"   [warn] could not write per-record report for "
                              f"{market_ref.ticker}: {e}")
                        continue
                    try:
                        _append_backtest_ledger_row({
                            "backtest_id": backtest_id,
                            "replayed_at_utc": ts_now_utc,
                            "as_of_date": as_of_date_iso,
                            "target_date": target_date_iso,
                            "market_ticker": market_ref.ticker,
                            "event_ticker": ev_ref.event_ticker,
                            "series": series_ref,
                            "model": args.predictor,
                            "method": rec["method"],
                            "prob_model": rec["prob_yes"],
                            "outcome": rec["outcome"],
                            "brier": brier_val,
                            "log_loss": ll_val,
                            "mode": mode,
                        })
                    except Exception as e:
                        print(f"   [warn] could not append ledger row for "
                              f"{market_ref.ticker}: {e}")

            if event_records:
                all_records.extend(event_records)
                event_groups.append(event_records)
                per_series[series_ticker].extend(event_records)
                # Quick log
                top = max(event_records, key=lambda r: r["prob_yes"])
                winner = next((r for r in event_records if r["outcome"] == 1), None)
                hit = "OK" if (winner and top["ticker"] == winner["ticker"]) else "miss"
                wstr = winner["subtitle"] if winner else "?"
                print(f"   {ev.event_ticker:<28} top1={top['subtitle']:<22} (P={top['prob_yes']:.2f}) "
                      f"actual={wstr:<22} -> {hit}")

    # Agrégats
    print("\n" + "=" * 70)
    print("MÉTRIQUES GLOBALES")
    print("=" * 70)

    agg = aggregate_metrics(all_records)
    top1 = event_top1_accuracy(event_groups)
    print(f"  Markets prédits     : {agg['n']}")
    print(f"  Events backtest     : {top1['n_events']}")
    print(f"  Base rate (P(YES))  : {agg['base_rate']:.3f}")
    print(f"  Top-1 accuracy      : {top1['top1_accuracy']:.3f}  ({top1['top1_correct']}/{top1['n_events']})")
    print(f"  Brier score         : {agg['brier_score']:.4f}")
    print(f"  Brier baseline const: {agg['brier_baseline_constant']:.4f}")
    print(f"  Brier skill score   : {agg['brier_skill_score']:+.4f}  (>0 = mieux que constante)")
    print(f"  Log loss            : {agg['log_loss']:.4f}")

    print("\nPar série :")
    print(f"  {'Series':<14} {'N':>4} {'Brier':>8} {'BSS':>8} {'LogLoss':>8}")
    for s, recs in per_series.items():
        a = aggregate_metrics(recs)
        print(f"  {s:<14} {a['n']:>4} {a['brier_score']:>8.4f} {a['brier_skill_score']:>+8.3f} {a['log_loss']:>8.4f}")

    # Écrit rapport
    out_dir = ROOT / "data" / "backtests"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = out_dir / f"backtest_{args.predictor}_{ts}.json"
    report_path.write_text(json.dumps({
        "predictor": args.predictor,
        "years_back": args.years_back,
        "series": series_list,
        "n_records": len(all_records),
        "global": agg,
        "top1": top1,
        "per_series": {s: aggregate_metrics(r) for s, r in per_series.items()},
        "records": all_records,
    }, indent=2), encoding="utf-8")
    print(f"\n>> Rapport global: {report_path}")
    if write_per_record:
        n_files = sum(1 for _ in RUNS_BACKTEST_DIR.rglob("report.json")) \
            if RUNS_BACKTEST_DIR.exists() else 0
        ledger_lines = 0
        if LEDGER_BACKTEST_PATH.exists():
            with LEDGER_BACKTEST_PATH.open(encoding="utf-8") as f:
                ledger_lines = sum(1 for _ in f) - 1  # exclude header
        print(f">> Per-record:    {RUNS_BACKTEST_DIR}/ ({n_files} report.json total)")
        print(f">> Ledger:        {LEDGER_BACKTEST_PATH} ({ledger_lines} rows total)")
    if ensemble_naive_warning:
        print(">> NOTE: predictor was NAIVE (used current vendor forecast, not "
              "archived). Brier/BSS above are soft signals only.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
