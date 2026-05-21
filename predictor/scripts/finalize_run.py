"""Finalize a live run once Kalshi has settled the underlying event.

Reads predictor/runs/<run_id>/report.json, fetches fresh resolutions from
Kalshi for every market in the report, then:
  - patches report.json    (resolution block + scoring block)
  - patches paper_bets.csv (resolved_at_utc, resolution, pnl_usd for the
                            champion's row only)
  - patches POST_RUN.md    (single-model v1 template OR generates fresh
                            multi-model v2 doc)

Supports two report.json schemas, dispatched on the top-level
`schema_version` field:
  - v1 (Run 001/002): single `model: {}` block + per-market `position`
    block. The champion is implicit. Kept untouched for backward compat.
  - v2 (Run 003+):   `models: []` array + per-market `champion_position`
    plus `challenger_shadow_positions[]`. The champion takes the actual
    paper bet; challengers and baselines accumulate Brier and theoretical
    P&L in scoring.by_model[] for A/B comparison.

Idempotent: if a market is not yet settled, the script reports it and
exits non-zero without writing partial data.

Usage:
    python predictor/scripts/finalize_run.py --run 002
    python predictor/scripts/finalize_run.py --run 003 --dry-run
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
    schema_version = int(report.get("schema_version", 1))
    if schema_version >= 2:
        return _finalize_v2(report, report_path, run_dir, dry_run)

    # ---- v1 path (Run 001 / 002 schema) ----
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


def _compute_pnl(side: str, n_contracts: float, entry_price: float, outcome: int) -> dict:
    """Common P&L calc used for champion + every shadow position.

    Kalshi pays $1.00 per contract if the contract's YES side matches the
    outcome. Side="YES" wins iff outcome==1; side="NO" wins iff outcome==0.
    """
    won = (side == "YES" and outcome == 1) or (side == "NO" and outcome == 0)
    cost = n_contracts * entry_price
    payout = n_contracts * 1.0 if won else 0.0
    return {
        "won": won,
        "cost_usd": round(cost, 2),
        "payout_usd": round(payout, 2),
        "pnl_usd": round(payout - cost, 2),
    }


def _finalize_v2(report: dict, report_path: Path, run_dir: Path, dry_run: bool) -> int:
    """v2 schema: multi-model report with champion + challengers + baseline."""
    run_id = report["run_id"]
    client = KalshiClient()
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # ---- 1. Resolve every market via Kalshi ----
    outcome: int | None = None
    observed_range: tuple[float | None, float | None] = (None, None)
    winning_ticker: str | None = None
    target_market_entry: dict | None = None

    for market_entry in report["markets"]:
        if market_entry.get("platform") != "kalshi":
            print(f">> Skipping non-kalshi market: {market_entry.get('platform')}")
            continue

        our_ticker = market_entry["ticker"]
        event_ticker = our_ticker.rsplit("-", 1)[0]
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
        if status not in ("settled", "finalized") and not result:
            print(f"!! {our_ticker} pas encore settled (status={status}, result={result or '-'})")
            print(f"   Relance plus tard quand Kalshi aura officiellement settled.")
            return 1

        outcome = 1 if result == "yes" else 0
        print(f"   {our_ticker}: status={status}, result={result}, outcome={outcome}")

        winning = find_winning_bin(ev.raw)
        if winning is not None:
            observed_range = parse_bin_range(winning)
            winning_ticker = winning.get("ticker")
            print(f"   Bin gagnant: {winning_ticker} "
                  f"(floor={observed_range[0]}, cap={observed_range[1]})")

        # Champion P&L (the one that actually exposes the ledger)
        champ_pos = market_entry["champion_position"]
        champ_side = champ_pos["side"]
        champ_n = float(champ_pos["n_contracts"])
        champ_entry = float(champ_pos["entry_price"])
        champ_pnl = _compute_pnl(champ_side, champ_n, champ_entry, outcome)

        market_entry["resolution"] = {
            "outcome": "yes" if outcome == 1 else "no",
            "observed_value_f": None,
            "observed_range_f": list(observed_range) if observed_range[0] is not None else None,
            "winning_bin_ticker": winning_ticker,
            "ts_utc": now_iso,
            "champion_pnl_usd": champ_pnl["pnl_usd"],
            "champion_payout_usd": champ_pnl["payout_usd"],
            "champion_cost_usd": champ_pnl["cost_usd"],
            "champion_won": champ_pnl["won"],
        }

        # Theoretical P&L per shadow position (same calc, same side/size by construction)
        shadow_pnls: dict[str, dict] = {}
        for shadow in market_entry.get("challenger_shadow_positions", []):
            sh_pnl = _compute_pnl(
                shadow["side"],
                float(shadow["n_contracts"]),
                float(shadow["entry_price"]),
                outcome,
            )
            shadow_pnls[shadow["model"]] = sh_pnl

        target_market_entry = market_entry
        target_market_entry["_shadow_pnls"] = shadow_pnls

    if outcome is None or target_market_entry is None:
        print("!! Aucun marche traite. Abort.")
        return 4

    # ---- 2. Score every model ----
    by_model: dict[str, dict] = {}
    for m in report["models"]:
        p_yes = m.get("p_yes")
        if p_yes is None:
            by_model[m["name"]] = {
                "role": m["role"],
                "method": m["method"],
                "p_yes": None,
                "brier": None,
                "won": None,
                "pnl_usd": None,
                "note": "no prediction (model returned None at run time)",
            }
            continue

        b = brier(float(p_yes), outcome)
        entry = {
            "role": m["role"],
            "method": m["method"],
            "p_yes": round(float(p_yes), 4),
            "brier": round(b, 4),
        }
        if m["role"] == "champion":
            entry["won"] = target_market_entry["resolution"]["champion_won"]
            entry["pnl_usd"] = target_market_entry["resolution"]["champion_pnl_usd"]
            entry["pnl_type"] = "actual"
        else:
            sh = target_market_entry["_shadow_pnls"].get(m["name"], {})
            entry["won"] = sh.get("won")
            entry["pnl_usd"] = sh.get("pnl_usd")
            entry["pnl_type"] = "theoretical"
        by_model[m["name"]] = entry

    # Ranking: who has the best Brier (lower = better) among models with a prediction
    ranked = sorted(
        [(name, info["brier"]) for name, info in by_model.items()
         if info.get("brier") is not None],
        key=lambda kv: kv[1],
    )
    best_name = ranked[0][0] if ranked else None
    champ_name = report["champion_at_time_of_run"]
    champ_brier = by_model.get(champ_name, {}).get("brier")

    report["scoring"] = {
        "outcome": "yes" if outcome == 1 else "no",
        "by_model": by_model,
        "ranking_by_brier": [{"model": n, "brier": b} for n, b in ranked],
        "best_brier_model": best_name,
        "champion_at_time_of_run": champ_name,
        "champion_is_best": (best_name == champ_name),
        "n_datapoints": 1,
        "note": (
            f"Run {run_id} multi-model trade. Single point — directional only, "
            "not statistically significant. The champion promotion rule requires "
            "N>=10 with sign test p<0.10."
        ),
    }

    # Clean up the temporary _shadow_pnls field before writing
    target_market_entry.pop("_shadow_pnls", None)

    print()
    print(">> Per-model scoring:")
    print(f"   {'model':<24} {'role':<11} {'p_yes':>7} {'brier':>8} {'pnl':>10} {'pnl_type':>12}")
    print("   " + "-" * 78)
    for name, info in by_model.items():
        p = f"{info['p_yes']:.3f}" if info.get("p_yes") is not None else "  -  "
        b_ = f"{info['brier']:.4f}" if info.get("brier") is not None else "  -   "
        pnl = info.get("pnl_usd")
        pnl_s = f"{pnl:+.2f}" if pnl is not None else "  -  "
        print(f"   {name:<24} {info['role']:<11} {p:>7} {b_:>8} {pnl_s:>10} {info.get('pnl_type', '-'):>12}")
    print()
    if best_name:
        if best_name == champ_name:
            print(f">> Champion ({champ_name}) is best by Brier on this run.")
        else:
            margin = champ_brier - by_model[best_name]["brier"]
            print(f">> Challenger {best_name} BEATS champion {champ_name} by "
                  f"{margin:.4f} Brier on this run.")
            print(f"   N=1 — not promotable yet. Need rolling-mean dominance over N>=10.")

    # ---- 3. Patch report.json ----
    if dry_run:
        print("\n[DRY RUN] would write report.json:")
        print(json.dumps(report, indent=2, default=str)[:3000] + "\n  ... (truncated)")
    else:
        report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        print(f"\n>> patched: {report_path}")

    # ---- 4. Patch paper_bets.csv (champion's row only) ----
    ledger_path = ROOT / "data" / "ledger" / "paper_bets.csv"
    if not ledger_path.exists():
        print(f"!! paper_bets.csv introuvable: {ledger_path}")
        return 5

    raw_csv = ledger_path.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(raw_csv))
    fieldnames = reader.fieldnames or []
    rows = list(reader)

    target_bet_ids = {
        m["champion_position"]["ledger_bet_id"]
        for m in report["markets"]
        if m.get("champion_position", {}).get("ledger_bet_id")
    }

    patched = 0
    for row in rows:
        if row.get("bet_id") in target_bet_ids:
            for m in report["markets"]:
                if m["champion_position"]["ledger_bet_id"] == row["bet_id"]:
                    res = m["resolution"]
                    row["resolved_at_utc"] = res["ts_utc"]
                    row["resolution"] = res["outcome"]
                    row["pnl_usd"] = f"{res['champion_pnl_usd']:.2f}"
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

    # ---- 5. Generate POST_RUN.md from scratch (multi-model format) ----
    md = _render_post_run_v2(report, run_id, outcome, observed_range, by_model, ranked)
    post_run_path = run_dir / "POST_RUN.md"
    if dry_run:
        print("\n[DRY RUN] would write POST_RUN.md:")
        print(md)
    else:
        post_run_path.write_text(md, encoding="utf-8")
        print(f">> wrote: {post_run_path}")

    print(f"\n>> Run {run_id} finalized.")
    champ_pnl = target_market_entry["resolution"]["champion_pnl_usd"]
    if target_market_entry["resolution"]["champion_won"]:
        print(f">> Champion WIN. Actual P&L: +${champ_pnl:.2f}")
    else:
        print(f">> Champion LOSS. Actual P&L: ${champ_pnl:.2f}")
    return 0


def _render_post_run_v2(
    report: dict,
    run_id: str,
    outcome: int,
    observed_range: tuple,
    by_model: dict,
    ranked: list,
) -> str:
    """Generate the POST_RUN.md content for a multi-model v2 run."""
    target_ticker = report["event"].get("target_market_ticker", "?")
    title = report["event"].get("title", "?")
    champ_name = report["champion_at_time_of_run"]
    outcome_label = "YES" if outcome == 1 else "NO"
    # Kalshi bin conventions : 'B' = bounded bin (floor + cap), 'T' = tail bin
    # (floor only, cap=None, signifie "≥ floor"). Il existe aussi le cas
    # symétrique théorique d'un tail-bas (cap only, floor=None, "≤ cap") même
    # si pas observé sur les events Low/High actuels. Sans ce guard, le format
    # f"{None:.0f}" plante avec NoneType.__format__ — cf. daily-trading run #13
    # du 2026-05-20 où runs 008/009 résolus sur KXLOWTNYC-26MAY19-T72 (≥72°F)
    # ont produit rc=99 "unsupported format string passed to NoneType.__format__".
    lo, hi = observed_range[0], observed_range[1]
    if lo is None and hi is None:
        range_s = "?"
    elif hi is None:
        range_s = f"≥{lo:.0f}°F"
    elif lo is None:
        range_s = f"≤{hi:.0f}°F"
    else:
        range_s = f"{lo:.0f}-{hi:.0f}°F"

    # Per-model lines
    rows = []
    for name, info in by_model.items():
        if info.get("brier") is None:
            rows.append(f"- `{name}` ({info['role']}) — no prediction")
            continue
        marker = " ⭐" if name == ranked[0][0] else ""
        pnl_label = "P&L réel" if info.get("pnl_type") == "actual" else "P&L théorique"
        pnl_s = f"{info['pnl_usd']:+.2f}" if info.get("pnl_usd") is not None else "-"
        rows.append(
            f"- `{name}` ({info['role']}) — p_yes={info['p_yes']:.3f}, "
            f"Brier={info['brier']:.4f}, {pnl_label}=${pnl_s}{marker}"
        )
    rows_md = "\n".join(rows)

    champ_brier = by_model.get(champ_name, {}).get("brier")
    best = ranked[0][0] if ranked else None
    head_verdict = "Champion best ✓" if best == champ_name else f"Challenger `{best}` ahead this run"

    return f"""**Run {run_id} — résolu {outcome_label} · Multi-model A/B**

Event : {title}
Bin cible : `{target_ticker}` · Outcome : {outcome_label} · Low observée (bin gagnant) : {range_s}

Modèles en course (⭐ = best Brier sur ce run) :
{rows_md}

Verdict run {run_id} : {head_verdict}.

Champion actuel : `{champ_name}` (la ligne réelle du ledger paper_bets.csv = celle de ce modèle).
Challengers et baselines : positions shadow, P&L théorique, pas d'exposition réelle.

Compteur Phase 1 : voir `dashboard/public/predictor_manifest.json` après rebuild.

Règle de promotion : un challenger n'est pas promoté sur un seul win. Il faut N>=10 résolus avec rolling-mean Brier strictement inférieur ET sign test 1-sided p<0.10. Cf. `predictor/runs_learning/CHAMPION.json`.

Log complet : https://github.com/Elladriel80/aratea/blob/main/predictor/runs/{run_id}/report.json
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, help="Run id (e.g. '002', '003')")
    parser.add_argument("--dry-run", action="store_true",
                        help="Don't write any files, just print what would happen")
    args = parser.parse_args()
    return finalize(args.run, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
