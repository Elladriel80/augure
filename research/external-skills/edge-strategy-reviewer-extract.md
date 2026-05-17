# edge-strategy-reviewer — extrait

Source : <https://github.com/tradermonty/claude-trading-skills/tree/main/skills/edge-strategy-reviewer>
Licence : MIT. Date d'extraction : 2026-05-17.

**Note** : ce skill remplace le `signal-postmortem` mentionné lors de
l'exploration initiale, qui n'existe pas dans le repo. `edge-strategy-reviewer`
est le pattern le plus proche d'une review-gate structurée.

## SKILL.md (frontmatter)

```yaml
---
name: edge-strategy-reviewer
description: >
  Critically review strategy drafts from edge-strategy-designer for edge
  plausibility, overfitting risk, sample size adequacy, and execution realism.
  Use when strategy_drafts/*.yaml exists and needs quality gate before pipeline
  export. Outputs PASS/REVISE/REJECT verdicts with confidence scores.
---
```

## Schéma de classification

Il review des **brouillons de stratégie** (YAML produits en amont par
`edge-strategy-designer`). Labels finaux :

- **PASS** — `export_eligible = true`
- **REVISE** — révisions demandées avant export
- **REJECT** — recaler la stratégie

Chaque verdict est accompagné d'un `confidence` ∈ [0, 100] et d'une liste de
`findings` avec severity.

## Checklist 8 critères (verbatim)

| # | Criterion | Weight | Key Checks |
|---|---|---|---|
| C1 | Edge Plausibility | 20 | Thesis quality, domain terms, mechanism keywords (continuous 50-95) |
| C2 | Overfitting Risk | 20 | 5-tier filter count scoring (90/80/60/40/10), precise threshold penalty |
| C3 | Sample Adequacy | 15 | Continuous scoring from estimated annual opportunities (10-95) |
| C4 | Regime Dependency | 10 | Cross-regime validation |
| C5 | Exit Calibration | 10 | Stop-loss, reward-to-risk |
| C6 | Risk Concentration | 10 | Position sizing limits |
| C7 | Execution Realism | 10 | Volume filter, export consistency |
| C8 | Invalidation Quality | 5 | Signal count and specificity |

## Verdict logic (verbatim)

> "C1 or C2 severity=fail → immediate REJECT
>  confidence >= 70, no fail findings → PASS
>  confidence < 35 → REJECT
>  Otherwise → REVISE"

## Adaptation Aratea : checklist 8 critères pour la promotion d'un challenger

| # | Critère tradermonty | Adaptation Kalshi binaire / Aratea |
|---|---|---|
| C1 | Edge plausibility (thesis quality) | Hypothèse météorologique défendable (forçage anticyclone, advection froide, etc.) — pas du pattern matching aveugle |
| C2 | Overfitting (filter count) | Nombre de features / régularisation L2 ; vérifier que les 11 features de `learned_v2` ne sont pas du data-snooping post-hoc |
| C3 | Sample adequacy | N≥30 paris settled (= "absolute minimum" backtest-expert), N≥50 = promotion |
| C4 | Regime dependency | Performance par régime saisonnier (printemps/été/automne/hiver) et par ville (NYC vs autres) |
| C5 | Exit calibration | **N/A sur payoff binaire** : pas de stop-loss intra-position, on tient jusqu'à settlement |
| C6 | Risk concentration | **Cap par event + portfolio heat** (voir RFC associé) |
| C7 | Execution realism | Liquidité du contrat Kalshi (bid/ask spread, volume), pas d'illusion de fills |
| C8 | Invalidation | Signaux explicites de dégradation : BSS challenger < champion sur 5 jours consécutifs, OOS < 50 % IS |

## Logique de gate proposée pour Aratea

Inspirée du verdict logic ci-dessus, transposée :

```
SI BSS_challenger > BSS_champion + epsilon
  ET N_settled >= 50
  ET aucun finding "fail" sur C1/C2 :
    PROMOTE
SI BSS_challenger > BSS_champion mais N < 50 :
    REVISE (continuer à tester)
SI BSS_challenger < BSS_baseline (kalshi_mid) ou < BSS_climato :
    REJECT
```

## Verdict réutilisation

**Gabarit utile, contenu à réécrire.** Le squelette "8 critères + verdict
4-états + confidence" est un format de review propre. Mais :

- C5 (Exit Calibration) est inutile sur Kalshi binaire — pas de stop-loss
- C7 (Volume filter) à reformuler : liquidité, pas volume action
- C2 (Overfitting) particulièrement pertinent : 11 features sur 14 jours de
  live, c'est mince — le risque d'over-fitting est réel et doit être tracké
  explicitement à chaque promotion

Si un jour Aratea formalise une procédure "promote challenger → champion",
ce gabarit est le bon point de départ.
