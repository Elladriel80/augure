"""live_run.py — capture a live multi-model snapshot for an event/market.

Runs every model in runs_learning/CHAMPION.json on a single Kalshi market,
produces runs/<run_id>/report.json with a `models[]` array (champion +
challenger(s) + baseline(s)), and appends one row to paper_bets.csv for
the *champion's* position only. Challengers and baselines are tracked in
shadow mode (P&L theoretical, no ledger row).

The split is deliberate: we expose ourselves to exactly one P&L per run
(the champion's), but accumulate Brier comparison data across all models
in parallel. When a challenger's rolling-mean Brier strictly dominates
the champion's over N>=10 resolved trades, we promote it via a manual
edit of CHAMPION.json (no auto-promotion yet — that's Phase 2 of the
A/B infra).

Usage:
    python predictor/scripts/live_run.py --run-id 003 \\
        --event KXLOWTNYC-26MAY13 \\
        --market KXLOWTNYC-26MAY13-B51.5 \\
        --side NO --size-usd 100

    python predictor/scripts/live_run.py --run-id 003 \\
        --event KXLOWTNYC-26MAY13 \\
        --market KXLOWTNYC-26MAY13-B51.5 \\
        --side NO --size-usd 100 --dry-run
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from src.kalshi import KalshiClient  # noqa: E402
from src.predictors import (  # noqa: E402
    ClimatologyPredictor,
    EnsemblePredictor,
    ForecastBlendPredictor,
    LearnedPredictor,
    parse_market,
)
from src.weather import OpenMeteoClient  # noqa: E402


RUNS_DIR = ROOT / "runs"
LEDGER_PATH = ROOT / "data" / "ledger" / "paper_bets.csv"
CHAMPION_PATH = ROOT / "runs_learning" / "CHAMPION.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _bet_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ000000")


def _load_champion_registry() -> dict:
    if not CHAMPION_PATH.exists():
        raise FileNotFoundError(
            f"{CHAMPION_PATH} not found. Create it (see existing template) before "
            "running live_run.py."
        )
    return json.loads(CHAMPION_PATH.read_text(encoding="utf-8"))


def _predict_all_models(
    registry: dict,
    weather: OpenMeteoClient,
    spec,
    kalshi_yes_mid: Optional[float],
) -> list[dict]:
    """Run every model declared in CHAMPION.json and return per-model predictions.

    Sub-predictors are constructed once and reused across models to dedupe
    Open-Meteo and Kalshi cache hits.
    """
    climato = ClimatologyPredictor(weather)
    forecast_blend = ForecastBlendPredictor(weather)
    ensemble = EnsemblePredictor(weather)

    results: list[dict] = []
    current_champion = registry["current_champion"]

    for model_meta in registry["models"]:
        name = model_meta["name"]
        method = model_meta["method"]
        role = (
            "champion" if name == current_champion
            else model_meta.get("role", "challenger")
        )

        try:
            if method == "ensemble":
                pred = ensemble.predict(spec)
                p_yes = pred.prob_yes
                inputs_summary = {"method": pred.method}
            elif method == "learned_v2":
                learned = LearnedPredictor(
                    weather_client=weather,
                    sub_climato=climato,
                    sub_forecast_blend=forecast_blend,
                    sub_ensemble=ensemble,
                )
                pred = learned.predict(spec)
                p_yes = pred.prob_yes
                inputs_summary = {
                    "method": pred.method,
                    "trained_at": learned.trained_at,
                    "feature_set": learned.feature_set_used,
                    "run_json_path": str(learned.run_json_path),
                }
            elif method == "kalshi_mid":
                if kalshi_yes_mid is None:
                    p_yes = None
                    inputs_summary = {"method": "kalshi_mid",
                                      "reason": "yes_mid not available"}
                else:
                    p_yes = float(kalshi_yes_mid)
                    inputs_summary = {"method": "kalshi_mid",
                                      "yes_mid_at_snapshot": p_yes}
            else:
                p_yes = None
                inputs_summary = {"method": method,
                                  "reason": f"unknown method '{method}'"}
        except Exception as e:
            p_yes = None
            inputs_summary = {"method": method, "error": str(e)}

        results.append({
            "name": name,
            "role": role,
            "method": method,
            "p_yes": p_yes,
            "feature_set": model_meta.get("feature_set"),
            "trained_at": model_meta.get("trained_at"),
            "inputs_summary": inputs_summary,
        })

    return results


def _compute_position(
    side: str,
    size_usd: float,
    yes_mid: float,
) -> dict:
    """Translate (side, size, entry mid) into a contract-count position spec.

    Kalshi prices are USD per contract that pays $1 if the bin resolves YES.
    Entry price for NO = 1 - yes_mid. We round n_contracts down to avoid
    over-spending — the actual cost is therefore <= size_usd.
    """
    entry_yes = float(yes_mid)
    entry_no = 1.0 - entry_yes
    entry_price = entry_yes if side == "YES" else entry_no
    if entry_price <= 0:
        raise ValueError(f"entry_price={entry_price} is not positive; can't trade.")
    n_contracts = int(size_usd // entry_price)
    cost = n_contracts * entry_price
    return {
        "side": side,
        "size_usd": float(size_usd),
        "entry_price_yes_cents": round(entry_yes * 100, 2),
        "entry_price_no_cents": round(entry_no * 100, 2),
        "entry_price": entry_price,
        "n_contracts": n_contracts,
        "cost_usd": round(cost, 2),
    }


def _edge_bps(p_model: Optional[float], yes_mid: Optional[float]) -> Optional[int]:
    if p_model is None or yes_mid is None:
        return None
    return int(round((p_model - yes_mid) * 10000))


def _append_ledger_row(row: dict) -> None:
    """Append one row to paper_bets.csv, creating the file with header if missing."""
    fieldnames = [
        "bet_id", "placed_at_utc", "market_ticker", "event_ticker",
        "target_date", "side", "stake_usd", "entry_price", "prob_model",
        "prob_market_implied", "edge", "method", "spec",
        "resolved_at_utc", "resolution", "pnl_usd",
    ]
    write_header = not LEDGER_PATH.exists()
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER_PATH.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        # Ensure all fields are present (empty if unresolved).
        for k in fieldnames:
            row.setdefault(k, "")
        writer.writerow(row)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True, help="Run id (e.g. '003')")
    parser.add_argument("--event", required=True, help="Kalshi event ticker")
    parser.add_argument("--market", required=True, help="Kalshi market ticker (the bin)")
    parser.add_argument("--side", required=True, choices=["YES", "NO"],
                        help="Champion's position side")
    parser.add_argument("--size-usd", type=float, default=100.0,
                        help="Champion's stake in USD (default 100)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Don't write report.json or ledger; just print")
    parser.add_argument("--notes", default="",
                        help="Free-text note saved alongside the run")
    args = parser.parse_args()

    # 1. Champion registry
    print(">> Loading CHAMPION.json...")
    registry = _load_champion_registry()
    champion_name = registry["current_champion"]
    print(f"   current_champion: {champion_name}")
    print(f"   models tracked  : {[m['name'] for m in registry['models']]}")

    # 2. Fetch event + locate target market
    print(f">> Fetching {args.event} from Kalshi...")
    client = KalshiClient()
    ev = client.get_event(args.event)
    target = None
    for m in ev.markets:
        if m.ticker == args.market:
            target = m
            break
    if target is None:
        print(f"!! Market {args.market} not found in event {args.event}.")
        print(f"   Markets available: {[m.ticker for m in ev.markets]}")
        return 2
    print(f"   event : {ev.title}")
    print(f"   market: {args.market}")
    print(f"   yes_bid={target.yes_bid}  yes_ask={target.yes_ask}  status={target.status}")

    # 3. Snapshot the market
    yes_bid = float(target.yes_bid) if target.yes_bid is not None else None
    yes_ask = float(target.yes_ask) if target.yes_ask is not None else None
    yes_mid = ((yes_bid + yes_ask) / 2.0) if (yes_bid is not None and yes_ask is not None) else None
    spread_cents = (round((yes_ask - yes_bid) * 100, 2)
                    if (yes_bid is not None and yes_ask is not None) else None)

    # 4. Parse the contract spec
    spec = parse_market(target)
    if spec is None:
        print(f"!! Could not parse market {args.market}. Check parsers.py.")
        return 3

    # 5. Run every model declared in CHAMPION.json
    print(">> Running all models...")
    weather = OpenMeteoClient()
    models = _predict_all_models(registry, weather, spec, yes_mid)
    for m in models:
        p = f"{m['p_yes']:.3f}" if m["p_yes"] is not None else "  -  "
        edge_bps = _edge_bps(m["p_yes"], yes_mid)
        edge_str = f"{edge_bps:+5d}bps" if edge_bps is not None else "  -  "
        print(f"   {m['name']:<22} role={m['role']:<10}  p_yes={p}  edge_vs_mid={edge_str}")

    # 6. Compute champion's position
    if yes_mid is None:
        print(f"!! yes_mid is None — can't size a position. Aborting.")
        return 4
    pos = _compute_position(args.side, args.size_usd, yes_mid)

    # Find the champion's p_yes for the ledger row
    champion_p_yes = next((m["p_yes"] for m in models if m["name"] == champion_name), None)
    champion_method = next((m["method"] for m in models if m["name"] == champion_name), "unknown")

    # 7. Build the report.json
    ts_utc = _now_iso()
    ledger_bet_id = _bet_id() if not args.dry_run else "DRY_RUN_NO_LEDGER"

    report = {
        "schema_version": 2,
        "run_id": args.run_id,
        "type": "live",
        "ts_utc": ts_utc,
        "event": {
            "ticker": ev.event_ticker,
            "title": ev.title,
            "target_market_ticker": args.market,
            "resolution_source": "NWS official daily climate report (per Kalshi rules)",
        },
        "champion_at_time_of_run": champion_name,
        "models": models,
        "markets": [
            {
                "platform": "kalshi",
                "ticker": args.market,
                "url": f"https://kalshi.com/markets/{ev.event_ticker.rsplit('-', 1)[0]}",
                "snapshot_pre": {
                    "yes_bid": yes_bid,
                    "yes_ask": yes_ask,
                    "yes_mid": yes_mid,
                    "spread_cents": spread_cents,
                    "ts_utc": ts_utc,
                },
                "edge_bps_by_model": {
                    m["name"]: _edge_bps(m["p_yes"], yes_mid) for m in models
                },
                "champion_position": {
                    "model": champion_name,
                    "method": champion_method,
                    **pos,
                    "opened_at_utc": ts_utc,
                    "paper": True,
                    "ledger_bet_id": ledger_bet_id,
                },
                "challenger_shadow_positions": [
                    {
                        "model": m["name"],
                        "method": m["method"],
                        **_compute_position(args.side, args.size_usd, yes_mid),
                        "shadow": True,
                        "note": ("Same side/size as champion for Brier comparability. "
                                 "P&L theoretical only — no ledger row, no real exposure."),
                    }
                    for m in models if m["name"] != champion_name
                ],
                "resolution": {
                    "outcome": None,
                    "observed_value_f": None,
                    "ts_utc": None,
                    "pnl_usd": None,
                },
            }
        ],
        "scoring": None,  # populated by finalize_run.py once Kalshi settles
        "notes": args.notes,
    }

    # 8. Write report.json + ledger row
    if args.dry_run:
        print()
        print(">> [DRY RUN] Would write report.json:")
        print(json.dumps(report, indent=2, default=str)[:2500] + "\n  ... (truncated)")
        print(">> [DRY RUN] Would append ledger row.")
        return 0

    run_dir = RUNS_DIR / args.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    report_path = run_dir / "report.json"
    report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print()
    print(f">> wrote {report_path}")

    ledger_row = {
        "bet_id": ledger_bet_id,
        "placed_at_utc": ts_utc,
        "market_ticker": args.market,
        "event_ticker": ev.event_ticker,
        "target_date": spec.target_date.isoformat(),
        "side": args.side,
        "stake_usd": args.size_usd,
        "entry_price": yes_mid,  # the YES mid at snapshot; resolution side derived from `side`
        "prob_model": champion_p_yes,
        "prob_market_implied": yes_mid,
        "edge": (champion_p_yes - yes_mid) if champion_p_yes is not None else "",
        "method": champion_method,
        "spec": spec.describe(),
    }
    _append_ledger_row(ledger_row)
    print(f">> appended ledger row to {LEDGER_PATH} (bet_id={ledger_bet_id})")

    print()
    print(">> Run captured. Next steps:")
    print("   1. (manual) Place the actual paper trade on Kalshi: "
          f"{args.side} {args.market} ~{pos['n_contracts']} contracts @ {pos['entry_price']:.2f}")
    print(f"   2. (after Kalshi settles) python predictor/scripts/finalize_run.py --run {args.run_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
