> [Lire en français](README.fr.md)

# Aratea

**Open-source weather prediction markets and decentralized parametric mutual coverage.**

Aratea is in early-stage development. Its first phase validates a predictive edge on Kalshi weather markets before building the DAO infrastructure for a mutualization-pool-backed parametric mutual.

> **Important note** — Aratea is not insurance in the meaning of the French Code des assurances or of Solvency II. It is a **decentralized discretionary mutual**: members pool capital, and indemnification follows automatic parametric execution backed by oracles, governed by token holders. See white paper, section 4.
>
> ---

> **Contributors welcome.** Aratea pays contributors in tokens, valued in BTC via a public rubric, fact-only from Git.
> - **5 good-first-issues open right now** → [`docs/contributor-starter-issues.md`](docs/contributor-starter-issues.md)
> - **How payment works** → [`docs/value_engine.md`](docs/value_engine.md)
> - **Current status** → [`STATUS.md`](STATUS.md)

---

## Repository structure

This is a monorepo organized in four top-level concerns:

```
aratea/
├── predictor/      ← prediction code (Phase 1: Kalshi POC)
├── contracts/      ← smart contracts (Phase 2+: token, governance, mutual)
├── rounds/         ← token issuance mechanics (live: AUG-POC labor-value mint)
└── docs/           ← project-wide documents (token model, architecture)
```

### `predictor/`
The prediction engine. Currently the Kalshi POC: meta-ensemble IA combining ECMWF, GraphCast, GFS, JMA forecasts; NWS resolution rules; microstructure analysis; backtest infrastructure.

### `contracts/`
Solidity smart contracts. **Phase 1 in progress** (May 2026): on-chain settlement layer for the labor-value mint mechanism — `AugPocToken` (ERC-20 + AccessControl + Pausable) and `RoundRegistry` (propose / challenge / execute / cancel lifecycle). No on-chain emission cap is enforced; quality is gated off-chain by the valuation rubric, the token-weighted vote above 0.01 BTC, the new-entrant cooldown, slashing, and the annual audit (white paper §7.7). Foundry, Solidity 0.8.24, OpenZeppelin v5, Arbitrum Sepolia testnet target. See [`contracts/README.md`](contracts/README.md) for status and milestones.

### `rounds/`
The live mechanics for issuing AUG-POC tokens to anyone bringing labor value to the project (code, research, data, design, capital). Contains the public rubric, hourly rate sheet, valuation agent prompt, automation scripts, and historical valuation reports.

### `docs/`
Cross-cutting documentation: token economic model, valuation engine spec, project architecture.

## Phases

1. **POC Kalshi** *(in progress)* — validate predictive edge. Go/no-go criterion: meta-ensemble IA beats best single model and beats climatology on N>50 events.
2. **DAO Aratea** — tokenized mutualization pool (Nexus Mutual style), parametric contract issuance via AMM/orderbook, pricing via the prediction engine.
3. **DePIN data layer** — physical weather stations rewarded in token (WeatherXM partnership or proprietary network).

## Token model in one sentence

A single token (AUG-POC, then ARA post-DAO). One unified mechanism: every contribution — cash or labor — is valued in BTC-equivalent and minted at NAV. No pre-allocated buckets, no founder bonus, no privileged categories. The cap table emerges organically from accumulated valuations. Read [`docs/token_model.md`](docs/token_model.md) for detail.

## How to participate

## How to participate

Start here:

1. **Pick a starter issue** → [`docs/contributor-starter-issues.md`](docs/contributor-starter-issues.md) (5 open, each scoped to one module, no credentials needed)
2. **Understand how you're paid** → [`docs/value_engine.md`](docs/value_engine.md) (fact-only Git, BTC valuation, public rubric)
3. **Register your wallet** when ready for the next monthly round → [`rounds/WALLETS.md`](rounds/WALLETS.md)
4. **Full process** → [`CONTRIBUTING.md`](CONTRIBUTING.md)

DMs open on X: [@jsl_augure](https://x.com/jsl_augure) (handle migrating to @jsl_aratea).

## License

[Apache 2.0](LICENSE).
