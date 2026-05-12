"""build_dashboard_manifest.py — emit the predictor manifest for the dashboard.

Aggregates three sources of truth into a single static JSON consumed by the
read-only dashboard at `dashboard/app/algorithm`:

  1. `predictor/runs_learning/<ts>/run.json` — every immutable training run.
  2. `predictor/src/learning/FEATURES.md` — the named-hypothesis registry
     (current status, hypothesis, source URL, date_added).
  3. `predictor/data/ledger/paper_bets.csv` — aggregated paper-bet counters
     (no individual rows; only totals).

Output: `dashboard/public/predictor_manifest.json`.

The dashboard never reads from the predictor directory at runtime — Vercel
serves the manifest as a static asset under `/predictor_manifest.json`. This
script is wired as the `prebuild` npm hook so the manifest is regenerated on
every deploy.

Usage:
    python predictor/scripts/build_dashboard_manifest.py

Exit code 0 on success. Non-zero if a source file is missing or malformed
(fail loudly during CI so we never ship a stale manifest).
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = REPO_ROOT / "predictor" / "runs_learning"
LIVE_RUNS_DIR = REPO_ROOT / "predictor" / "runs"
FEATURES_MD = REPO_ROOT / "predictor" / "src" / "learning" / "FEATURES.md"
PAPER_BETS_CSV = REPO_ROOT / "predictor" / "data" / "ledger" / "paper_bets.csv"
OUTPUT_PATH = REPO_ROOT / "dashboard" / "public" / "predictor_manifest.json"

# Phase 1 paper-bet target encoded in the discovery plan (50 resolved bets).
PHASE_1_TARGET = 50


def _load_runs() -> list[dict[str, Any]]:
    """Read every `run.json` under runs_learning/, oldest first."""
    if not RUNS_DIR.exists():
        return []
    runs: list[dict[str, Any]] = []
    for sub in sorted(RUNS_DIR.iterdir()):
        if not sub.is_dir():
            continue
        run_file = sub / "run.json"
        if not run_file.exists():
            continue
        try:
            runs.append(json.loads(run_file.read_text(encoding="utf-8")))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"malformed run.json at {run_file}: {exc}")
    runs.sort(key=lambda r: r.get("timestamp_utc", ""))
    return runs


def _strip_md(cell: str) -> str:
    """Drop the backticks / outer whitespace from a Markdown table cell."""
    s = cell.strip()
    if s.startswith("`") and s.endswith("`") and len(s) > 1:
        s = s[1:-1]
    return s


def _parse_features_md() -> list[dict[str, Any]]:
    """Parse the registry table out of `FEATURES.md`.

    Robust enough for the current shape:
      | name | hypothesis | source | date_added | brier_delta | status |

    Rows whose name cell contains `TBD` markers are kept as-is — the
    dashboard layer formats them.
    """
    if not FEATURES_MD.exists():
        raise SystemExit(f"missing registry: {FEATURES_MD}")
    raw = FEATURES_MD.read_text(encoding="utf-8")

    # Find the registry table (first line starts with `| name |`).
    lines = raw.splitlines()
    header_idx = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("|") and "name" in stripped and "hypothesis" in stripped:
            header_idx = i
            break
    if header_idx is None:
        raise SystemExit("could not find registry header in FEATURES.md")

    # Skip header (|...|) and separator (|---|---|).
    data_start = header_idx + 2
    features: list[dict[str, Any]] = []
    for line in lines[data_start:]:
        stripped = line.strip()
        if not stripped.startswith("|"):
            break
        # split on | and drop the leading/trailing empty cells.
        cells = [c for c in stripped.split("|")]
        # leading | and trailing | create empty strings on both ends
        cells = cells[1:-1] if len(cells) >= 2 else cells
        if len(cells) < 6:
            continue
        name = _strip_md(cells[0])
        hypothesis = cells[1].strip()
        source = cells[2].strip()
        date_added = cells[3].strip()
        brier_delta_cell = cells[4].strip()
        status = cells[5].strip()

        brier_delta_value: float | None
        try:
            # Accept "+0.0020", "-0.0000", "0.0020"
            brier_delta_value = float(brier_delta_cell.replace("+", ""))
        except ValueError:
            brier_delta_value = None  # "TBD", "—", etc.

        features.append(
            {
                "name": name,
                "hypothesis": hypothesis,
                "source": source,
                "date_added": date_added,
                "registry_brier_delta": brier_delta_value,
                "registry_brier_delta_raw": brier_delta_cell,
                "status": status,
            }
        )
    return features


def _build_feature_history(
    registry: list[dict[str, Any]], runs: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Stitch the per-run measurements onto each registry feature."""
    out: list[dict[str, Any]] = []
    latest_run_by_feature: dict[str, dict[str, Any]] = {}
    for run in runs:
        deltas = run.get("feature_brier_deltas") or {}
        kept = set(run.get("kept_features") or [])
        dropped = set(run.get("dropped_features") or [])
        feature_set = run.get("feature_set_used") or ""
        ts = run.get("timestamp_utc") or ""
        for name, delta in deltas.items():
            entry = {
                "run_ts": ts,
                "feature_set": feature_set,
                "brier_delta": delta,
                "status": (
                    "dropped"
                    if name in dropped
                    else ("active" if name in kept else "experimental")
                ),
            }
            latest_run_by_feature[name] = entry

    for feat in registry:
        name = feat["name"]
        history = [
            {
                "run_ts": run.get("timestamp_utc"),
                "feature_set": run.get("feature_set_used"),
                "brier_delta": (run.get("feature_brier_deltas") or {}).get(name),
                "status": (
                    "dropped"
                    if name in set(run.get("dropped_features") or [])
                    else (
                        "active"
                        if name in set(run.get("kept_features") or [])
                        else None
                    )
                ),
            }
            for run in runs
            if name in (run.get("feature_brier_deltas") or {})
        ]
        # Latest measured delta wins for current_brier_delta. Fall back to
        # the registry value when the feature has never been in a run yet
        # (e.g. NDFD before forward captures accumulate).
        if history:
            current_brier_delta: float | None = history[-1]["brier_delta"]
        else:
            current_brier_delta = feat["registry_brier_delta"]
        out.append(
            {
                "name": name,
                "hypothesis": feat["hypothesis"],
                "source": feat["source"],
                "date_added": feat["date_added"],
                "current_status": feat["status"],
                "current_brier_delta": current_brier_delta,
                "current_brier_delta_raw": feat["registry_brier_delta_raw"],
                "history": history,
            }
        )
    return out


