# position-sizer — extrait

Source : <https://github.com/tradermonty/claude-trading-skills/tree/main/skills/position-sizer>
Licence : MIT. Date d'extraction : 2026-05-17.

## SKILL.md (frontmatter)

```yaml
---
name: position-sizer
description: Calculate risk-based position sizes for long stock trades. Use when user asks about position sizing, how many shares to buy, risk per trade, Kelly criterion, ATR-based sizing, or portfolio risk allocation. Supports stop-loss distance calculation, volatility scaling, and sector concentration checks.
---
```

## Modes proposés

1. **Fixed Fractional** — 1 % du capital risqué par trade par défaut.
2. **ATR-Based** — risque par share = ATR × multiplicateur (2.0 par défaut).
3. **Kelly Criterion** — calcul `W - (1-W)/R`, half-Kelly recommandé.

Contraintes portfolio : `max-position-pct`, `max-sector-pct`,
`current-sector-exposure`. La plus stricte gagne.

## Key Principles (verbatim)

1. Survival first
2. The 1 % rule: Default to 1 % risk per trade; never exceed 2 % without exceptional reason
3. Round down: Always round shares down to whole numbers
4. Strictest constraint wins
5. **Half Kelly: Never use full Kelly in practice; half Kelly captures 75 % of growth with far less risk**
6. **Portfolio heat: Total open risk should not exceed 6-8 % of account equity**
7. Asymmetry of losses

## Code Python — fonction Kelly (verbatim, `scripts/position_sizer.py`)

```python
def calculate_kelly(params: SizingParameters) -> dict:
    """Kelly Criterion calculation.

    Kelly % = W - (1-W)/R
    where W = win_rate, R = avg_win / avg_loss
    Half-Kelly = kelly_pct / 2 (recommended conservative amount)
    Negative expectancy floors at 0%.
    """
    w = params.win_rate
    r = params.avg_win / params.avg_loss
    kelly_pct = w - (1 - w) / r
    kelly_pct = max(0.0, kelly_pct) * 100  # Convert to percentage, floor at 0
    half_kelly_pct = kelly_pct / 2
    return {
        "method": "kelly",
        "kelly_pct": round(kelly_pct, 2),
        "half_kelly_pct": round(half_kelly_pct, 2),
    }
```

## Mapping vs `Aratea/predictor/src/simulation/sizing.py`

Aratea utilise déjà la formule équivalente sur payoff binaire Kalshi :

```python
# Aratea — kelly_fractional_size (existant)
edge = p_yes - px
b = (1 - px) / px              # net odds
f_kelly = max(0.0, edge / b)   # fraction du bankroll
f = min(f_kelly * kelly_fraction, max_fraction_per_bet)
```

Démonstration que les deux formules sont identiques sur payoff binaire :

- Pari YES à prix `px` sur Kalshi : payoff = 1 si vrai, 0 sinon. Mise = `px`
  par contrat. Gain net si vrai = `1 − px`. Perte si faux = `px`.
- En notation tradermonty : `R = avg_win / avg_loss = (1 − px) / px = b`,
  `W = p_yes`.
- Donc `kelly = W − (1 − W) / R = p_yes − (1 − p_yes) / b = (p_yes · b − (1 − p_yes)) / b = (p_yes − px) / b = edge / b`.
- **Les deux expressions sont algébriquement identiques.**

## Différences de paramétrage

| | tradermonty | Aratea |
|---|---|---|
| Fraction recommandée | half-Kelly (α=0.5) | quart-Kelly (α=0.25) |
| Cap absolu par trade | non explicite | `max_fraction_per_bet=0.05` |
| Floor edge négatif | `max(0, kelly)` | `max(0, edge/b)` |
| Bornes numériques | sur win_rate | sur `p_yes` et `px` (1e-6 / 0.01) |
| Portfolio heat (cap somme positions ouvertes) | **6-8 %** explicite | **absent** |
| Contrainte de concentration sector/event | `max-sector-pct` | **absente** |

## Verdict réutilisation

- **Sizing per-trade : rien à changer.** Aratea est déjà conforme et plus conservateur
  (α=0.25 vs α=0.5). Le cap dur à 5 % est raisonnable en Phase 1.
- **Portfolio heat : à importer.** Aujourd'hui rien n'empêche d'ouvrir 5 paris
  simultanés à 5 % chacun = 25 % du bankroll exposé. Le concept "Total open
  risk ≤ 6-8 %" est directement transposable.
- **Cap concentration : à importer, mais redéfinir la dimension.** L'analogue
  Kalshi du "sector" n'est pas évident (région ? type de marché ? même front
  météo ?). Voir RFC associé.
