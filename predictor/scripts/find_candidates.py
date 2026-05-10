"""find_candidates.py — surface the most actionable Run 002 candidates.

Reads the most recent `forward_*.json` in `predictor/data/predictions/`,
filters on markets that resolve today or tomorrow (UTC) and that are
quoted, then ranks them by the meta-ensemble's edge versus the Kalshi
mid. Same-sign filter on edge vs market AND vs climatology (the
prediction must agree with itself: the ensemble disagrees with the
market in the same direction it disagrees with the historical
baseline).

Builder-log output: top 10 markets, one line per market, plus a small
summary at the end.

Usage:
    python predictor/scripts/find_candidates.py
"""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
PRED_DIR = ROOT / "data" / "predictions"

EDGE_BPS_THRESHOLD = 500  # 5 cents = 500 bps minimum edge vs market
TOP_N = 10


def latest_forward_file() -> Path:
    candidates = sorted(PRED_DIR.glob("forward_*.json"))
    if not candidates:
        sys.exit(f"No forward_*.json found under {PRED_DIR}")
    return candidates[-1]


def main() -> int:
    path = latest_forward_file()
    print(f">> reading {path.name}")
    data = json.loads(path.read_text(encoding="utf-8"))

    today = date.today()
    tomorrow = today + timedelta(days=1)
    valid_dates = {today.isoformat(), tomorrow.isoformat()}
    print(f">> filtering target_date in {sorted(valid_dates)}")

    rows = []
    for r in data.get("records", []):
        td = r.get("target_date")
        if td not in valid_dates:
            continue
        mid = r.get("yes_mid")
        if mid is None:
            continue
        bid = r.get("yes_bid")
        ask = r.get("yes_ask")
        if bid is None or ask is None:
            continue
        spread = ask - bid

        preds = r.get("predictions", {})
        ens = preds.get("ensemble", {}).get("prob_yes")
        clim = preds.get("climatology", {}).get("prob_yes")
        if ens is None or clim is None:
            continue

        edge_market_bps = (ens - mid) * 10000
        edge_clim_bps = (ens - clim) * 10000

        # Same-sign filter: ensemble disagrees with market AND with
        # climatology in the same direction.
        if edge_market_bps * edge_clim_bps <= 0:
            continue
        if abs(edge_market_bps) < EDGE_BPS_THRESHOLD:
            continue

        rows.append({
            "ticker": r.get("ticker"),
            "target_date": td,
            "subtitle": r.get("subtitle", ""),
            "location": r.get("location_key", ""),
            "mid": mid,
            "spread_cents": spread * 100,
            "p_yes_ens": ens,
            "p_yes_clim": clim,
            "edge_market_bps": edge_market_bps,
            "edge_clim_bps": edge_clim_bps,
        })

    rows.sort(key=lambda x: abs(x["edge_market_bps"]), reverse=True)
    top = rows[:TOP_N]

    print(f">> {len(rows)} candidate(s) after filters; showing top {len(top)}")
    print()
    print(
        f"{'ticker':<32} {'date':<12} {'mid':>5} {'spread':>7} "
        f"{'p_ens':>6} {'p_clim':>6} {'edge_mkt':>9} {'edge_clim':>9}  side"
    )
    print("-" * 110)
    for x in top:
        side = "BUY YES" if x["edge_market_bps"] > 0 else "BUY NO"
        print(
            f"{x['ticker']:<32} {x['target_date']:<12} "
            f"{x['mid']:>5.2f} {x['spread_cents']:>6.1f}c "
            f"{x['p_yes_ens']:>6.3f} {x['p_yes_clim']:>6.3f} "
            f"{x['edge_market_bps']:>+8.0f}bp {x['edge_clim_bps']:>+8.0f}bp  {side}"
        )
        if x["subtitle"]:
            print(f"{'':<32} {x['location']} — {x['subtitle']}")

    print()
    print(f">> total candidates passing filters: {len(rows)}")
    print(f">> threshold: |edge_vs_market| >= {EDGE_BPS_THRESHOLD} bps, same sign as edge_vs_clim")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
