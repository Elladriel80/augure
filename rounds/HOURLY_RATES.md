# HOURLY_RATES — Augure rate sheet (BTC)

> [Lire en français](HOURLY_RATES.fr.md)

*Version 0.1 — modifiable by PR + ratification.*

## Principle

A single standard for the entire project. No individual salary, no negotiation, no geographic differentiation. The rates below are the **only** ones used by the valuation agent.

The unit of account is **BTC**. Rates are denominated in **sats per hour** (1 BTC = 100,000,000 sats). Rates are deliberately modest relative to market rates: the upside promise is in the tokens, not the rate.

Reference: average Paris freelance daily rate (TJM) divided by 7 working hours, then converted to BTC at the calibration date.

## Table

| Profile | sats / hour | sats / day (×7) | mBTC / hour |
|---|---|---|---|
| Senior dev / smart contracts | 130,000 | 910,000 | 1.30 |
| Mid-level dev | 80,000 | 560,000 | 0.80 |
| Junior / apprentice | 40,000 | 280,000 | 0.40 |
| ML engineer / data scientist | 140,000 | 980,000 | 1.40 |
| Senior researcher / quant | 160,000 | 1,120,000 | 1.60 |
| Product designer / UX | 90,000 | 630,000 | 0.90 |
| Tech writer / documentation | 70,000 | 490,000 | 0.70 |
| Community / ops / coordination | 60,000 | 420,000 | 0.60 |
| Smart contract security audit | 220,000 | 1,540,000 | 2.20 |

Calibration date: 2026-05. Reference BTC/EUR ≈ 95,000 € (anchor only — does not enter calculations).

## Profile selection

The agent picks the profile from the **nature of the output**, not from who produced it. A junior delivering senior-grade code is rated at the senior rate for that PR. Conversely, a senior producing trivial output gets rated at the matching profile.

If multiple profiles apply, decompose by hours per nature and sum.

## Junior delivering senior output

The system values the **artifact**, not the effort. A junior who ships senior-level work earns the senior rate. Consistent with labor-value theory: what matters is what was produced, not the trouble it took.

Inverse: a senior producing slow because distracted is bounded by the **hours actually needed** at the matching profile. No premium for wasted time.

## Recalibration

Rates are reviewed:
- **Quarterly** by benchmarking against Paris freelance TJMs (sources: Malt, Comet, Crème de la Crème aggregated). Conversion at trimester average BTC/EUR spot.
- **On trigger** if BTC drifts > 25 % vs reference price within a quarter.

Any change follows the versioning process of `RUBRIC.md`.

## Currency

Internal accounting and mint are exclusively in BTC. EUR/USD references in this document are anchors for periodic recalibration, never used in the valuation chain.

## Limitations

- The grid remains arbitrary at a fundamental level — no single "true" rate exists. Mitigation: transparent methodology, regular recalibration, holder vote for significant changes.
- Profiles do not cover every imaginable contribution. For unlisted cases, the agent proposes a profile and rate by analogy to the existing grid, with explicit justification, and the decision is ratified like any other valuation.
- BTC volatility means contributors are exposed to BTC/fiat fluctuations. This is intentional: the project is BTC-aligned. Holder votes can recalibrate if drift becomes material.
