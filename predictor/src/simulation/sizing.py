"""Calcul de taille de pari (Kelly fractionnel) + caps portefeuille.

Le sizing per-trade ``kelly_fractional_size`` est laissé inchangé. Au-dessus,
``PortfolioHeat`` + ``capped_kelly_size`` appliquent deux garde-fous
agrégés décrits dans ``research/rfc/RFC-portfolio-heat-and-correlation-caps.md`` :

- portfolio heat : somme des fractions engagées sur paris non-settled
  ≤ ``MAX_PORTFOLIO_HEAT`` (10 %).
- correlation cap : somme par cluster spatio-temporel (région NOAA × fenêtre
  settlement ≤ 3 jours) ≤ ``MAX_CLUSTER_EXPOSURE`` (6 %).

L'ordre d'application est *strictest constraint wins* : on prend le min des
trois caps (per-trade, heat, cluster) avant de redescendre dans le Kelly.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from .clusters import BetContext, NOAARegion, same_settlement_window, spatial_cluster_for_ticker
from .ledger import Ledger, PaperBet

MAX_FRACTION_PER_BET = 0.05
MAX_PORTFOLIO_HEAT = 0.10
MAX_CLUSTER_EXPOSURE = 0.06


def kelly_fractional_size(
    prob_yes: float,
    market_yes_price: float,
    side: str,
    kelly_fraction: float = 0.25,
    bankroll: float = 1000.0,
    max_fraction_per_bet: float = 0.05,
) -> float:
    """Calcule la taille de pari en USD selon Kelly fractionnel.

    Args:
        prob_yes: P(OUI) selon notre modèle, ∈ [0, 1]
        market_yes_price: prix du contrat OUI sur Kalshi (∈ [0, 1])
        side: "YES" ou "NO" (le pari à placer)
        kelly_fraction: fraction du Kelly théorique (0.25 = quart Kelly)
        bankroll: capital virtuel disponible
        max_fraction_per_bet: cap absolu par pari

    Returns:
        Montant en USD à miser. 0.0 si pari non rentable.
    """
    p_yes = max(1e-6, min(1 - 1e-6, prob_yes))
    px = max(0.01, min(0.99, market_yes_price))

    if side.upper() == "YES":
        # Acheter YES à 'px', payoff +1 si OUI, perte -px sinon (Kalshi paie 1$ sur résolution)
        # Edge = p_yes - px ; odds = (1-px)/px (gain si on gagne / mise)
        edge = p_yes - px
        b = (1 - px) / px           # net odds
        f_kelly = max(0.0, edge / b)  # fraction du bankroll
    elif side.upper() == "NO":
        p_no = 1 - p_yes
        px_no = 1 - px
        edge = p_no - px_no
        b = (1 - px_no) / px_no
        f_kelly = max(0.0, edge / b)
    else:
        raise ValueError(f"side doit être YES ou NO, reçu: {side}")

    f = min(f_kelly * kelly_fraction, max_fraction_per_bet)
    return round(f * bankroll, 2)


def _bet_context_from_paper_bet(
    bet: PaperBet, bankroll: float
) -> BetContext | None:
    """Construit un ``BetContext`` depuis une ligne de ledger paper-bet.

    Retourne ``None`` si le pari est settled (``resolved_at_utc`` non vide).
    Lève ``ValueError`` si :
      - le ``event_ticker`` n'est pas parseable,
      - la ville extraite n'est pas dans ``CITY_TO_NOAA``.

    Utilise ``event_ticker`` (sans strike) pour le clustering, **pas**
    ``market_ticker`` qui inclut le strike (ex. ``…-B50.5``) et n'est pas
    parseable par ``parse_city_from_ticker``.
    """
    if bet.resolved_at_utc:
        return None
    cluster = spatial_cluster_for_ticker(bet.event_ticker)
    fraction = bet.stake_usd / bankroll
    settlement_date = date.fromisoformat(bet.target_date)
    return BetContext(
        bet_id=bet.bet_id,
        market_ticker=bet.event_ticker,
        spatial_cluster=cluster,
        settlement_date=settlement_date,
        fraction_engaged=fraction,
    )


@dataclass
class PortfolioHeat:
    """État courant des paris non-settled, pour appliquer heat + cluster caps.

    Reconstruction au démarrage via ``from_ledger(ledger_path, bankroll)`` :
    pas de persistance disque séparée, le ledger paper-bet est la source de
    vérité unique. L'état in-memory est régénéré à chaque run de
    ``daily_auto`` depuis le CSV.
    """

    open_bets: list[BetContext] = field(default_factory=list)
    max_portfolio_heat: float = MAX_PORTFOLIO_HEAT
    max_cluster_exposure: float = MAX_CLUSTER_EXPOSURE
    max_fraction_per_bet: float = MAX_FRACTION_PER_BET
    cluster_window_days: int = 3

    @classmethod
    def from_ledger(
        cls,
        ledger_path: Path,
        bankroll: float,
        *,
        on_unknown_ticker: str = "warn",
        max_portfolio_heat: float = MAX_PORTFOLIO_HEAT,
        max_cluster_exposure: float = MAX_CLUSTER_EXPOSURE,
        max_fraction_per_bet: float = MAX_FRACTION_PER_BET,
        cluster_window_days: int = 3,
    ) -> PortfolioHeat:
        """Reconstruit l'état des paris non-settled depuis le ledger.

        ``on_unknown_ticker`` choisit la politique sur ville hors mapping :

        - ``"warn"`` (défaut) : ``print`` un warning + skip la ligne. Tolérant,
          ne crashe pas le driver si un env-override drift inject un ticker
          dont la ville n'a pas encore été ajoutée à ``CITY_TO_NOAA``.
        - ``"raise"`` : propage le ``ValueError``. À utiliser quand on veut
          détecter les drifts en hard fail (CI, tests).
        - ``"skip"`` : skip silencieusement. Déconseillé hors tests.

        Lève ``ValueError`` si ``on_unknown_ticker`` n'est pas reconnu.
        """
        if on_unknown_ticker not in ("warn", "raise", "skip"):
            raise ValueError(
                f"on_unknown_ticker doit être warn|raise|skip, reçu : "
                f"{on_unknown_ticker!r}"
            )
        portfolio = cls(
            max_portfolio_heat=max_portfolio_heat,
            max_cluster_exposure=max_cluster_exposure,
            max_fraction_per_bet=max_fraction_per_bet,
            cluster_window_days=cluster_window_days,
        )
        ledger = Ledger(ledger_path)
        for bet in ledger.read_all():
            try:
                ctx = _bet_context_from_paper_bet(bet, bankroll)
            except ValueError as e:
                if on_unknown_ticker == "raise":
                    raise
                if on_unknown_ticker == "warn":
                    print(
                        f"[warn] PortfolioHeat.from_ledger : ticker "
                        f"{bet.event_ticker!r} non clusterisable ({e}) — "
                        f"ligne skippée."
                    )
                continue
            if ctx is None:
                continue
            portfolio.register(ctx)
        return portfolio

    def total_open_fraction(self) -> float:
        return sum(b.fraction_engaged for b in self.open_bets)

    def cluster_open_fraction(
        self, cluster: NOAARegion, around_date: date
    ) -> float:
        return sum(
            b.fraction_engaged
            for b in self.open_bets
            if b.spatial_cluster == cluster
            and same_settlement_window(
                b.settlement_date, around_date, self.cluster_window_days
            )
        )

    def remaining_capacity(
        self, cluster: NOAARegion, around_date: date
    ) -> float:
        """Capacité résiduelle = min(heat_room, cluster_room, per_trade_room).

        Retourne 0.0 si l'un des caps est déjà saturé.
        """
        heat_room = max(0.0, self.max_portfolio_heat - self.total_open_fraction())
        cluster_room = max(
            0.0,
            self.max_cluster_exposure
            - self.cluster_open_fraction(cluster, around_date),
        )
        per_trade_room = self.max_fraction_per_bet
        return min(heat_room, cluster_room, per_trade_room)

    def register(self, bet: BetContext) -> None:
        if any(b.bet_id == bet.bet_id for b in self.open_bets):
            raise ValueError(f"bet_id déjà ouvert : {bet.bet_id!r}")
        self.open_bets.append(bet)

    def settle(self, bet_id: str) -> None:
        self.open_bets = [b for b in self.open_bets if b.bet_id != bet_id]


def capped_kelly_size(
    *,
    prob_yes: float,
    market_yes_price: float,
    side: str,
    bankroll: float,
    market_ticker: str,
    settlement_date: date,
    bet_id: str,
    portfolio: PortfolioHeat,
    kelly_fraction: float = 0.25,
) -> tuple[float, BetContext | None]:
    """Wrapper sur ``kelly_fractional_size`` appliquant heat + cluster caps.

    Calcule la capacité résiduelle du portefeuille (min des trois caps) puis
    la passe en ``max_fraction_per_bet`` au sizer per-trade. Si la capacité
    est nulle ou si le Kelly retourne 0.0, retourne ``(0.0, None)`` : refus
    pur, **jamais** de redimensionnement à epsilon (cf. RFC §2.3).

    Le caller est responsable d'appeler ``portfolio.register(ctx)`` après
    confirmation d'envoi du pari sur Kalshi — on ne l'enregistre pas ici
    pour éviter de gonfler la heat avec des paris jamais soumis.
    """
    if bankroll <= 0:
        return 0.0, None

    cluster = spatial_cluster_for_ticker(market_ticker)
    cap_fraction = portfolio.remaining_capacity(cluster, settlement_date)

    if cap_fraction <= 0.0:
        return 0.0, None

    amount = kelly_fractional_size(
        prob_yes=prob_yes,
        market_yes_price=market_yes_price,
        side=side,
        kelly_fraction=kelly_fraction,
        bankroll=bankroll,
        max_fraction_per_bet=cap_fraction,
    )

    if amount <= 0.0:
        return 0.0, None

    fraction = amount / bankroll
    ctx = BetContext(
        bet_id=bet_id,
        market_ticker=market_ticker,
        spatial_cluster=cluster,
        settlement_date=settlement_date,
        fraction_engaged=fraction,
    )
    return amount, ctx
