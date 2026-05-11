"""Build a training dataset for the learned predictor.

Reads `predictor/data/predictions/forward_*.json`, joins with resolved
outcomes (fetched live from Kalshi), and produces a list of
(features_dict, outcome_int, metadata) tuples suitable for training.

Design notes:
  - For each ticker we keep the EARLIEST capture with a non-null
    yes_mid (so the snapshot has both model predictions and a real
    market quote at the same observation moment).
  - Drop rows with any feature missing — no imputation, no silent
    zero-fill. We'd rather lose rows than introduce ghost data.
  - Outcome is 1 if Kalshi resolved the market YES, 0 if NO, drop
    everything else.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Make `src` importable when run from anywhere
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import DATA_DIR  # noqa: E402
from src.learning.features import extract  # noqa: E402


def load_forward_records() -> list[dict]:
    """Load every record in every forward_*.json under data/predictions/.

    Annotate each record with its capture timestamp for later
    chronological sorting.
    """
    pred_dir = DATA_DIR / "predictions"
    files = sorted(pred_dir.glob("forward_*.json"))
    out: list[dict] = []
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        for r in data.get("records", []):
            r["_capture_at"] = data.get("snapshot_at")
            out.append(r)
    return out


def keep_earliest_with_quote(records: list[dict]) -> list[dict]:
    """For each ticker, keep the earliest capture with non-null yes_mid."""
    by_ticker: dict[str, dict] = {}
    for r in sorted(records, key=lambda x: x.get("_capture_at", "")):
        if r.get("yes_mid") is None:
            continue
        if r["ticker"] not in by_ticker:
            by_ticker[r["ticker"]] = r
    return list(by_ticker.values())


def fetch_resolutions(records: list[dict]) -> dict[str, str]:
    """Hit Kalshi to fetch resolution status for every unique event_ticker."""
    from src.kalshi.client import KalshiClient
    client = KalshiClient()
    events = sorted({r["event_ticker"] for r in records})
    resolutions: dict[str, str] = {}
    for ev_ticker in events:
        try:
            ev = client.get_event(ev_ticker, with_nested_markets=True)
            for m in ev.markets:
                if m.result in ("yes", "no"):
                    resolutions[m.ticker] = m.result
        except Exception as e:
            print(f"  [warn] {ev_ticker}: {type(e).__name__}: {e}")
    return resolutions


def build(spec) -> tuple[list[dict], list[int], list[dict]]:
    """Return (X_feature_dicts, y_outcomes, meta) for the given feature spec.

    `meta` carries ticker, target_date, capture_at, yes_mid per row —
    useful for time-based CV splits and per-row debugging.
    """
    all_records = load_forward_records()
    unique = keep_earliest_with_quote(all_records)
    resolutions = fetch_resolutions(unique)

    X: list[dict] = []
    y: list[int] = []
    meta: list[dict] = []
    for r in unique:
        outcome = resolutions.get(r["ticker"])
        if outcome not in ("yes", "no"):
            continue
        feats = extract(r, spec)
        if feats is None:
            continue
        X.append(feats)
        y.append(1 if outcome == "yes" else 0)
        meta.append({
            "ticker": r["ticker"],
            "event_ticker": r["event_ticker"],
            "target_date": r.get("target_date"),
            "capture_at": r.get("_capture_at"),
            "yes_mid": r.get("yes_mid"),
        })
    return X, y, meta
