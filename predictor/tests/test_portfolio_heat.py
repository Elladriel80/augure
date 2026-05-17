"""Tests des caps portfolio heat + correlation sur ``capped_kelly_size``.

Couvre les 6 scénarios listés dans
``research/rfc/RFC-portfolio-heat-and-correlation-caps.md`` §3 et l'addendum
de spec (refus pur quand ``remaining_capacity == 0``).
"""
from __future__ import annotations

from datetime import date

from src.simulation.clusters import BetContext
from src.simulation.sizing import (
    MAX_CLUSTER_EXPOSURE,
    MAX_FRACTION_PER_BET,
    MAX_PORTFOLIO_HEAT,
    PortfolioHeat,
    capped_kelly_size,
)

# Edge volontairement énorme (P=0.99 vs px=0.50) pour que le Kelly veuille
# parier large : ainsi le seul facteur limitant est le cap portefeuille.
HUGE_EDGE_KW = dict(prob_yes=0.99, market_yes_price=0.50, side="YES")
BANKROLL = 1000.0
TODAY = date(2026, 5, 17)


def _open_bet(
    bet_id: str,
    ticker: str,
    cluster: str,
    settlement_date: date,
    fraction: float,
) -> BetContext:
    return BetContext(
        bet_id=bet_id,
        market_ticker=ticker,
        spatial_cluster=cluster,  # type: ignore[arg-type]
        settlement_date=settlement_date,
        fraction_engaged=fraction,
    )


# --- 1. Heat cap ----------------------------------------------------------
def test_heat_cap_blocks_excessive_total_exposure() -> None:
    portfolio = PortfolioHeat()
    # Heat déjà saturée : 2 paris à 5 % = 10 % (= MAX_PORTFOLIO_HEAT).
    portfolio.register(_open_bet("a", "KXLOWTNYC-26MAY15", "NE", TODAY, 0.05))
    portfolio.register(_open_bet("b", "KXLOWTLAX-26MAY15", "SW", TODAY, 0.05))
    assert portfolio.total_open_fraction() == MAX_PORTFOLIO_HEAT

    amount, ctx = capped_kelly_size(
        **HUGE_EDGE_KW,
        bankroll=BANKROLL,
        market_ticker="KXLOWTCHI-26MAY17",  # cluster MW, vierge
        settlement_date=TODAY,
        bet_id="c",
        portfolio=portfolio,
    )
    assert amount == 0.0
    assert ctx is None


# --- 2. Cluster cap -------------------------------------------------------
def test_cluster_cap_blocks_correlated_bets() -> None:
    # Trois villes NE (NYC, BOS, PHIL) dans la même fenêtre 3 j.
    portfolio = PortfolioHeat()
    portfolio.register(_open_bet("a", "KXLOWTNYC-26MAY17", "NE", TODAY, 0.03))
    portfolio.register(_open_bet("b", "KXLOWTBOS-26MAY18", "NE", date(2026, 5, 18), 0.03))
    # Cluster NE déjà à 6 % = MAX_CLUSTER_EXPOSURE.
    assert portfolio.cluster_open_fraction("NE", TODAY) == MAX_CLUSTER_EXPOSURE

    amount, ctx = capped_kelly_size(
        **HUGE_EDGE_KW,
        bankroll=BANKROLL,
        market_ticker="KXLOWTPHIL-26MAY19",
        settlement_date=date(2026, 5, 19),
        bet_id="c",
        portfolio=portfolio,
    )
    assert amount == 0.0
    assert ctx is None


# --- 3. Clusters indépendants ---------------------------------------------
def test_independent_clusters_dont_interfere() -> None:
    portfolio = PortfolioHeat()
    portfolio.register(_open_bet("a", "KXLOWTNYC-26MAY17", "NE", TODAY, 0.05))
    # CHI (cluster MW) ne partage pas le cluster NE. Cluster MW vierge :
    # cluster_room = 6 %, heat_room = 10 - 5 = 5 %, per_trade = 5 %.
    # Le sizing accepte donc 5 % (= 50 USD sur 1000 de bankroll).
    amount, ctx = capped_kelly_size(
        **HUGE_EDGE_KW,
        bankroll=BANKROLL,
        market_ticker="KXLOWTCHI-26MAY17",
        settlement_date=TODAY,
        bet_id="b",
        portfolio=portfolio,
    )
    assert amount == 50.0
    assert ctx is not None
    assert ctx.spatial_cluster == "MW"


# --- 4. Settle libère la heat ---------------------------------------------
def test_settled_bets_release_heat() -> None:
    portfolio = PortfolioHeat()
    portfolio.register(_open_bet("a", "KXLOWTNYC-26MAY15", "NE", TODAY, 0.05))
    portfolio.register(_open_bet("b", "KXLOWTLAX-26MAY15", "SW", TODAY, 0.05))
    assert portfolio.total_open_fraction() == 0.10

    portfolio.settle("a")
    assert portfolio.total_open_fraction() == 0.05
    # Settle d'un id inconnu = no-op.
    portfolio.settle("ghost")
    assert portfolio.total_open_fraction() == 0.05

    # On peut maintenant prendre un nouveau pari (cluster MW, frais).
    amount, ctx = capped_kelly_size(
        **HUGE_EDGE_KW,
        bankroll=BANKROLL,
        market_ticker="KXLOWTCHI-26MAY17",
        settlement_date=TODAY,
        bet_id="c",
        portfolio=portfolio,
    )
    assert amount > 0.0
    assert ctx is not None


