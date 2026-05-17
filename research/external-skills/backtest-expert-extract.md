# backtest-expert — extrait

Source : <https://github.com/tradermonty/claude-trading-skills/tree/main/skills/backtest-expert>
Licence : MIT. Date d'extraction : 2026-05-17.

## SKILL.md (frontmatter)

```yaml
---
name: backtest-expert
description: Expert guidance for systematic backtesting of trading strategies. Use when developing, testing, stress-testing, or validating quantitative trading strategies. Covers "beating ideas to death" methodology, parameter robustness testing, slippage modeling, bias prevention, and interpreting backtest results. Applicable when user asks about backtesting, strategy validation, robustness testing, avoiding overfitting, or systematic trading development.
---
```

## Philosophie

> "Find strategies that 'break the least', not strategies that 'profit the most' on paper."

## Stress testing (verbatim)

**Parameter sensitivity**
- Test stop loss at 50 %, 75 %, 100 %, 125 %, 150 % of baseline
- Test profit target at 80 %, 90 %, 100 %, 110 %, 120 % of baseline
- Vary entry/exit timing by ±15-30 minutes
- Look for 'plateaus' of stable performance, not narrow spikes

**Execution friction**
- Increase slippage to 1.5-2x typical estimates
- Model worst-case fills (buy at ask+1 tick, sell at bid−1 tick)
- Add realistic order rejection scenarios

**Sample size**
- Absolute minimum: 30 trades
- Preferred: 100+ trades
- High confidence: 200+ trades

## Walk-forward validation (verbatim)

1. Optimize on training period (e.g., Year 1-3)
2. Test on validation period (Year 4)
3. Roll forward and repeat
4. Compare in-sample vs out-of-sample performance

**Warning signs** :
- Out-of-sample <50 % of in-sample performance
- Need frequent parameter re-optimization
- Parameters change dramatically between periods

## Common Failure Patterns (verbatim)

1. Parameter sensitivity
2. Regime-specific
3. Slippage sensitivity
4. Small sample
5. Look-ahead bias
6. Over-optimization

## Décision finale

Le script `evaluate_backtest.py` (référencé par le SKILL.md) score sur
5 dimensions : Sample Size, Expectancy, Risk Management, Robustness,
Execution Realism. Sortie : **Deploy / Refine / Abandon**.

## Mapping vs tournoi Aratea

Aratea a déjà :

- Champion `learned_v2` (LR L2 11 features)
- Challenger en rolling test
- Baseline `kalshi_mid` (le marché — l'imbattable de référence)
- BSS comme métrique de gate de promotion
- CI cron daily_auto

Ce qui manque :

| Pattern tradermonty | État Aratea | Action |
|---|---|---|
| Parameter sensitivity (variations ±25/50 %) | non vérifié | Ajouter `tests/test_param_sensitivity.py` |
| Slippage 1.5-2x | non modélisé | Modéliser `prix_kalshi + buffer_worst_case` |
| Sample minimum 30, preferred 100+ | seuil promo BSS sans seuil N | Aligner avec memo `project_seasonal_phase_b.md` (N≥50 Tier 1) |
| Walk-forward OOS < 50 % IS = warning | check implicite via tournoi | Formaliser comme gate |
| Survivorship | risque réel : on ne teste que NYC LOWT | Tester sur séries non-NYC pour mesurer la généralisation |
| Look-ahead bias | à auditer manuellement | Créer checklist `docs/backtest-audit.md` |

## Verdict réutilisation

Réutilisation conceptuelle, pas plug-and-play.

Trois éléments **vraiment** transposables :

1. **Le mantra "plateaus, not peaks"** : tester `EDGE_THRESHOLD` à 0.06, 0.08,
   0.10, 0.12, 0.15 et regarder si le sweet spot est large ou pointu. Si le
   gate ne marche qu'à exactement 0.10, c'est un signe d'over-fitting.
2. **Seuils de sample size 30/100/200** : aligner explicitement avec les
   gates Aratea. Le N≥50 du seasonal Phase B (Tier 1) tombe entre "absolute
   minimum" et "preferred" — défendable mais à documenter.
3. **Walk-forward formel** : sur 14 jours de live, c'est trop court pour
   du walk-forward propre. À utiliser pour Phase B (3-12 mois).
