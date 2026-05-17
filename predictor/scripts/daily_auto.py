"""Autonomous daily orchestrator for Aratea Kalshi paper trading.

Triggered by .github/workflows/daily-trading.yml cron at 14:00 UTC.
Designed to run unattended — exits 0 on every non-catastrophic case so the
workflow never fails on missing data (e.g. event not yet published).

Workflow per invocation:
  1. Auto-finalize: for every run with a not-yet-resolved report.json,
     check Kalshi. If settled, run finalize_run.finalize().
  2. Auto-capture (multi-event): for each series in EVENT_SERIES_LIST, fetch
     tomorrow's event, score every parseable median bin with the champion
     (vendor_ensemble), select up to MAX_BINS_PER_EVENT bins that clear
     |edge vs kalshi_mid| >= EDGE_THRESHOLD and spread <= SPREAD_THRESHOLD.
     Capture each into its own run (write report.json + append ledger).
     Stake per run is sized via capped_kelly_size (quart-Kelly + 3 caps :
     per-trade 5 %, portfolio heat 10 %, cluster exposure 6 %). See RFC
     research/rfc/RFC-portfolio-heat-and-correlation-caps.md.
  3. Rebuild dashboard manifest.

The workflow then commits + pushes the result.

Idempotent: dedupe is per (event_ticker, market_ticker). With
MAX_BINS_PER_EVENT > 1 multiple open runs on the same event are legitimate;
only the same bin is suppressed if already open.

All thresholds and the event list are env-overridable for rollback:
  ARATEA_EDGE_THRESHOLD, ARATEA_SPREAD_THRESHOLD,
  ARATEA_MAX_BINS_PER_EVENT, ARATEA_EVENT_SERIES (comma-separated).

Skip conditions (auto-capture exits clean):
  - event not yet published on Kalshi (per series, others still scanned)
  - no parseable market could be scored
  - no median bin clears the thresholds
  - portfolio heat / cluster cap saturated (refusé strict, pas de redim.)
  - event_ticker dont la ville n'est pas dans CITY_TO_NOAA (warn + skip)

Usage:
    python predictor/scripts/daily_auto.py
    python predictor/scripts/daily_auto.py --dry-run
    # legacy single-event NYC-only behavior:
    ARATEA_EVENT_SERIES=KXLOWTNYC ARATEA_MAX_BINS_PER_EVENT=1 \\
        ARATEA_EDGE_THRESHOLD=0.10 ARATEA_SPREAD_THRESHOLD=0.05 \\
        python predictor/scripts/daily_auto.py
"""
from __future__ import annotations

