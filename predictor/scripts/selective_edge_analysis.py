"""selective_edge_analysis.py — does selective betting beat the market?

Strategy B (challenger to Phase A.1 thesis "the meta-ensemble beats the
market"). The aggregate result on N=60 says no: kalshi_mid Brier 0.1234
< ensemble Brier 0.1438. But maybe we have edge on a SUBSET — markets
where our model AND climatology both disagree with the market by a wide
margin (the `find_candidates.py` heuristic).

This script slices the resolved sample by that filter and computes
Brier on:
  - the high-edge subset for ensemble
  - the high-edge subset for kalshi_mid
  - the complement (low/no edge) for both

If selective ensemble Brier < selective kalshi_mid Brier on the
high-edge subset → the edge exists, we just need to size positions
only where we have it (instead of always-bet aggregate). This is the
"selectivity hypothesis".

If selective ensemble Brier >= selective kalshi_mid Brier on the
high-edge subset → the edge isn't really there even with the filter →
the thesis needs a deeper pivot (different venue, different vertical).

Builder-log output: table + verdict, no pandas dependency.

Usage:
    python predictor/scripts/selective_edge_analysis.py
    python predictor/scripts/selective_edge_analysis.py --threshold-bps 1000
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from src.config import DATA_DIR  # noqa: E402
from src.kalshi.client import KalshiClient  # noqa: E402


def brier(rows: list[dict], key: str) -> float | None:
    if not rows:
        return None
    n = len(rows)
    return sum((r[key] - r["outcome"]) ** 2 for r in rows) / n


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--threshold-bps", type=int, default=500,
                        help="Min |edge vs market| in bps for inclusion in "
                             "high-edge subset (default 500 = 5 cents).")
    parser.add_argument("--no-fetch", action="store_true",
                        help="Skip Kalshi resolution fetch; score only "
                             "markets whose result is already cached.")
    args = parser.parse_args()

    pred_dir = DATA_DIR / "predictions"
    files = sorted(pred_dir.glob("forward_*.json"))
    if not files:
        print(f"No forward_*.json under {pred_dir}.")
        return 1

    # Load all predictions, group by ticker keeping earliest capture WITH a
    # non-null yes_mid (so we have both model prediction and market price
    # for the same observation point).
    all_records: list[dict] = []
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        for r in data.get("records", []):
            r["_capture_at"] = data.get("snapshot_at")
            all_records.append(r)

    by_ticker: dict[str, dict] = {}
    for r in sorted(all_records, key=lambda x: x.get("_capture_at", "")):
        if r.get("yes_mid") is None:
            continue
        if r["ticker"] not in by_ticker:
            by_ticker[r["ticker"]] = r
    unique = list(by_ticker.values())
    print(f">> {len(unique)} unique markets with a quoted yes_mid")

    # Fetch resolutions
    resolutions: dict[str, str] = {}
    if not args.no_fetch:
        client = KalshiClient()
        events = sorted({r["event_ticker"] for r in unique})
        print(f">> fetching resolutions for {len(events)} events...")
        for ev_ticker in events:
            try:
                ev = client.get_event(ev_ticker, with_nested_markets=True)
                for m in ev.markets:
                    if m.result in ("yes", "no"):
                        resolutions[m.ticker] = m.result
            except Exception as e:
                print(f"  [warn] {ev_ticker}: {type(e).__name__}: {e}")

    rows: list[dict] = []
    for r in unique:
        if r["ticker"] not in resolutions:
            continue
        preds = r.get("predictions", {})
        ens = preds.get("ensemble", {}).get("prob_yes")
        clim = preds.get("climatology", {}).get("prob_yes")
        mid = r.get("yes_mid")
        if ens is None or clim is None or mid is None:
            continue
        outcome = 1 if resolutions[r["ticker"]] == "yes" else 0
        edge_market_bps = (ens - mid) * 10000
        edge_clim_bps = (ens - clim) * 10000
        rows.append({
            "ticker": r["ticker"],
            "target_date": r.get("target_date"),
            "outcome": outcome,
            "p_ens": ens,
            "p_clim": clim,
            "mid": mid,
            "edge_market_bps": edge_market_bps,
            "edge_clim_bps": edge_clim_bps,
        })

    print(f">> {len(rows)} resolved markets with both model + market data")
    if not rows:
        return 0

    # Filter: high-edge AND directional consistency (model and climato
    # disagree with market in the same direction).
    threshold = args.threshold_bps
    high_edge = [
        r for r in rows
        if abs(r["edge_market_bps"]) >= threshold
        and r["edge_market_bps"] * r["edge_clim_bps"] > 0
    ]
    low_edge = [r for r in rows if r not in high_edge]

    print(f">> high-edge filter: |edge_vs_market| >= {threshold} bps AND "
          f"same sign as edge_vs_climato")
    print(f">> high-edge count: {len(high_edge)} / {len(rows)} "
          f"({100 * len(high_edge) / len(rows):.0f}%)")
    print()

    # Compute Brier on each subset
    def fmt(b):
        return f"{b:.4f}" if b is not None else "  n/a"

    ens_all = brier(rows, "p_ens")
    mid_all = brier(rows, "mid")
    ens_high = brier(high_edge, "p_ens")
    mid_high = brier(high_edge, "mid")
    ens_low = brier(low_edge, "p_ens")
    mid_low = brier(low_edge, "mid")

    print(f"{'subset':<20} {'n':>4}  {'ens Brier':>10}  {'mid Brier':>10}  "
          f"{'winner':>10}")
    print("-" * 64)
    def line(label, n, e, m):
        if e is None or m is None:
            winner = "n/a"
        elif e < m:
            winner = "ENSEMBLE"
        elif m < e:
            winner = "MARKET"
        else:
            winner = "tie"
        print(f"{label:<20} {n:>4}  {fmt(e):>10}  {fmt(m):>10}  {winner:>10}")

    line("all", len(rows), ens_all, mid_all)
    line(f"high-edge >={threshold}bp", len(high_edge), ens_high, mid_high)
    line("low-edge / no signal", len(low_edge), ens_low, mid_low)

    print()
    print("Reading:")
    print("  - 'ENSEMBLE' on high-edge subset = selectivity works")
    print("  - 'MARKET' on high-edge subset   = filter does not save us")
    print("  - aggregate 'all' subset is reference benchmark")

    # Also show: of high-edge bets, what's the directional accuracy?
    # Split by direction (BUY YES = model > market vs BUY NO = model < market)
    # since they probe different parts of the market structure.
    if high_edge:
        n_correct = 0
        for r in high_edge:
            predicted_yes = r["p_ens"] > r["mid"]
            actual_yes = bool(r["outcome"])
            if predicted_yes == actual_yes:
                n_correct += 1
        print(f"\n>> directional accuracy on high-edge bets (all): "
              f"{n_correct}/{len(high_edge)} = "
              f"{100*n_correct/len(high_edge):.0f}%")

        buy_yes = [r for r in high_edge if r["edge_market_bps"] > 0]
        buy_no = [r for r in high_edge if r["edge_market_bps"] < 0]

        print(f"\n>> split by trade direction:")
        for label, subset in [("BUY YES (model > market)", buy_yes),
                              ("BUY NO  (model < market)", buy_no)]:
            n = len(subset)
            if n == 0:
                print(f"   {label:<32} n={n} — empty, no signal to read")
                continue
            n_yes = sum(r["outcome"] for r in subset)
            # For BUY YES, "correct" = outcome is YES
            # For BUY NO,  "correct" = outcome is NO
            if "YES" in label:
                n_correct = n_yes
            else:
                n_correct = n - n_yes
            ens_brier = brier(subset, "p_ens")
            mid_brier = brier(subset, "mid")
            winner = "ENSEMBLE" if (ens_brier or 1) < (mid_brier or 0) else "MARKET"
            print(f"   {label:<32} n={n:<3} accuracy={n_correct}/{n} "
                  f"= {100*n_correct/n:.0f}%  "
                  f"ens={fmt(ens_brier)}  mid={fmt(mid_brier)}  → {winner}")

        # Verdict
        print(f"\n>> verdict:")
        if buy_yes and buy_no:
            ay = sum(r["outcome"] for r in buy_yes) / len(buy_yes)
            an = 1 - sum(r["outcome"] for r in buy_no) / len(buy_no)
            if ay > 0.55:
                print(f"   BUY YES direction has positive edge "
                      f"(accuracy {100*ay:.0f}%) — keep that side, drop BUY NO")
            elif an > 0.55:
                print(f"   BUY NO direction has positive edge "
                      f"(accuracy {100*an:.0f}%) — keep that side, drop BUY YES")
            elif ay < 0.30 and an > 0.55:
                print(f"   Asymmetric: fade BUY YES signal (it goes against), "
                      f"trust BUY NO signal")
            else:
                print(f"   Neither direction shows clear positive edge. "
                      f"Pivot deeper (different venue / vertical) recommended.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