# --- 5. Refus pur quand cap = 0 ------------------------------------------
def test_zero_cap_means_refuse_pure() -> None:
    """Garde-fou non-négociable : retour strict (0.0, None) sans epsilon
    ni minimum bet, sinon le predictor apprend sur du bruit de remplissage."""
    portfolio = PortfolioHeat()
    portfolio.register(_open_bet("a", "KXLOWTNYC-26MAY17", "NE", TODAY, 0.05))
    portfolio.register(_open_bet("b", "KXLOWTLAX-26MAY17", "SW", TODAY, 0.05))
    assert portfolio.remaining_capacity("MW", TODAY) == 0.0

    amount, ctx = capped_kelly_size(
        **HUGE_EDGE_KW,
        bankroll=BANKROLL,
        market_ticker="KXLOWTCHI-26MAY17",
        settlement_date=TODAY,
        bet_id="c",
        portfolio=portfolio,
    )
    assert amount == 0.0
    assert ctx is None


# --- 6. Strictest constraint wins ----------------------------------------
def test_strictest_wins_heat_binding() -> None:
    # Heat used 7 %, cluster MW vierge → heat_room = 3 %, cluster_room = 6 %,
    # per_trade = 5 % → min = 3 % (heat binding).
    portfolio = PortfolioHeat()
    portfolio.register(_open_bet("a", "KXLOWTNYC-26MAY15", "NE", TODAY, 0.04))
    portfolio.register(_open_bet("b", "KXLOWTLAX-26MAY15", "SW", TODAY, 0.03))

    amount, ctx = capped_kelly_size(
        **HUGE_EDGE_KW,
        bankroll=BANKROLL,
        market_ticker="KXLOWTCHI-26MAY17",
        settlement_date=TODAY,
        bet_id="c",
        portfolio=portfolio,
    )
    assert amount == 30.0  # 3 % * 1000
    assert ctx is not None
    assert ctx.fraction_engaged == 0.03


def test_strictest_wins_cluster_binding() -> None:
    # Heat used 2 %, cluster NE used 4 % → heat_room = 8 %, cluster_room = 2 %,
    # per_trade = 5 % → min = 2 % (cluster binding).
    portfolio = PortfolioHeat()
    portfolio.register(_open_bet("a", "KXLOWTNYC-26MAY17", "NE", TODAY, 0.02))
    portfolio.register(_open_bet("b", "KXLOWTBOS-26MAY17", "NE", TODAY, 0.02))

    amount, ctx = capped_kelly_size(
        **HUGE_EDGE_KW,
        bankroll=BANKROLL,
        market_ticker="KXLOWTPHIL-26MAY17",
        settlement_date=TODAY,
        bet_id="c",
        portfolio=portfolio,
    )
    assert amount == 20.0  # 2 % * 1000
    assert ctx is not None


def test_strictest_wins_per_trade_binding() -> None:
    # Portefeuille vierge → heat_room = 10 %, cluster_room = 6 %,
    # per_trade = 5 % → min = 5 % (per-trade binding).
    portfolio = PortfolioHeat()
    amount, ctx = capped_kelly_size(
        **HUGE_EDGE_KW,
        bankroll=BANKROLL,
        market_ticker="KXLOWTNYC-26MAY17",
        settlement_date=TODAY,
        bet_id="c",
        portfolio=portfolio,
    )
    assert amount == 50.0  # 5 % * 1000 = MAX_FRACTION_PER_BET
    assert ctx is not None
    assert ctx.fraction_engaged == MAX_FRACTION_PER_BET


# --- Garde-fous additionnels ----------------------------------------------
def test_zero_bankroll_returns_refusal() -> None:
    portfolio = PortfolioHeat()
    amount, ctx = capped_kelly_size(
        **HUGE_EDGE_KW,
        bankroll=0.0,
        market_ticker="KXLOWTNYC-26MAY17",
        settlement_date=TODAY,
        bet_id="x",
        portfolio=portfolio,
    )
    assert amount == 0.0
    assert ctx is None


def test_no_edge_returns_refusal_without_registering() -> None:
    # Kelly = 0 (prob_yes = px) → amount = 0 → ctx None, rien n'est ajouté.
    portfolio = PortfolioHeat()
    amount, ctx = capped_kelly_size(
        prob_yes=0.50,
        market_yes_price=0.50,
        side="YES",
        bankroll=BANKROLL,
        market_ticker="KXLOWTNYC-26MAY17",
        settlement_date=TODAY,
        bet_id="x",
        portfolio=portfolio,
    )
    assert amount == 0.0
    assert ctx is None
    assert portfolio.open_bets == []


def test_caller_must_register_ctx_explicitly() -> None:
    # Le wrapper renvoie le ctx mais ne l'enregistre pas — caller responsable.
    portfolio = PortfolioHeat()
    amount, ctx = capped_kelly_size(
        **HUGE_EDGE_KW,
        bankroll=BANKROLL,
        market_ticker="KXLOWTNYC-26MAY17",
        settlement_date=TODAY,
        bet_id="x",
        portfolio=portfolio,
    )
    assert amount > 0.0
    assert ctx is not None
    assert portfolio.open_bets == []  # pas auto-registered
    portfolio.register(ctx)
    assert portfolio.open_bets == [ctx]
