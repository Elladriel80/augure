"""Calcul de taille de pari (Kelly fractionnel)."""
from __future__ import annotations


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
