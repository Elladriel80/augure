# RUBRIC — valuation rules

> [Lire en français](RUBRIC.fr.md)

*Version 0.2 — fact-only, BTC. All changes go through PR + 7-day public discussion + ratification.*

## 1. Single question

For every observable artifact, the agent answers **one question only**:

> How much would the market have paid a professional to produce this exact output, at this exact quality?

The answer is in **BTC** (or sats). No EUR/USD anywhere in the calculation chain.

## 2. Hard constraints

- **Fact-only.** Inputs are limited to: merged PRs, their diffs, files, descriptions, reviews, commit messages, signed commits on `main`. No self-declared hours, no submissions, no narrative claims.
- **Push KO = 0.** Closed-without-merge / rejected / abandoned PRs have zero value.
- **No bonus.** No "founder", "loyalty", or "early-mover" multipliers exist.
- **Hard caps.** Quality ∈ [0.5 ; 1.3], Impact ∈ [0.8 ; 1.5]. The agent never breaches these bounds.

## 3. Calculation

```
value_BTC = estimated_hours × hourly_rate_BTC × quality_adjustment × impact_adjustment
```

- **estimated_hours** : time a competent professional in the right profile would need to produce the same output, starting from a familiar-with-stack but not-with-repo state. Inferred from the diff and surrounding context.
- **hourly_rate_BTC** : from `HOURLY_RATES.md`, picked by output profile (not by who wrote it).
- **quality_adjustment** : ∈ [0.5 ; 1.3], hard-bounded.
- **impact_adjustment** : ∈ [0.8 ; 1.5], hard-bounded.
- Floor: 0.4 ; ceiling: 1.95 on combined adjustments.

## 4. Estimating hours

In order:

1. **Diff** — added/removed lines, files touched, apparent complexity (if/loops/branching density).
2. **Context** — core vs peripheral module, refactor vs greenfield, integrations affected.
3. **Associated artifacts** — added tests, updated docs, referenced issues, RFCs.

Heuristics (calibration baseline):
- 100 clean tested lines on an isolated module ≈ 4-8 hours.
- Architectural refactor touching 5+ files ≈ 2-4 days.
- RFC / spec doc 2-3 pages ≈ 4-8 hours.
- Targeted bug fix with regression test ≈ 1-3 hours.
- Analysis notebook / benchmark ≈ 1-2 days.

If a contribution mixes natures, **decompose** and sum.

## 5. Output profile selection (rate determination)

The profile is picked from the **nature of the output**, not from who wrote it. A junior who delivers senior-level code on a smart contract is rated at the senior-SC rate for that PR.

If multiple profiles apply within one PR, the agent decomposes by hours per nature:
```
example: PR mixes 3h ML logic + 2h documentation
value_pre_adjust = 3 × ML_rate + 2 × techwriter_rate
```

## 6. Quality adjustment — ×0.5 to ×1.3

| Signal | Effect |
|---|---|
| Tests added and meaningful | +0.10 |
| Documentation updated (docstrings, README, ADR) | +0.05 |
| Clean code, follows conventions | +0.05 |
| CI green on first run | +0.05 |
| Multiple reviewers approving without major change request | +0.05 |
| Introduces tech debt (TODO without ticket, undocumented hack) | -0.10 |
| Ships a regression (later identified and traced back) | -0.20 |
| Incomplete work / immediate rework needed | -0.30 |

Start from 1.0, apply changes, hard-clamp to [0.5 ; 1.3].

## 7. Impact adjustment — ×0.8 to ×1.5

| Level | Criterion | Coefficient |
|---|---|---|
| Blocking | Unblocks a major roadmap step or solves a critical risk | 1.4 - 1.5 |
| High | Measurably improves a key metric (P&L, predictive quality, robustness) | 1.2 - 1.3 |
| Standard | Normal progress on a planned task | 1.0 |
| Modest | Peripheral work, polish, nice-to-have | 0.9 |
| Low | Likely to be discarded or duplicated | 0.8 |

The agent justifies each level with explicit reference to roadmap or measured outcome.

## 8. Non-code artifacts (still fact-based)

### Datasets committed to the repo
- Public dataset under permissive license: **value = 0** (curation hours valued at relevant profile rate if visible in commit history).
- Proprietary dataset purchased: value = documented acquisition cost converted to BTC, capped at market price.
- Built dataset (scraping, labeling, sensor capture): hours implied by the code that produced it × matching profile.

### RFCs, specs, design docs (committed as Markdown)
- Hours × researcher or designer profile.
- Impact adjustment based on adoption (RFC adopted as-is: ×1.3 ; modified majorly: ×1.0 ; rejected: ×0.8).

### Community digest documents (only if committed)
- A monthly community digest committed as `community/digest-YYYY-MM.md`, signed by the contributor's wallet, can be valued as community work.
- Hours × community profile.
- No value if not committed. The Discord history alone does not count.

### Disclosed bugs (responsible disclosure)
- Critical (fund loss, key leak): 0.05 - 0.20 BTC
- High (DoS, state corruption): 0.015 - 0.05 BTC
- Medium (non-blocking inconsistency): 0.003 - 0.015 BTC
- Minor (typo, edge case): 0.0005 - 0.003 BTC

Inspired by Immunefi tiers, recalibrated after first cases.

## 9. Cash deposits

Out of valuation rubric (1 sat = 1 sat, no estimation needed) but **subject to ratification like any other contribution**.

- BTC deposit: sent to the round's `subscription-pending` multisig address. If accepted at day +7, mint at NAV. If refused by ratifier(s) with written rationale, funds are returned to the sender.
- USDC / EURC deposit: converted to sats at subscription-day spot, same pending + ratification mechanic.

Cash apports appear in the monthly agent report **without valuation** (gross amount + sender address) for ratifier visibility. Refusal is possible for strategic, reputational, conflict-of-interest or compliance reasons. Symmetry with code: a labor contribution is "refused" by not merging its PR; a cash contribution is refused by returning its funds.

## 10. Retroactive valuation (genesis)

Once, at project opening:
1. The agent scans the entire Git history of the main repo.
2. Decomposes the history into logical phases (visible in branch/tag/CHANGELOG structure).
3. Applies the standard method per phase.
4. **Challenge window extended to 30 days** (vs 7 standard).
5. First-round prospect investors are explicitly invited to challenge before they invest.
6. No "founder" bonus. The fairness of the model depends on the absence of categorical privilege.

## 11. Tie-breaker rule

> When the agent hesitates between two estimates, it picks the lower one. If a contributor believes they were under-valued, they file a formal challenge with arguments.

## 12. Versioning

This rubric is versioned in Git. Every change requires:
1. PR opened with rationale.
2. Minimum 7 days of public discussion.
3. Ratification (phase 1: JS ; phase 2: committee ; phase 3: 51 % vote).
4. The new version applies to the next round following merge, never retroactively.

## 13. Known limitations

- Off-Git invisible work (synchronous mentoring, DM debugging, hallway calls) is not captured. **By design.** The trade-off is objectivity over inclusivity. To be valued, work must produce a Git-visible artifact.
- The agent may systematically misestimate certain categories. Annual audit comparing AI valuations to live freelance market rates. Recalibration if drift > 20 %.
- Quality and impact adjustments rest on the agent's reading. The Top-X holder panel is the safety net.
