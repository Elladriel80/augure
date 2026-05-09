> [Lire en français](README.fr.md)

# Augure

**Open-source weather prediction markets and decentralized parametric mutual coverage.**

Augure is in early-stage development. Its first phase validates a predictive edge on Kalshi weather markets before building the DAO infrastructure for a mutualization-pool-backed parametric mutual.

> **Important note** — Augure is not insurance in the meaning of the French Code des assurances or of Solvency II. It is a **decentralized discretionary mutual**: members pool capital, and indemnification follows automatic parametric execution backed by oracles, governed by token holders. See white paper, section 4.

## Repository structure

This is a monorepo organized in four top-level concerns:

```
augure/
├── predictor/      ← prediction code (Phase 1: Kalshi POC)
├── contracts/      ← smart contracts (Phase 2+: token, governance, mutual)
├── rounds/         ← token issuance mechanics (live: AUG-POC labor-value mint)
└── docs/           ← project-wide documents (token model, architecture)
```

### `predictor/`
The prediction engine. Currently the Kalshi POC: meta-ensemble IA combining ECMWF, GraphCast, GFS, JMA forecasts; NWS resolution rules; microstructure analysis; backtest infrastructure.

### `contracts/`
Solidity smart contracts. **Phase 1 in progress** (May 2026): on-chain settlement layer for the labor-value mint mechanism — `AugPocToken` (ERC-20 + AccessControl + Pausable), `RoundRegistry` (propose / challenge / execute / cancel lifecycle), `MonthlyMintCap` (10 % monthly cap library). Foundry, Solidity 0.8.24, OpenZeppelin v5, Arbitrum Sepolia testnet target. See [`contracts/README.md`](contracts/README.md) for status and milestones.

### `rounds/`
The live mechanics for issuing AUG-POC tokens to anyone bringing labor value to the project (code, research, data, design, capital). Contains the public rubric, hourly rate sheet, valuation agent prompt, automation scripts, and historical valuation reports.

### `docs/`
Cross-cutting documentation: token economic model, valuation engine spec, project architecture.

## Phases

1. **POC Kalshi** *(in progress)* — validate predictive edge. Go/no-go criterion: meta-ensemble IA beats best single model and beats climatology on N>50 events.
2. **DAO Augure** — tokenized mutualization pool (Nexus Mutual style), parametric contract issuance via AMM/orderbook, pricing via the prediction engine.
3. **DePIN data layer** — physical weather stations rewarded in token (WeatherXM partnership or proprietary network).

## Token model in one sentence

A single token (AUG-POC, then AUG post-DAO). One unified mechanism: every contribution — cash or labor — is valued in BTC-equivalent and minted at NAV. No pre-allocated buckets, no founder bonus, no privileged categories. The cap table emerges organically from accumulated valuations. Read [`docs/token_model.md`](docs/token_model.md) for detail.

## How to participate

See [`CONTRIBUTING.md`](CONTRIBUTING.md). In short: register your wallet, ship Git-observable artifacts (code, data, RFCs) on the relevant module, get evaluated monthly by the rubric, receive AUG-POC tokens.

## License

[Apache 2.0](LICENSE).
