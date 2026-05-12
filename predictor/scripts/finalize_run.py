"""Finalize a live run once Kalshi has settled the underlying event.

Reads predictor/runs/<run_id>/report.json, fetches fresh resolutions from
Kalshi for every market in the report, then:
  - patches report.json    (resolution block + scoring block)
  - patches paper_bets.csv (resolved_at_utc, resolution, pnl_usd for our row)
  - patches POST_RUN.md    (fills <YES|NO>, <TBD>, <XX.X°F> templates)

Idempotent: if a market is not yet settled, the script reports it and exits
non-zero without writing partial data.

Usage:
    python predictor/scripts/finalize_run.py --run 002
    python predictor/scripts/finalize_run.py --run 002 --dry-run
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from src.kalshi import KalshiClient  # noqa: E402


# ---- pure helpers --------------------------------------------------------


def brier(p: float, y: int) -> float:
    """Brier score for a single binary outcome. y ∈ {0,1}."""
    return (p - y) ** 2


def fmt_brier(x: float) -> str:
    return f"{x:.4f}"


def parse_bin_range(market_raw: dict) -> tuple[float | None, float | None]:
    """Extract (floor, cap) in degrees F from a Kalshi temperature bin."""
    floor = market_raw.get("floor_strike")
    cap = market_raw.get("cap_strike")
    return (
        float(floor) if floor is not None else None,
        float(cap) if cap is not None else None,
    )


def find_winning_bin(event_raw: dict) -> dict | None:
    """Return the raw market dict whose result == 'yes', or None."""
    for m in event_raw.get("markets", []):
        if (m.get("result") or "").lower() == "yes":
            return m
    return None


# ---- core ----------------------------------------------------------------


def finalize(run_id: str, dry_run: bool = False) -> int:
    run_dir = ROOT / "runs" / run_id
    report_path = run_dir / "report.json"
    if not report_path.exists():
        print(f"!! report.json introuvable: {report_path}")
        return 2

    report = json.loads(report_path.read_text(encoding="utf-8"))
    p_model = float(report["model"]["p_yes"])
    p_climato = float(report["model"].get("p_yes_climatology", 0.0))

    client = KalshiClient()
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Process every market in the report
    p_kalshi_mid_entry: float | None = None
    outcome: int | None = None
    observed_range: tuple[float | None, float | None] = (None, None)

    for market_entry in report["markets"]:
        if market_entry.get("platform") != "kalshi":
            print(f">> Skipping non-kalshi market: {market_entry.get('platform')}")
            continue

        event_ticker = market_entry["ticker"].rsplit("-", 1)[0]
        our_ticker = market_entry["ticker"]
        print(f">> Fetching {event_ticker} ...")
        ev = client.get_event(event_ticker)
        client.snapshot_event(ev)

        # Find our specific bin
        our_market_raw = None
        for m in ev.raw.get("markets", []):
            if m.get("ticker") == our_ticker:
                our_market_raw = m
                break
        if our_market_raw is None:
            print(f"!! Market {our_ticker} introuvable dans event {event_ticker}")
            return 3

        status = our_market_raw.get("status", "")
        result = (our_market_raw.get("result") or "").lower()

        if status != "settled" and not result:
            print(f"!! {our_ticker} pas encore settled (status={status}, result={result or '-'})")
            print(f"   Relance plus tard quand Kalshi aura officiellement settled.")
            return 1

        # We have a result. Compute outcome.
        outcome = 1 if result == "yes" else 0
        print(f"   {our_ticker}: status={status}, result={result}, outcome={outcome}")

        # Find the winning bin to derive the observed temperature range
        winning = find_winning_bin(ev.raw)
        if winning is not None:
            observed_range = parse_bin_range(winning)
            print(f"   Bin gagnant: {winning.get('ticker')} "
                  f"(floor={observed_range[0]}, cap={observed_range[1]})")

        # P&L on our position
        pos = market_entry["position"]
        side = pos["side"]
        n_contracts = float(pos["n_contracts"])
        entry_price = pos["entry_price_yes_cents"] / 100.0 if side == "YES" \
            else pos["entry_price_no_cents"] / 100.0
        won = (side == "YES" and outcome == 1) or (side == "NO" and outcome == 0)
        cost_usd = n_contracts * entry_price
        payout_usd = n_contracts * 1.00 if won else 0.0
        pnl_usd = payout_usd - cost_usd

        # Use kalshi_mid from snapshot_pre as the market baseline
        snap = market_entry.get("snapshot_pre") or {}
        p_kalshi_mid_entry = snap.get("yes_mid")

        # Patch the market entry resolution block
        market_entry["resolution"] = {
            "outcome": "yes" if outcome == 1 else "no",
            "observed_value_f": None,  # exact NWS value not pulled here; range derivable from winning bin
            "observed_range_f": list(observed_range) if observed_range[0] is not None else None,
            "winning_bin_ticker": winning.get("ticker") if winning else None,
            "ts_utc": now_iso,
            "pnl_usd": round(pnl_usd, 2),
            "payout_usd": round(payout_usd, 2),
            "cost_usd": round(cost_usd, 2),
            "won": won,
        }

    if outcome is None:
        print("!! Aucun marche traite. Abort.")
        return 4

    # Scoring (single datapoint, paper trade)
    b_model = brier(p_model, outcome)
    b_climato = brier(p_climato, outcome)
    b_kalshi = brier(p_kalshi_mid_entry, outcome) if p_kalshi_mid_entry is not None else None

    report["scoring"] = {
        "brier_model": round(b_model, 4),
        "brier_climatology": round(b_climato, 4),
        "brier_kalshi_mid_entry": round(b_kalshi, 4) if b_kalshi is not None else None,
        "brier_best_single_model": None,  # we don't track individual ECMWF/GFS/etc Brier in live runs
        "model_beats_climato": b_model < b_climato,
        "model_beats_kalshi_mid": b_kalshi is not None and b_model < b_kalshi,
        "n_datapoints": 1,
        "note": "Run 002 = first live paper trade. Single point — directional only, not statistically significant.",
    }

    print(f"\n   Brier model:        {fmt_brier(b_model)}")
    print(f"   Brier climato:      {fmt_brier(b_climato)}")
    if b_kalshi is not None:
        print(f"   Brier kalshi_mid:   {fmt_brier(b_kalshi)}")
    print(f"   Model beats climato:    {b_model < b_climato}")
    if b_kalshi is not None:
        print(f"   Model beats kalshi_mid: {b_model < b_kalshi}")

    # ---- 1. Patch report.json ---------------------------------------------
    if dry_run:
        print("\n[DRY RUN] would write report.json:")
        print(json.dumps(report, indent=2))
    else:
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\n>> patched: {report_path}")

    # ---- 2. Patch paper_bets.csv ------------------------------------------
    ledger_path = ROOT / "data" / "ledger" / "paper_bets.csv"
    if not ledger_path.exists():
        print(f"!! paper_bets.csv introuvable: {ledger_path}")
        return 5

    raw_csv = ledger_path.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(raw_csv))
    fieldnames = reader.fieldnames or []
    rows = list(reader)

    # Match by ledger_bet_id stored in report
    target_bet_ids = {
        m["position"]["ledger_bet_id"]
        for m in report["markets"]
        if m.get("position", {}).get("ledger_bet_id")
    }

    patched = 0
    for row in rows:
        if row.get("bet_id") in target_bet_ids:
            # Find which market entry corresponds
            for m in report["markets"]:
                if m["position"]["ledger_bet_id"] == row["bet_id"]:
                    res = m["resolution"]
                    row["resolved_at_utc"] = res["ts_utc"]
                    row["resolution"] = res["outcome"]  # 'yes' or 'no'
                    row["pnl_usd"] = f"{res['pnl_usd']:.2f}"
                    patched += 1

    if patched == 0:
        print(f"!! Aucune ligne paper_bets.csv matchee (target ids: {target_bet_ids})")
    else:
        out_io = io.StringIO()
        writer = csv.DictWriter(out_io, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        if dry_run:
            print(f"\n[DRY RUN] would write {patched} row(s) to paper_bets.csv")
        else:
            ledger_path.write_text(out_io.getvalue(), encoding="utf-8")
            print(f">> patched: {ledger_path} ({patched} row(s))")

    # ---- 3. Patch POST_RUN.md ---------------------------------------------
    post_run_path = run_dir / "POST_RUN.md"
    if not post_run_path.exists():
        print(f"!! POST_RUN.md introuvable: {post_run_path}")
        return 6

    md = post_run_path.read_text(encoding="utf-8")

    outcome_label = "YES" if outcome == 1 else "NO"
    md = md.replace("résolu <YES|NO>", f"résolu {outcome_label}")
    md = md.replace("Outcome : <YES|NO>", f"Outcome : {outcome_label}")
    md = md.replace("Meta bat baseline ? <YES|NO>",
                    f"Meta bat baseline ? {'YES' if b_model < b_climato else 'NO'} "
                    f"(climato), "
                    f"{'YES' if (b_kalshi is not None and b_model < b_kalshi) else 'NO'} "
                    f"(kalshi_mid)")

    if observed_range[0] is not None:
        md = md.replace("Low observée NWS : <XX.X°F>",
                        f"Low observée (bin gagnant) : {observed_range[0]:.0f}-{observed_range[1]:.0f}°F")

    # P&L line — match our single market
    first_market = report["markets"][0]
    pos = first_market["position"]
    res = first_market["resolution"]
    no_exit = 100 if res["won"] and pos["side"] == "NO" else 0
    yes_exit = 100 if res["won"] and pos["side"] == "YES" else 0
    md = md.replace(
        f"NO entry <TBD>¢, NO exit <TBD>¢, P&L paper $<TBD>",
        f"NO entry {pos['entry_price_no_cents']}¢, NO exit {no_exit}¢, "
        f"P&L paper {'+' if res['pnl_usd'] >= 0 else ''}${res['pnl_usd']:.2f}",
    )

    md = md.replace("Brier modèle : <TBD>", f"Brier modèle : {fmt_brier(b_model)}")
    md = md.replace("Brier climatology : <TBD>", f"Brier climatology : {fmt_brier(b_climato)}")
    md = md.replace(
        "Brier best single model : <TBD>",
        f"Brier kalshi_mid (entry) : {fmt_brier(b_kalshi) if b_kalshi is not None else 'n/a'}",
    )

    if dry_run:
        print("\n[DRY RUN] would write POST_RUN.md:")
        print(md)
    else:
        post_run_path.write_text(md, encoding="utf-8")
        print(f">> patched: {post_run_path}")

    print(f"\n>> Run {run_id} finalized.")
    if first_market["resolution"]["won"]:
        print(f">> WIN. P&L: +${first_market['resolution']['pnl_usd']:.2f}")
    else:
        print(f">> LOSS. P&L: ${first_market['resolution']['pnl_usd']:.2f}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, help="Run id (e.g. '002')")
    parser.add_argument("--dry-run", action="store_true",
                        help="Don't write any files, just print what would happen")
    args = parser.parse_args()
    return finalize(args.run, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
