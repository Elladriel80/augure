"""Tests de la reconstruction de ``PortfolioHeat`` depuis le ledger CSV.

Le helper ``_bet_context_from_paper_bet`` et la classmethod
``PortfolioHeat.from_ledger`` doivent :
  - skipper les paris settled (``resolved_at_utc`` non vide),
  - utiliser ``event_ticker`` (sans strike) pour le clustering, pas
    ``market_ticker``,
  - calculer ``fraction_engaged = stake_usd / bankroll``,
  - gérer les villes inconnues via ``on_unknown_ticker`` (warn/raise/skip).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.simulation.sizing import (
    PortfolioHeat,
    _bet_context_from_paper_bet,
)
from src.simulation.ledger import Ledger, PaperBet


_HEADER = (
    "bet_id,placed_at_utc,market_ticker,event_ticker,target_date,side,"
    "stake_usd,entry_price,prob_model,prob_market_implied,edge,method,spec,"
    "resolved_at_utc,resolution,pnl_usd\n"
)


def _write_ledger(path: Path, rows: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_HEADER + "".join(rows), encoding="utf-8")


def _row(
    *,
    bet_id: str,
    event_ticker: str,
    market_ticker: str | None = None,
    target_date: str,
    stake_usd: float = 100.0,
    side: str = "NO",
    resolved: bool = False,
    pnl: float | None = None,
) -> str:
    mt = market_ticker or f"{event_ticker}-B50.5"
    resolved_at = "2026-05-15T19:00:00Z" if resolved else ""
    resolution = "yes" if resolved else ""
    pnl_str = "" if pnl is None else str(pnl)
    return (
        f"{bet_id},2026-05-10T17:00:00Z,{mt},{event_ticker},{target_date},"
        f"{side},{stake_usd},0.36,0.146,0.36,-0.21,ensemble,test bet,"
        f"{resolved_at},{resolution},{pnl_str}\n"
    )


# --- 1. Seuls les paris non-resolved sont chargés -------------------------
def test_from_ledger_loads_only_unresolved(tmp_path: Path) -> None:
    path = tmp_path / "paper_bets.csv"
    _write_ledger(
        path,
        [
            _row(bet_id="a", event_ticker="KXLOWTNYC-26MAY11",
                 target_date="2026-05-11", resolved=True, pnl=50.0),
            _row(bet_id="b", event_ticker="KXLOWTNYC-26MAY12",
                 target_date="2026-05-12", resolved=True, pnl=-100.0),
            _row(bet_id="c", event_ticker="KXLOWTNYC-26MAY17",
                 target_date="2026-05-17", resolved=False),
        ],
    )
    portfolio = PortfolioHeat.from_ledger(path, bankroll=1000.0)
    assert len(portfolio.open_bets) == 1
    assert portfolio.open_bets[0].bet_id == "c"


# --- 2. CRITIQUE — event_ticker (sans strike) pour le clustering ----------
def test_from_ledger_uses_event_ticker_for_cluster(tmp_path: Path) -> None:
    """Garde-fou non-négociable : le parser ne doit JAMAIS voir le strike.

    Si l'implémentation utilise ``market_ticker`` (qui inclut ``-B50.5``),
    ``parse_city_from_ticker`` lève sur le segment date malformé et ce test
    explose avec un ValueError au lieu de passer.
    """
    path = tmp_path / "paper_bets.csv"
    _write_ledger(
        path,
        [
            _row(
                bet_id="x",
                event_ticker="KXLOWTNYC-26MAY17",
                market_ticker="KXLOWTNYC-26MAY17-B50.5",
                target_date="2026-05-17",
                resolved=False,
            ),
        ],
    )
    portfolio = PortfolioHeat.from_ledger(path, bankroll=1000.0)
    assert len(portfolio.open_bets) == 1
    assert portfolio.open_bets[0].spatial_cluster == "NE"
    # Sanity : le ticker stocké dans BetContext est bien l'event_ticker.
    assert portfolio.open_bets[0].market_ticker == "KXLOWTNYC-26MAY17"


# --- 3. fraction_engaged = stake / bankroll -------------------------------
def test_from_ledger_fraction_uses_bankroll(tmp_path: Path) -> None:
    path = tmp_path / "paper_bets.csv"
    _write_ledger(
        path,
        [
            _row(bet_id="a", event_ticker="KXLOWTNYC-26MAY17",
                 target_date="2026-05-17", stake_usd=100.0, resolved=False),
        ],
    )
    portfolio = PortfolioHeat.from_ledger(path, bankroll=1000.0)
    assert portfolio.open_bets[0].fraction_engaged == pytest.approx(0.10)

    # Avec un bankroll plus petit, la fraction grimpe.
    portfolio2 = PortfolioHeat.from_ledger(path, bankroll=500.0)
    assert portfolio2.open_bets[0].fraction_engaged == pytest.approx(0.20)


# --- 4. on_unknown_ticker="warn" (défaut) ---------------------------------
def test_from_ledger_warns_on_unknown_city(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "paper_bets.csv"
    _write_ledger(
        path,
        [
            _row(bet_id="a", event_ticker="KXLOWTZZZ-26MAY17",
                 target_date="2026-05-17", resolved=False),
            _row(bet_id="b", event_ticker="KXLOWTNYC-26MAY17",
                 target_date="2026-05-17", resolved=False),
        ],
    )
    portfolio = PortfolioHeat.from_ledger(path, bankroll=1000.0)
    # ZZZ skippé, NYC chargé.
    assert len(portfolio.open_bets) == 1
    assert portfolio.open_bets[0].bet_id == "b"
    captured = capsys.readouterr()
    assert "warn" in captured.out.lower()
    assert "ZZZ" in captured.out


# --- 5. on_unknown_ticker="raise" -----------------------------------------
def test_from_ledger_raises_on_unknown_city(tmp_path: Path) -> None:
    path = tmp_path / "paper_bets.csv"
    _write_ledger(
        path,
        [
            _row(bet_id="a", event_ticker="KXLOWTZZZ-26MAY17",
                 target_date="2026-05-17", resolved=False),
        ],
    )
    with pytest.raises(ValueError, match="absente du mapping NOAA"):
        PortfolioHeat.from_ledger(
            path, bankroll=1000.0, on_unknown_ticker="raise"
        )


# --- 6. Fichier vide ------------------------------------------------------
def test_from_ledger_empty_file_returns_empty(tmp_path: Path) -> None:
    path = tmp_path / "paper_bets.csv"
    _write_ledger(path, [])  # header seul
    portfolio = PortfolioHeat.from_ledger(path, bankroll=1000.0)
    assert portfolio.open_bets == []


# --- Bonus : politique on_unknown_ticker invalide -------------------------
def test_from_ledger_invalid_policy_raises(tmp_path: Path) -> None:
    path = tmp_path / "paper_bets.csv"
    _write_ledger(path, [])
    with pytest.raises(ValueError, match="on_unknown_ticker"):
        PortfolioHeat.from_ledger(
            path, bankroll=1000.0, on_unknown_ticker="ignore_lol"
        )


# --- Bonus : helper unitaire ----------------------------------------------
def test_helper_returns_none_on_settled_bet() -> None:
    bet = PaperBet(
        bet_id="x", placed_at_utc="2026-05-10T17:00:00Z",
        market_ticker="KXLOWTNYC-26MAY11-B50.5",
        event_ticker="KXLOWTNYC-26MAY11",
        target_date="2026-05-11", side="NO", stake_usd=100.0,
        entry_price=0.36, prob_model=0.146, prob_market_implied=0.36,
        edge=-0.21, method="ensemble", spec="test",
        resolved_at_utc="2026-05-12T12:00:00Z", resolution="no", pnl_usd=56.0,
    )
    assert _bet_context_from_paper_bet(bet, bankroll=1000.0) is None


def test_helper_skips_market_ticker_in_favor_of_event_ticker() -> None:
    bet = PaperBet(
        bet_id="x", placed_at_utc="2026-05-10T17:00:00Z",
        market_ticker="KXLOWTNYC-26MAY11-B50.5",  # PIÈGE
        event_ticker="KXLOWTNYC-26MAY11",        # CORRECT
        target_date="2026-05-11", side="NO", stake_usd=50.0,
        entry_price=0.36, prob_model=0.146, prob_market_implied=0.36,
        edge=-0.21, method="ensemble", spec="test",
    )
    ctx = _bet_context_from_paper_bet(bet, bankroll=1000.0)
    assert ctx is not None
    assert ctx.spatial_cluster == "NE"
    assert ctx.fraction_engaged == pytest.approx(0.05)
