> [Lire en français](README.fr.md)

# Augure

**Open-source decentralized weather prediction markets and parametric insurance.**

Augure is in early-stage development. Its first phase validates a predictive edge on Kalshi weather markets before building the DAO infrastructure for risk-pool based parametric insurance.

## Repository structure

This is a monorepo organized in four top-level concerns:

```
augure/
├── predictor/      ← prediction code (Phase 1: Kalshi POC)
├── contracts/      ← smart contracts (Phase 2+: token, governance, insurance)
├── rounds/         ← token issuance mechanics (live: AUG-POC labor-value mint)
└── docs/           ← project-wide documents (token model, architecture)
```

### `predictor/`
The prediction engine. Currently the Kalshi POC: meta-ensemble IA combining ECMWF, GraphCast, GFS, JMA forecasts; NWS resolution rules; microstructure analysis; backtest infrastructure.

### `contracts/`
Solidity smart contracts. Currently a roadmap (no live contracts yet). Will host the AUG-POC ERC-20 token, the rounds-mint module, panel governance, and (Phase 3+) parametric insurance contracts and weather oracles.

### `rounds/`
The live mechanics for issuing AUG-POC tokens to anyone bringing labor value to the project (code, research, data, design, capital). Contains the public rubric, hourly rate sheet, valuation agent prompt, automation scripts, and historical valuation reports.

### `docs/`
Cross-cutting documentation: token economic model, valuation engine spec, project architecture.

## Phases

1. **POC Kalshi** *(in progress)* — validate predictive edge. Go/no-go criterion: meta-ensemble IA beats best single model and beats climatology on N>50 events.
2. **DAO Augure** — tokenized risk pool (Nexus Mutual style), contract issuance via AMM/orderbook, pricing via the prediction engine.
3. **DePIN data layer** — physical weather stations rewarded in token (WeatherXM partnership or proprietary network).

## Token model in one sentence

A single token (AUG-POC, then AUG post-DAO). One unified mechanism: every contribution — cash or labor — is valued in BTC-equivalent and minted at NAV. No pre-allocated buckets, no founder bonus, no privileged categories. The cap table emerges organically from accumulated valuations. Read [`docs/token_model.md`](docs/token_model.md) for detail.

## How to participate

See [`CONTRIBUTING.md`](CONTRIBUTING.md). In short: register your wallet, ship Git-observable artifacts (code, data, RFCs) on the relevant module, get evaluated monthly by the rubric, receive AUG-POC tokens.

## License

[Apache 2.0](LICENSE).