def _shape_runs_for_dashboard(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Trim run records to the fields the dashboard renders."""
    shaped: list[dict[str, Any]] = []
    for run in runs:
        brier_test = run.get("brier_test")
        brier_kalshi = run.get("brier_kalshi_mid_test")
        gap = None
        verdict = run.get("verdict")
        if isinstance(brier_test, (int, float)) and isinstance(brier_kalshi, (int, float)):
            gap = brier_test - brier_kalshi
            if verdict is None:
                # Heuristic when older runs predate the verdict field.
                if gap < -1e-4:
                    verdict = "LEARNED"
                elif gap > 1e-4:
                    verdict = "MARKET"
                else:
                    verdict = "TIE"
        shaped.append(
            {
                "ts": run.get("timestamp_utc"),
                "feature_set": run.get("feature_set_used"),
                "feature_names": run.get("feature_names") or [],
                "n_train": run.get("n_train"),
                "n_test": run.get("n_test"),
                "train_date_range": run.get("train_date_range"),
                "test_date_range": run.get("test_date_range"),
                "brier_train": run.get("brier_train"),
                "brier_test": brier_test,
                "brier_kalshi_mid_test": brier_kalshi,
                "log_loss_train": run.get("log_loss_train"),
                "log_loss_test": run.get("log_loss_test"),
                "log_loss_kalshi_mid_test": run.get("log_loss_kalshi_mid_test"),
                "gap_vs_kalshi_mid": gap,
                "verdict": verdict or "TIE",
                "notes": run.get("notes") or "",
            }
        )
    return shaped


def _normalize_live_run(report: dict[str, Any]) -> dict[str, Any] | None:
    """Convert a Run report.json (v1 or v2 schema) into a uniform shape for the dashboard.

    Returns None if the report is unusable (no markets, malformed, etc.).
    Output shape is the same across schemas — the React layer doesn't
    need to know whether the run is v1 or v2.
    """
    if not isinstance(report, dict) or "markets" not in report:
        return None
    markets = report.get("markets") or []
    if not markets:
        return None
    market = markets[0]  # current convention: one target market per run

    schema = int(report.get("schema_version", 1))
    run_id = report.get("run_id") or "?"
    ts_utc = report.get("ts_utc")

    event = report.get("event") or {}
    target_ticker = event.get("target_market_ticker") or market.get("ticker")

    snap = market.get("snapshot_pre") or {}
    kalshi_mid = snap.get("yes_mid")

    # Position (champion's) + resolution
    if schema >= 2:
        pos = market.get("champion_position") or {}
        champion_name = report.get("champion_at_time_of_run", "?")
    else:
        pos = market.get("position") or {}
        champion_name = "vendor_ensemble"

    resolution_raw = market.get("resolution") or {}
    has_outcome = resolution_raw.get("outcome") is not None
    status = "resolved" if has_outcome else "open"

    # Per-model snapshot (predicted p_yes + Brier post-resolution)
    models_out: list[dict[str, Any]] = []
    scoring = report.get("scoring") or {}
    by_model = (scoring.get("by_model") if isinstance(scoring, dict) else None) or {}

    if schema >= 2:
        for m in report.get("models") or []:
            score = by_model.get(m["name"], {}) if has_outcome else {}
            models_out.append({
                "name": m["name"],
                "role": m.get("role"),
                "method": m.get("method"),
                "p_yes": m.get("p_yes"),
                "brier": score.get("brier"),
                "won": score.get("won"),
                "pnl_usd": score.get("pnl_usd"),
                "pnl_type": score.get("pnl_type"),
            })
    else:
        # v1 — synthesize models from the legacy `model` block + kalshi_mid baseline.
        m_block = report.get("model") or {}
        p_model = m_block.get("p_yes")
        p_clim = m_block.get("p_yes_climatology")
        b_model = scoring.get("brier_model") if isinstance(scoring, dict) else None
        b_clim = scoring.get("brier_climatology") if isinstance(scoring, dict) else None
        b_kalshi = scoring.get("brier_kalshi_mid_entry") if isinstance(scoring, dict) else None
        outcome = resolution_raw.get("outcome")
        outcome_bin = 1 if outcome == "yes" else (0 if outcome == "no" else None)

        # Champion pnl (actual) computed from the position block
        actual_pnl = resolution_raw.get("pnl_usd")
        actual_won = resolution_raw.get("won")
        models_out.append({
            "name": "vendor_ensemble",
            "role": "champion",
            "method": "ensemble",
            "p_yes": p_model,
            "brier": b_model,
            "won": actual_won,
            "pnl_usd": actual_pnl,
            "pnl_type": "actual" if actual_pnl is not None else None,
        })
        if p_clim is not None:
            models_out.append({
                "name": "climatology",
                "role": "baseline",
                "method": "climatology",
                "p_yes": p_clim,
                "brier": b_clim,
                "won": None,
                "pnl_usd": None,
                "pnl_type": None,
            })
        if kalshi_mid is not None:
            models_out.append({
                "name": "kalshi_mid_baseline",
                "role": "baseline",
                "method": "kalshi_mid",
                "p_yes": kalshi_mid,
                "brier": b_kalshi,
                "won": None,
                "pnl_usd": None,
                "pnl_type": None,
            })

    # Champion P&L (uniform across schemas)
    if schema >= 2:
        champion_pnl = resolution_raw.get("champion_pnl_usd")
        champion_won = resolution_raw.get("champion_won")
    else:
        champion_pnl = resolution_raw.get("pnl_usd")
        champion_won = resolution_raw.get("won")

    return {
        "run_id": run_id,
        "schema_version": schema,
        "ts_utc": ts_utc,
        "event_ticker": event.get("ticker") or (target_ticker.rsplit("-", 1)[0] if target_ticker else "?"),
        "event_title": event.get("title", "?"),
        "target_market_ticker": target_ticker,
        "champion_name": champion_name,
        "kalshi_mid_at_entry": kalshi_mid,
        "position": {
            "side": pos.get("side"),
            "n_contracts": pos.get("n_contracts"),
            "entry_price": pos.get("entry_price"),
            "size_usd": pos.get("size_usd"),
            "entry_price_yes_cents": pos.get("entry_price_yes_cents"),
            "entry_price_no_cents": pos.get("entry_price_no_cents"),
        },
        "models": models_out,
        "resolution": {
            "status": status,
            "outcome": resolution_raw.get("outcome"),
            "observed_range_f": resolution_raw.get("observed_range_f"),
            "winning_bin_ticker": resolution_raw.get("winning_bin_ticker"),
            "ts_utc": resolution_raw.get("ts_utc"),
            "champion_pnl_usd": champion_pnl,
            "champion_won": champion_won,
        },
    }


def _load_live_runs() -> list[dict[str, Any]]:
    """Read every `runs/<id>/report.json` and normalize them."""
    if not LIVE_RUNS_DIR.exists():
        return []
    out: list[dict[str, Any]] = []
    for sub in sorted(LIVE_RUNS_DIR.iterdir()):
        if not sub.is_dir():
            continue
        report_file = sub / "report.json"
        if not report_file.exists():
            continue
        try:
            data = json.loads(report_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"malformed live report.json at {report_file}: {exc}")
        norm = _normalize_live_run(data)
        if norm is not None:
            out.append(norm)
    # Sort by run_id (zero-padded string compare works because we use 3-digit IDs)
    out.sort(key=lambda r: r.get("run_id", ""))
    return out


def _paper_bets_summary() -> dict[str, Any]:
    """Aggregate counters from the paper-bet ledger. No row-level leakage."""
    if not PAPER_BETS_CSV.exists():
        return {
            "n_open": 0,
            "n_resolved": 0,
            "pnl_usd_cumulative": 0.0,
            "phase_1_counter": f"0/{PHASE_1_TARGET}",
        }
    n_open = 0
    n_resolved = 0
    pnl_cum = 0.0
    with PAPER_BETS_CSV.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            resolution = (row.get("resolution") or "").strip()
            if resolution:
                n_resolved += 1
                try:
                    pnl_cum += float(row.get("pnl_usd") or 0.0)
                except ValueError:
                    pass
            else:
                n_open += 1
    total = n_open + n_resolved
    return {
        "n_open": n_open,
        "n_resolved": n_resolved,
        "pnl_usd_cumulative": round(pnl_cum, 2),
        "phase_1_counter": f"{total}/{PHASE_1_TARGET}",
    }


def main() -> int:
    runs = _load_runs()
    registry = _parse_features_md()
    features = _build_feature_history(registry, runs)
    shaped_runs = _shape_runs_for_dashboard(runs)
    paper_bets = _paper_bets_summary()

    # Pick the most recent test-set kalshi_mid Brier as the all-time bench
    # reference for the chart. Same row-set caveat from runs_learning/README
    # applies — but for a single-line chart annotation it's the honest pick.
    latest_kalshi_bench = None
    for r in reversed(shaped_runs):
        if isinstance(r.get("brier_kalshi_mid_test"), (int, float)):
            latest_kalshi_bench = r["brier_kalshi_mid_test"]
            break

    live_runs = _load_live_runs()

    manifest = {
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "schema_version": 2,
        "features": features,
        "runs": shaped_runs,             # learned-predictor training runs
        "live_runs": live_runs,           # Kalshi paper trades (Run 001, 002, 003, ...)
        "paper_bets_summary": paper_bets,
        "kalshi_mid_reference": latest_kalshi_bench,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(manifest, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )
    print(
        f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} "
        f"({len(shaped_runs)} training run(s), {len(live_runs)} live run(s), "
        f"{len(features)} feature(s))"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
