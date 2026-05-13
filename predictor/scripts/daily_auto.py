"""Autonomous daily orchestrator for Aratea Kalshi paper trading.

Triggered by .github/workflows/daily-trading.yml cron at 14:00 UTC.
Designed to run unattended — exits 0 on every non-catastrophic case so the
workflow never fails on missing data (e.g. event not yet published).

Workflow per invocation:
  1. Auto-finalize: for every run with a not-yet-resolved report.json,
     check Kalshi. If settled, run finalize_run.finalize().
  2. Auto-capture: pick tomorrow's NYC LOWT event, score every parseable
     median bin with the champion (vendor_ensemble), select the bin with
     |edge vs kalshi_mid| > EDGE_THRESHOLD and spread <= SPREAD_THRESHOLD.
     If a winner is found, capture a run (write report.json + append
     ledger). If not, log the reason and skip.
  3. Rebuild dashboard manifest.

The workflow then commits + pushes the result.

Idempotent. Safe to re-run within the same day — the bin-selection step
overwrites the day's open run if no resolution has been logged yet (the
report.json is rewritten in place). Set --no-overwrite to opt out.

Skip conditions (auto-capture exits clean):
  - tomorrow's KXLOWTNYC event is not yet published on Kalshi
  - no median bin has |edge| > EDGE_THRESHOLD
  - all candidate bins have spread > SPREAD_THRESHOLD

Usage:
    python predictor/scripts/daily_auto.py
    python predictor/scripts/daily_auto.py --dry-run
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
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

# Reuse the live_run helpers so we don't duplicate position math.
sys.path.insert(0, str(SCRIPTS))
from live_run import (  # noqa: E402
    _append_ledger_row,
    _bet_id,
    _compute_position,
    _edge_bps,
    _load_champion_registry,
    _now_iso,
    _predict_all_models,
)
from finalize_run import finalize  # noqa: E402


# ---- decision thresholds --------------------------------------------------
EDGE_THRESHOLD = 0.10       # |p_champion - kalshi_mid| must be at least 10 pts
SPREAD_THRESHOLD = 0.05     # yes_ask - yes_bid must be <= 5 cents
SIZE_USD = 100.0            # paper stake per run

# Hardcoded event class for now: NYC daily low temperature.
EVENT_SERIES = "KXLOWTNYC"

# Kalshi tickers encode the date as 26MAY13 (yy MON dd, uppercase).
def _kalshi_date_token(d: date) -> str:
    return d.strftime("%y%b%d").upper()


RUNS_DIR = ROOT / "runs"
LEDGER_PATH = ROOT / "data" / "ledger" / "paper_bets.csv"


# ---- step 1: auto-finalize -----------------------------------------------


def _scan_open_runs() -> list[tuple[str, Path]]:
    """Return [(run_id, report_path), ...] for runs with no resolved outcome."""
    out = []
    if not RUNS_DIR.exists():
        return out
    for run_dir in sorted(RUNS_DIR.iterdir()):
        if not run_dir.is_dir():
            continue
        rj = run_dir / "report.json"
        if not rj.exists():
            continue
        try:
            data = json.loads(rj.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"   [warn] unreadable report.json {rj}: {e}")
            continue
        # An "open" run is one where at least one market still has resolution.outcome = null
        open_any = False
        for m in data.get("markets", []):
            r = (m.get("resolution") or {}).get("outcome")
            if r is None:
                open_any = True
                break
        if open_any:
            out.append((run_dir.name, rj))
    return out


def step_finalize() -> dict:
    """Try to finalize every open run. Returns a summary dict."""
    print(">> step 1: auto-finalize open runs")
    open_runs = _scan_open_runs()
    if not open_runs:
        print("   nothing open. skip.")
        return {"open_before": 0, "finalized": []}

    print(f"   {len(open_runs)} open run(s): {[r[0] for r in open_runs]}")
    finalized = []
    skipped = []
    for run_id, _ in open_runs:
        print(f"   -> finalize_run.finalize(run='{run_id}', dry_run=False)")
        try:
            rc = finalize(run_id, dry_run=False)
        except SystemExit as e:
            rc = e.code if isinstance(e.code, int) else 99
        except Exception as e:
            print(f"   !! exception while finalizing {run_id}: {e}")
            rc = 99
        if rc == 0:
            finalized.append(run_id)
        elif rc == 1:
            # Not yet settled — fine, will retry tomorrow.
            print(f"   [skip] {run_id} not yet settled by Kalshi.")
            skipped.append(run_id)
        else:
            print(f"   !! finalize_run returned rc={rc} for {run_id}")
            skipped.append(run_id)
    return {"open_before": len(open_runs), "finalized": finalized, "skipped": skipped}


# ---- step 2: auto-capture -------------------------------------------------


def _next_run_id() -> str:
    """Return the next run id as a zero-padded 3-digit string."""
    existing = []
    if RUNS_DIR.exists():
        for d in RUNS_DIR.iterdir():
            if d.is_dir():
                try:
                    existing.append(int(d.name))
                except ValueError:
                    continue
    next_n = (max(existing) + 1) if existing else 1
    return f"{next_n:03d}"


def _select_target_bin(ev, champion_p_yes_by_ticker: dict[str, float]) -> Optional[dict]:
    """Return the chosen target bin dict, or None if no bin clears the thresholds.

    The chosen bin must:
      - be parseable
      - have strike_type 'between' (median bin, not a tail T-bin)
      - have both yes_bid and yes_ask non-null (tradable)
      - be liquid: yes_bid > MIN_QUOTE and yes_ask < MAX_QUOTE
        (skips bins where market makers haven't posted yet — e.g. event
        just published, both quotes still at 0 → yes_mid 0 → can't trade)
      - spread <= SPREAD_THRESHOLD
      - |edge_vs_mid| >= EDGE_THRESHOLD
    Among qualifying bins, the one with the largest |edge| wins.
    """
    MIN_QUOTE = 0.02  # below = effectively no bid
    MAX_QUOTE = 0.98  # above = effectively no ask

    candidates = []
    for m in ev.markets:
        raw = next((r for r in ev.raw.get("markets", []) if r.get("ticker") == m.ticker), None)
        if raw is None:
            continue
        if raw.get("strike_type") != "between":
            continue  # tail bin, skip
        yb = m.yes_bid
        ya = m.yes_ask
        if yb is None or ya is None:
            continue
        yb_f = float(yb)
        ya_f = float(ya)
        # Liquidity check: a bin with yes_bid=0 (or yes_ask=1) means quotes
        # haven't been posted yet — yes_mid would be 0 (or 1) and we can't
        # size a position against that price. Skip until the market is
        # actually tradable.
        if yb_f < MIN_QUOTE or ya_f > MAX_QUOTE:
            continue
        spread = ya_f - yb_f
        if spread > SPREAD_THRESHOLD:
            continue
        yes_mid = (yb_f + ya_f) / 2.0
        p_champ = champion_p_yes_by_ticker.get(m.ticker)
        if p_champ is None:
            continue
        edge = p_champ - yes_mid
        if abs(edge) < EDGE_THRESHOLD:
            continue
        candidates.append({
            "ticker": m.ticker,
            "yes_bid": float(yb),
            "yes_ask": float(ya),
            "yes_mid": yes_mid,
            "spread": spread,
            "p_champion": p_champ,
            "edge": edge,
            "abs_edge": abs(edge),
        })

    if not candidates:
        return None

    # Sort by abs_edge descending; tie-break by smaller spread (cleaner trade).
    candidates.sort(key=lambda c: (-c["abs_edge"], c["spread"]))
    return candidates[0]


def _open_runs_for_event(event_ticker: str) -> list[str]:
    """Return run_ids that are currently open AND target the same event_ticker.

    Used to dedupe: if today's cron already captured a run for tomorrow's
    event (e.g. via a manual workflow_dispatch earlier), don't capture
    twice.
    """
    matches: list[str] = []
    if not RUNS_DIR.exists():
        return matches
    for run_dir in RUNS_DIR.iterdir():
        if not run_dir.is_dir():
            continue
        rj = run_dir / "report.json"
        if not rj.exists():
            continue
        try:
            data = json.loads(rj.read_text(encoding="utf-8"))
        except Exception:
            continue
        ev = (data.get("event") or {}).get("ticker")
        if ev != event_ticker:
            continue
        # Open = at least one market with resolution.outcome == null
        for m in data.get("markets", []):
            if (m.get("resolution") or {}).get("outcome") is None:
                matches.append(run_dir.name)
                break
    return matches


def step_capture(dry_run: bool) -> dict:
    """Try to capture a new run for tomorrow's KXLOWTNYC event. Returns summary."""
    print(">> step 2: auto-capture new run")

    tomorrow = date.today() + timedelta(days=1)
    event_ticker = f"{EVENT_SERIES}-{_kalshi_date_token(tomorrow)}"
    print(f"   target event: {event_ticker} (tomorrow = {tomorrow.isoformat()})")

    # Dedupe: skip if an open run already exists for this event ticker.
    already = _open_runs_for_event(event_ticker)
    if already:
        print(f"   [skip] open run(s) already exist for {event_ticker}: {already}. "
              "No duplicate capture.")
        return {"captured": False, "reason": "already_open_run_for_event",
                "event_ticker": event_ticker, "existing_runs": already}

    # 1. Fetch the event from Kalshi
    client = KalshiClient()
    try:
        ev = client.get_event(event_ticker)
    except Exception as e:
        print(f"   [skip] event not yet published or fetch error: {e}")
        return {"captured": False, "reason": "event_not_published_or_error",
                "event_ticker": event_ticker, "error": str(e)}

    print(f"   event title: {ev.title}")
    print(f"   markets: {len(ev.markets)}")

    # 2. Score every parseable market with the champion (vendor_ensemble)
    weather = OpenMeteoClient()
    ensemble = EnsemblePredictor(weather)
    champion_p_yes_by_ticker: dict[str, float] = {}
    for m in ev.markets:
        spec = parse_market(m)
        if spec is None:
            continue
        try:
            pred = ensemble.predict(spec)
            champion_p_yes_by_ticker[m.ticker] = float(pred.prob_yes)
        except Exception as e:
            print(f"   [warn] predict error on {m.ticker}: {e}")

    if not champion_p_yes_by_ticker:
        print("   [skip] no markets could be scored.")
        return {"captured": False, "reason": "no_markets_scored",
                "event_ticker": event_ticker}

    # 3. Select the best target bin
    target = _select_target_bin(ev, champion_p_yes_by_ticker)
    if target is None:
        print(f"   [skip] no median bin clears thresholds "
              f"(|edge|>={EDGE_THRESHOLD}, spread<={SPREAD_THRESHOLD}).")
        return {"captured": False, "reason": "no_bin_clears_thresholds",
                "event_ticker": event_ticker,
                "candidates": list(champion_p_yes_by_ticker.keys())}

    side = "NO" if target["edge"] < 0 else "YES"
    print(f"   target bin: {target['ticker']}  yes_mid={target['yes_mid']:.3f}  "
          f"p_champion={target['p_champion']:.3f}  edge={target['edge']:+.3f}  "
          f"side={side}")

    # 4. Now run all models (champion + challengers + baseline) on the chosen bin
    registry = _load_champion_registry()
    target_market = next(m for m in ev.markets if m.ticker == target["ticker"])
    spec = parse_market(target_market)
    if spec is None:
        print("   !! parse_market returned None on selected target. abort capture.")
        return {"captured": False, "reason": "parse_market_failed_on_target"}

    models = _predict_all_models(registry, weather, spec, target["yes_mid"])
    for m in models:
        p = f"{m['p_yes']:.3f}" if m["p_yes"] is not None else "  -  "
        print(f"     {m['name']:<22} role={m['role']:<10}  p_yes={p}")

    # 5. Build report.json + append ledger row
    run_id = _next_run_id()
    print(f"   assigned run-id: {run_id}")

    pos = _compute_position(side, SIZE_USD, target["yes_mid"])
    ts_utc = _now_iso()
    ledger_bet_id = _bet_id() if not dry_run else "DRY_RUN_NO_LEDGER"
    champion_name = registry["current_champion"]
    champion_method = next(
        (m["method"] for m in models if m["name"] == champion_name), "unknown"
    )
    champion_p_yes = next(
        (m["p_yes"] for m in models if m["name"] == champion_name), None
    )

    report = {
        "schema_version": 2,
        "run_id": run_id,
        "type": "live",
        "ts_utc": ts_utc,
        "event": {
            "ticker": ev.event_ticker,
            "title": ev.title,
            "target_market_ticker": target["ticker"],
            "resolution_source": "NWS official daily climate report (per Kalshi rules)",
        },
        "champion_at_time_of_run": champion_name,
        "models": models,
        "markets": [
            {
                "platform": "kalshi",
                "ticker": target["ticker"],
                "url": f"https://kalshi.com/markets/{ev.event_ticker.rsplit('-', 1)[0]}",
                "snapshot_pre": {
                    "yes_bid": target["yes_bid"],
                    "yes_ask": target["yes_ask"],
                    "yes_mid": target["yes_mid"],
                    "spread_cents": round(target["spread"] * 100, 2),
                    "ts_utc": ts_utc,
                },
                "edge_bps_by_model": {
                    m["name"]: _edge_bps(m["p_yes"], target["yes_mid"]) for m in models
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
                        **_compute_position(side, SIZE_USD, target["yes_mid"]),
                        "shadow": True,
                        "note": ("Auto-captured by daily_auto.py. Same side/size as "
                                 "champion for Brier comparability."),
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
        "scoring": None,
        "notes": (
            f"Auto-captured by daily_auto.py on {ts_utc}. "
            f"Selection rule: median-bin with max |edge_vs_mid| "
            f"(threshold {EDGE_THRESHOLD}), spread<={SPREAD_THRESHOLD}. "
            f"Champion {champion_name} edge={target['edge']:+.3f}, side={side}."
        ),
    }

    if dry_run:
        print(f"   [DRY RUN] would write runs/{run_id}/report.json")
        print(f"   [DRY RUN] would append ledger row (bet_id={ledger_bet_id})")
        return {"captured": True, "dry_run": True, "run_id": run_id,
                "event_ticker": event_ticker, "target": target}

    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "report.json").write_text(
        json.dumps(report, indent=2, default=str), encoding="utf-8"
    )
    print(f"   wrote runs/{run_id}/report.json")

    _append_ledger_row({
        "bet_id": ledger_bet_id,
        "placed_at_utc": ts_utc,
        "market_ticker": target["ticker"],
        "event_ticker": ev.event_ticker,
        "target_date": spec.target_date.isoformat(),
        "side": side,
        "stake_usd": SIZE_USD,
        "entry_price": target["yes_mid"],
        "prob_model": champion_p_yes,
        "prob_market_implied": target["yes_mid"],
        "edge": (champion_p_yes - target["yes_mid"]) if champion_p_yes is not None else "",
        "method": champion_method,
        "spec": spec.describe(),
    })
    print(f"   appended ledger row (bet_id={ledger_bet_id})")

    return {"captured": True, "dry_run": False, "run_id": run_id,
            "event_ticker": event_ticker, "target_market": target["ticker"],
            "side": side, "n_contracts": pos["n_contracts"]}


# ---- step 3: rebuild manifest ---------------------------------------------


def step_manifest() -> dict:
    """Re-generate dashboard manifest. Subprocess-call so we use the existing script verbatim."""
    print(">> step 3: rebuild dashboard manifest")
    cmd = [sys.executable, str(SCRIPTS / "build_dashboard_manifest.py")]
    try:
        result = subprocess.run(cmd, cwd=str(ROOT), check=False, capture_output=True, text=True)
    except Exception as e:
        print(f"   !! build_dashboard_manifest exception: {e}")
        return {"ok": False, "error": str(e)}
    print(result.stdout.strip() or "   (no stdout)")
    if result.stderr.strip():
        print("   stderr:", result.stderr.strip())
    return {"ok": result.returncode == 0, "rc": result.returncode}


# ---- main -----------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="Don't write report.json, ledger, or manifest. Just print.")
    args = parser.parse_args()

    started = datetime.now(timezone.utc)
    print("=" * 70)
    print(f"daily_auto.py @ {started.isoformat()}")
    print(f"dry_run = {args.dry_run}")
    print("=" * 70)

    summary = {
        "started_at": started.isoformat(),
        "dry_run": args.dry_run,
    }

    summary["finalize"] = step_finalize()
    print()
    summary["capture"] = step_capture(args.dry_run)
    print()
    if not args.dry_run:
        summary["manifest"] = step_manifest()
    print()

    finished = datetime.now(timezone.utc)
    print("=" * 70)
    print(f"daily_auto.py done @ {finished.isoformat()} "
          f"(duration {(finished - started).total_seconds():.1f}s)")
    print("=" * 70)

    # Always exit 0. The workflow should not fail on missing data — it will retry
    # tomorrow. The summary is printed for the workflow log.
    return 0


if __name__ == "__main__":
    sys.exit(main())
