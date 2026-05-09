# Announcement Templates — Manual Backup

These are ready-to-paste English templates for Discord and X, in the **builder-log / dev-in-public** voice we've chosen for Augure.

Use them when:
- The CI workflow fails (network, API, secrets) and you need to post anyway.
- You want to announce something that isn't a Git tag (a milestone, a research finding, a roadmap shift).
- You want to tweak the auto-generated copy before posting.

**Voice rules** (kept in sync with `feedback_no_assurance_terminology.md`):
- Say "decentralized mutual" or "parametric coverage", **never** "insurance".
- Augure is presented as an autonomous project. Do not reference any prior brand.
- Honest, technical-but-readable. No hype. No emojis-as-decoration.
- One emoji max per X post if it adds signal (e.g. ⚙️ for infra, 📈 for results).

---

## 1. Tagged release — `vX.Y.Z`

### Discord

```
### `Augure` — release v0.1.0 shipped

**What's in:**

__New__
• Kalshi market fetcher with backoff and pagination
• Climatology baseline predictor (CONUS stations, daily granularity)
• Forecast-blend predictor combining ECMWF + GFS

__Improved__
• Kelly sizing now caps per-market exposure at 2% of bankroll
• Ledger writes are atomic across crash points

__Docs__
• ARCHITECTURE.md updated for the predictor module

[release notes](<https://github.com/augure/augure/releases/tag/v0.1.0>) · [diff](<https://github.com/augure/augure/compare/v0.0.5...v0.1.0>)

_Decentralized prediction markets for weather risk._
```

### X (≤280 chars)

```
Augure v0.1.0 — Kalshi fetcher + climatology baseline + ECMWF/GFS blend predictor are live. Backtest on April markets next.
https://github.com/augure/augure/releases/tag/v0.1.0
```

---

## 2. Pre-release / alpha — `vX.Y.Z-alpha`

### Discord

```
### `Augure` — pre-release v0.1.0-alpha shipped

Alpha cut — APIs may still change before v0.1.0. Calling for testers who want to point a wallet at a testnet round.

__What works__
• Round lifecycle: open → commit → reveal → settle
• Predictor outputs JSON conformant to the round oracle schema

__Known limits__
• Settlement uses a placeholder oracle — real Kalshi resolver lands in alpha-2
• No slashing yet for predictor disputes

[release notes](<https://github.com/augure/augure/releases/tag/v0.1.0-alpha>)

_Decentralized prediction markets for weather risk._
```

### X

```
Augure v0.1.0-alpha is out. Round lifecycle works end-to-end on testnet. Looking for a few testers to spar with the predictor disputes flow before stable.
https://github.com/augure/augure/releases/tag/v0.1.0-alpha
```

---

## 3. Phase 1 POC milestone (Kalshi edge proven)

### Discord

```
### `Augure` — Phase 1 milestone

We ran the predictor against 30 days of live Kalshi weather markets without staking real capital. Results:

__Outcome__
• 142 markets covered, 89 trades sized
• Predicted edge held over the window — paper P&L positive after fees
• Calibration: predicted probabilities tracked outcomes within ±3pp on the 0.3–0.7 band

__What this means__
The predictor is good enough to be the price-taker for a small live pool. Phase 2 starts: real capital, capped, on a single station cluster.

Full numbers and raw ledger in the repo: [POC report](<https://github.com/augure/augure/blob/main/augure/predictor/reports/2026-05-poc.md>)

_Decentralized prediction markets for weather risk._
```

### X

```
Augure Phase 1 result: 30-day paper run against live Kalshi weather markets. 89 trades sized, edge held after fees, calibration within ±3pp. Moving to live capital, capped, single station cluster.
```

---

## 4. Single-feature ship (mid-cycle)

### Discord

```
### `Augure` — shipped: parametric round settlement

Round outcomes now resolve from an on-chain oracle commitment fed by the predictor. Replaces the manual settle path used in tests.

__Why it matters__
This is the bridge between "the model says X" and "the contract pays Y". Without it, parametric coverage is just a chart.

__Next__
• Wire Kalshi resolution prices into the oracle commitment
• Add dispute window (48h) before payout finalization

PR: <https://github.com/augure/augure/pull/42>

_Decentralized prediction markets for weather risk._
```

### X

```
Just shipped on-chain settlement for Augure rounds. Predictor commits, oracle reads, contract pays — no human in the path. Dispute window lands next.
https://github.com/augure/augure/pull/42
```

---

## 5. Honest correction / rollback

Use this when something broke and you want to be transparent. This builds more trust than silence.

### Discord

```
### `Augure` — rolling back v0.2.1

We caught a bug in the Kelly sizing path that under-sized trades by ~30% on markets with bid/ask spreads above 5c. No real funds were at risk (still on testnet) but the backtest numbers from the v0.2.1 announcement are wrong.

__What we're doing__
• Reverted main to v0.2.0
• Re-running the April backtest with the fix on a branch
• Will republish corrected numbers before tagging v0.2.2

Sorry for the noise. The fix and the corrected report will land within 48h.

_Decentralized prediction markets for weather risk._
```

### X

```
Heads up: rolled back Augure v0.2.1. Found a Kelly-sizing bug that distorted the backtest numbers I posted yesterday. No funds at risk (testnet only). Re-running with the fix, corrected report by Sunday.
```

---

## 6. Weekly builder log (no specific tag)

### Discord

```
### `Augure` — week of May 5–9, 2026

What got done:

__Predictor__
• ECMWF ingestion path stabilized (was failing on partial parquet files)
• Added the dispute-stub so contracts can read predictor commitments

__Contracts__
• Round lifecycle tests pass against forge fuzzer
• Gas trimmed ~12% on settlement after struct packing

__Discord & docs__
• Server structure refactor in progress (70% done)
• CONTRIBUTING.md updated for the predictor sub-package

What's next: finish the Discord, run the Phase 1 paper backtest end-to-end.

_Decentralized prediction markets for weather risk._
```

### X

```
Augure week recap: predictor stabilized on ECMWF ingestion, contracts -12% gas on settle, contributor docs updated. Phase 1 paper backtest coming next week.
```

---

## Tone reminders

- Lead with **what shipped** or **what we learned** — not with how hard it was.
- If numbers exist, cite them with units. "+3pp", "30 days", "142 markets" — not "lots".
- If something broke, say it broke. The crypto-builder audience trusts transparency more than polish.
- Don't link to the same URL on Discord and X in the same hour — the X-Discord cross-poster bots will deduplicate and your Discord ping looks like spam.