import argparse
import csv
import json
import os
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
from src.predictors.parsers import SERIES_MAP  # noqa: E402
from src.config import SIMULATION  # noqa: E402
from src.simulation.clusters import BetContext, parse_city_from_ticker  # noqa: E402
from src.simulation.ledger import Ledger  # noqa: E402
from src.simulation.sizing import (  # noqa: E402
    PortfolioHeat,
    capped_kelly_size,
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
# All thresholds are env-overridable for a safe rollback path. To revert to the
# legacy single-event NYC-only behavior, set:
#   ARATEA_EDGE_THRESHOLD=0.10
#   ARATEA_SPREAD_THRESHOLD=0.05
#   ARATEA_EVENT_SERIES=KXLOWTNYC
#   ARATEA_MAX_BINS_PER_EVENT=1
EDGE_THRESHOLD = float(os.environ.get("ARATEA_EDGE_THRESHOLD", "0.05"))
SPREAD_THRESHOLD = float(os.environ.get("ARATEA_SPREAD_THRESHOLD", "0.08"))
# Cap on captures per event per day (post-dedupe). Multiplied by len(EVENT_SERIES_LIST)
# gives the theoretical upper bound on daily captures.
MAX_BINS_PER_EVENT = int(os.environ.get("ARATEA_MAX_BINS_PER_EVENT", "3"))

# Bankroll minimum viable. En dessous, on raise plutôt que continuer à
# trader sur capital dégradé : c'est un signal de corruption du ledger ou
# de bug du settlement worker, pas un état normal de fonctionnement.
MIN_VIABLE_BANKROLL_USD = 200.0

# Multi-event scan. Selected from the 29 Kalshi series confirmed valid by
# the 2026-05-17 audit (see SERIES_MAP in src/predictors/parsers.py). Chosen
# to maximize geographic diversity and to include both HIGH and LOW where
# Kalshi has them. 16 series × MAX_BINS_PER_EVENT (default 3) = up to ~48
# captures/day. All tickers below MUST exist in SERIES_MAP; the validation
# at the start of step_capture warns loudly if any drift in.
EVENT_SERIES_LIST = [
    s.strip() for s in os.environ.get(
        "ARATEA_EVENT_SERIES",
        # LOW temperature — 10 cities, broad regional coverage
        "KXLOWTNYC,KXLOWTLAX,KXLOWTSFO,KXLOWTCHI,"
        "KXLOWTDC,KXLOWTBOS,KXLOWTMIA,KXLOWTPHX,"
        "KXLOWTDEN,KXLOWTSEA,"
        # HIGH temperature — 6 most liquid HIGH series (also covers
        # additional geography: Atlanta is HIGH-only in our selection)
        "KXHIGHTSFO,KXHIGHTDC,KXHIGHTBOS,KXHIGHTPHX,"
        "KXHIGHTSEA,KXHIGHTATL",
    ).split(",") if s.strip()
]


# Kalshi tickers encode the date as 26MAY13 (yy MON dd, uppercase).
def _kalshi_date_token(d: date) -> str:
    return d.strftime("%y%b%d").upper()


RUNS_DIR = ROOT / "runs"
LEDGER_PATH = ROOT / "data" / "ledger" / "paper_bets.csv"


def _compute_current_bankroll() -> float:
    """Bankroll virtuel courant = starting + P&L des paris settled.

    Marqué-au-market sur le ledger paper-bet. Les paris non-settled ne
    contribuent pas (leur P&L est ``None``). Le résultat alimente
    ``capped_kelly_size`` : la fraction 5 % per-trade s'ajuste donc au
    capital effectivement disponible.

    Lève ``RuntimeError`` si le bankroll tombe sous ``MIN_VIABLE_BANKROLL_USD``
    — fail-fast pour ne pas trader sur capital dégradé (signal de
    corruption du ledger ou bug du settlement worker, pas un état normal).
    """
    ledger = Ledger(LEDGER_PATH)
    bets = ledger.read_all()
    realized_pnl = sum(b.pnl_usd for b in bets if b.pnl_usd is not None)
    bankroll = SIMULATION["starting_bankroll"] + realized_pnl
    if bankroll < MIN_VIABLE_BANKROLL_USD:
        raise RuntimeError(
            f"Bankroll dégradé sous seuil viable : ${bankroll:.2f} < "
            f"${MIN_VIABLE_BANKROLL_USD:.2f}. Signal de corruption du "
            f"ledger ou bug settlement — investiguer avant de relancer."
        )
    return bankroll


def _size_with_caps(
    *,
    target: dict,
    event_ticker: str,
    current_bankroll: float,
    portfolio: PortfolioHeat,
    settlement_date: date,
    bet_id: str,
) -> tuple[float, BetContext | None]:
    """Wrapper testable autour de ``capped_kelly_size``.

    Extrait du flow ``_capture_one_bin`` pour pouvoir tester la décision de
    sizing sans monter tous les mocks (KalshiClient, OpenMeteoClient,
    EnsemblePredictor, registry). Le caller reste responsable du
    ``portfolio.register(ctx)`` après confirmation d'écriture au ledger.

    Passe ``event_ticker`` (sans strike) à ``capped_kelly_size`` —
    ``target['ticker']`` est le ``market_ticker`` (avec strike ``-B50.5``)
    que ``parse_city_from_ticker`` ne saurait pas décoder.
    """
    side = "NO" if target["edge"] < 0 else "YES"
    return capped_kelly_size(
        prob_yes=target["p_champion"],
        market_yes_price=target["yes_mid"],
        side=side,
        bankroll=current_bankroll,
        market_ticker=event_ticker,
        settlement_date=settlement_date,
        bet_id=bet_id,
        portfolio=portfolio,
        kelly_fraction=SIMULATION["kelly_fraction"],
    )


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


def _select_target_bins(ev, champion_p_yes_by_ticker: dict[str, float]) -> list[dict]:
    """Return up to MAX_BINS_PER_EVENT qualifying bins, best edge first.

    Each bin must:
      - be parseable
      - have strike_type 'between' (median bin, not a tail T-bin)
      - have both yes_bid and yes_ask non-null (tradable)
      - be liquid: yes_bid > MIN_QUOTE and yes_ask < MAX_QUOTE
        (skips bins where market makers haven't posted yet — e.g. event
        just published, both quotes still at 0 → yes_mid 0 → can't trade)
      - spread <= SPREAD_THRESHOLD
      - |edge_vs_mid| >= EDGE_THRESHOLD
    Among qualifying bins, return the top MAX_BINS_PER_EVENT sorted by
    abs_edge descending (tie-break: smaller spread).

    Returns [] if no bin qualifies.
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
        return []

    # Sort by abs_edge descending; tie-break by smaller spread (cleaner trade).
    candidates.sort(key=lambda c: (-c["abs_edge"], c["spread"]))
    return candidates[:MAX_BINS_PER_EVENT]


def _already_captured_bin(event_ticker: str, market_ticker: str) -> Optional[str]:
    """Return run_id of an open run matching (event_ticker, market_ticker), or None.

    Dedupe is per-bin now (was per-event): with MAX_BINS_PER_EVENT > 1 we
    legitimately want multiple open runs on the same event, just not on the
    same bin.
    """
    if not RUNS_DIR.exists():
        return None
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
        ev_t = (data.get("event") or {}).get("ticker")
        if ev_t != event_ticker:
            continue
        for m in data.get("markets", []):
            if m.get("ticker") != market_ticker:
                continue
            if (m.get("resolution") or {}).get("outcome") is None:
                return run_dir.name
    return None


def _capture_one_bin(
    ev,
    target: dict,
    weather,
    registry: dict,
    portfolio: PortfolioHeat,
    current_bankroll: float,
    dry_run: bool,
) -> dict:
    """Capture one (event, bin) into runs/<NNN>/report.json + ledger.

    Extracted from the legacy single-bin step_capture so the multi-event loop
    can call it repeatedly without duplicating report-building logic.

    Sizing via ``_size_with_caps`` (Kelly fractionnel + 3 caps portfolio).
    Skip strict si :
      - parse_market échoue ;
      - la ville extraite de event_ticker n'est pas dans CITY_TO_NOAA
        (defensive : symétrique au validateur unknown_series de step_capture) ;
      - les caps portefeuille saturent (amount = 0 → refus pur, aucun
        redimensionnement à epsilon).
    """
    target_market = next(m for m in ev.markets if m.ticker == target["ticker"])
    spec = parse_market(target_market)
    if spec is None:
        print(f"   !! parse_market returned None on {target['ticker']}. skip.")
        return {"captured": False, "reason": "parse_market_failed_on_target",
                "event_ticker": ev.event_ticker, "market_ticker": target["ticker"]}

    side = "NO" if target["edge"] < 0 else "YES"
    ledger_bet_id = _bet_id() if not dry_run else "DRY_RUN_NO_LEDGER"

    try:
        size_usd, bet_ctx = _size_with_caps(
            target=target,
            event_ticker=ev.event_ticker,
            current_bankroll=current_bankroll,
            portfolio=portfolio,
            settlement_date=spec.target_date,
            bet_id=ledger_bet_id,
        )
    except ValueError as e:
        # Defensive : capped_kelly_size → spatial_cluster_for_ticker peut
        # lever si event_ticker pointe sur une ville absente de CITY_TO_NOAA
        # (cas drift env-override). On log + skip, on ne crashe pas le run.
        try:
            offending_city = parse_city_from_ticker(ev.event_ticker)
        except Exception:
            offending_city = "<parse échec>"
        print(f"   [skip] cluster inconnu pour event_ticker={ev.event_ticker} "
              f"(ville extraite='{offending_city}') : {e}")
        return {"captured": False, "reason": "unknown_cluster",
                "event_ticker": ev.event_ticker, "market_ticker": target["ticker"]}

    if size_usd == 0.0:
        heat_pct = portfolio.total_open_fraction() * 100
        print(f"   [skip] cap atteint pour {target['ticker']} side={side} "
              f"(heat={heat_pct:.1f}%, bankroll=${current_bankroll:.2f})")
        return {"captured": False, "reason": "cap_atteint",
                "event_ticker": ev.event_ticker, "market_ticker": target["ticker"],
                "heat_pct": heat_pct}

    # bet_ctx est garanti non-None puisque size_usd > 0 (cf. capped_kelly_size).
    assert bet_ctx is not None
    # Heat prédictive : ce que ce pari ajoutera une fois registered.
    heat_after_pct = (portfolio.total_open_fraction() + bet_ctx.fraction_engaged) * 100

    models = _predict_all_models(registry, weather, spec, target["yes_mid"])
    for m in models:
        p = f"{m['p_yes']:.3f}" if m["p_yes"] is not None else "  -  "
        print(f"     {m['name']:<22} role={m['role']:<10}  p_yes={p}")

    run_id = _next_run_id()
    print(f"   assigned run-id: {run_id} (bin={target['ticker']}, side={side}, "
          f"size=${size_usd:.2f})")

    pos = _compute_position(side, size_usd, target["yes_mid"])
    ts_utc = _now_iso()
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
                        **_compute_position(side, size_usd, target["yes_mid"]),
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
            f"Selection rule: top-{MAX_BINS_PER_EVENT} median bin(s) per event "
            f"with |edge_vs_mid|>={EDGE_THRESHOLD}, spread<={SPREAD_THRESHOLD}. "
            f"Champion {champion_name} edge={target['edge']:+.3f}, side={side}, "
            f"Kelly capped size=${size_usd:.2f} (bankroll=${current_bankroll:.2f}, "
            f"portfolio_heat_after_register={heat_after_pct:.1f}%)."
        ),
    }

    if dry_run:
        print(f"   [DRY RUN] would write runs/{run_id}/report.json")
        print(f"   [DRY RUN] would append ledger row (bet_id={ledger_bet_id})")
        print(f"   [DRY RUN] would register bet in portfolio "
              f"(heat: {portfolio.total_open_fraction()*100:.1f}% → {heat_after_pct:.1f}%)")
        return {"captured": True, "dry_run": True, "run_id": run_id,
                "event_ticker": ev.event_ticker, "market_ticker": target["ticker"],
                "side": side, "size_usd": size_usd}

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
        "stake_usd": size_usd,
        "entry_price": target["yes_mid"],
        "prob_model": champion_p_yes,
        "prob_market_implied": target["yes_mid"],
        "edge": (champion_p_yes - target["yes_mid"]) if champion_p_yes is not None else "",
        "method": champion_method,
        "spec": spec.describe(),
    })
    print(f"   appended ledger row (bet_id={ledger_bet_id})")

    # Register dans le portefeuille APRÈS confirmation d'écriture au ledger :
    # invariant "registered = écrit au disque" préservé. Le ledger reste la
    # source de vérité ; portfolio.register est juste la mise à jour
    # in-memory du cumul de heat pour le bin suivant dans la même boucle.
    portfolio.register(bet_ctx)
    print(f"   registered bet in portfolio (heat now {heat_after_pct:.1f}%)")

    return {"captured": True, "dry_run": False, "run_id": run_id,
            "event_ticker": ev.event_ticker, "market_ticker": target["ticker"],
            "side": side, "n_contracts": pos["n_contracts"], "size_usd": size_usd,
            "heat_after_pct": heat_after_pct}


def step_capture(dry_run: bool) -> dict:
    """Try to capture new runs across all EVENT_SERIES_LIST for tomorrow's events.

    For each event series, fetch tomorrow's event, score every parseable bin
    with the champion, select up to MAX_BINS_PER_EVENT qualifying bins, and
    capture each into its own run. Dedupe per (event_ticker, market_ticker).
    """
    print(">> step 2: auto-capture new runs (multi-event)")

    # Validate that every series in EVENT_SERIES_LIST is mapped to a city in
    # SERIES_MAP. Unmapped series will silently produce 0 captures because
    # parse_market returns None for them. The check is loud (printed warning),
    # not fatal — env-override use cases may legitimately point at new series
    # while the SERIES_MAP catches up.
    unknown_series = [s for s in EVENT_SERIES_LIST if s not in SERIES_MAP]
    if unknown_series:
        print(f"   [WARN] {len(unknown_series)} of {len(EVENT_SERIES_LIST)} "
              f"series in EVENT_SERIES_LIST are NOT in SERIES_MAP; they will "
              f"produce 0 captures (silent skip in parse_market):")
        for s in unknown_series:
            print(f"          - {s}")
        print(f"          To fix, add the missing prefix(es) to "
              f"src/predictors/parsers.py SERIES_MAP.")

    tomorrow = date.today() + timedelta(days=1)
    print(f"   target date : {tomorrow.isoformat()}")
    print(f"   event series: {len(EVENT_SERIES_LIST)} "
          f"({', '.join(EVENT_SERIES_LIST[:5])}"
          + (', ...' if len(EVENT_SERIES_LIST) > 5 else '') + ")")
    print(f"   thresholds  : |edge|>={EDGE_THRESHOLD}, spread<={SPREAD_THRESHOLD}, "
          f"max_bins/event={MAX_BINS_PER_EVENT}")

    # Bankroll courant + reconstruction du portefeuille AVANT toute capture.
    # step_finalize() a déjà tourné en step 1, donc le ledger reflète l'état
    # post-settlement le plus récent : reconstruct ici voit la heat actuelle.
    current_bankroll = _compute_current_bankroll()
    portfolio = PortfolioHeat.from_ledger(LEDGER_PATH, current_bankroll)
    print(f"   bankroll    : ${current_bankroll:.2f} (starting "
          f"${SIMULATION['starting_bankroll']:.2f} + P&L réalisé)")
    print(f"   portfolio   : {len(portfolio.open_bets)} pari(s) non-settled, "
          f"heat={portfolio.total_open_fraction()*100:.1f}% / "
          f"{portfolio.max_portfolio_heat*100:.0f}% cap")
    if portfolio.open_bets:
        for b in portfolio.open_bets:
            print(f"                 - {b.bet_id[:16]}  {b.market_ticker}  "
                  f"cluster={b.spatial_cluster}  fraction="
                  f"{b.fraction_engaged*100:.2f}%")

    client = KalshiClient()
    weather = OpenMeteoClient()
    ensemble = EnsemblePredictor(weather)
    registry = _load_champion_registry()

    per_event_summaries: list[dict] = []
    captures: list[dict] = []

    for series in EVENT_SERIES_LIST:
        event_ticker = f"{series}-{_kalshi_date_token(tomorrow)}"
        print(f"\n   ---- {event_ticker} ----")

        try:
            ev = client.get_event(event_ticker)
        except Exception as e:
            print(f"   [skip] event not yet published or fetch error: {e}")
            per_event_summaries.append({
                "event_ticker": event_ticker, "skipped": True,
                "reason": "event_not_published_or_error", "error": str(e),
            })
            continue

        print(f"   event title : {ev.title}  | markets: {len(ev.markets)}")

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
            per_event_summaries.append({
                "event_ticker": event_ticker, "skipped": True,
                "reason": "no_markets_scored",
            })
            continue

        targets = _select_target_bins(ev, champion_p_yes_by_ticker)
        if not targets:
            print(f"   [skip] no bin clears thresholds.")
            per_event_summaries.append({
                "event_ticker": event_ticker, "skipped": True,
                "reason": "no_bin_clears_thresholds",
            })
            continue

        print(f"   {len(targets)} qualifying bin(s) (cap {MAX_BINS_PER_EVENT})")

        event_captured = 0
        for target in targets:
            existing = _already_captured_bin(event_ticker, target["ticker"])
            if existing:
                print(f"   [dedupe] {target['ticker']} already open in run {existing}, skip.")
                continue
            side = "NO" if target["edge"] < 0 else "YES"
            print(f"   capture: {target['ticker']}  yes_mid={target['yes_mid']:.3f}  "
                  f"p_champion={target['p_champion']:.3f}  edge={target['edge']:+.3f}  "
                  f"side={side}")
            result = _capture_one_bin(
                ev=ev, target=target, weather=weather, registry=registry,
                portfolio=portfolio, current_bankroll=current_bankroll,
                dry_run=dry_run,
            )
            captures.append(result)
            if result.get("captured"):
                event_captured += 1

        per_event_summaries.append({
            "event_ticker": event_ticker, "skipped": False,
            "qualifying_bins": len(targets),
            "captured_count": event_captured,
        })

    n_captured = sum(1 for c in captures if c.get("captured"))
    print(f"\n   TOTAL: {n_captured} captures across "
          f"{len(EVENT_SERIES_LIST)} events scanned")

    return {
        "captured_count": n_captured,
        "captures": captures,
        "per_event": per_event_summaries,
    }


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
