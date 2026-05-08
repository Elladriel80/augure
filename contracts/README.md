> [Lire en français](README.fr.md)

# contracts

Solidity smart contracts for the Augure protocol. **Empty for now** — the directory holds the architectural roadmap until the predictor's POC validates the case for proceeding to on-chain components.

## Status

Phase 2+ — *not started*.

Phase 1 (POC Kalshi) runs entirely off-chain. Smart contracts begin only after the POC's go/no-go criterion is met (meta-ensemble beats best single model and climatology on N>50 events). Until then this directory exists to signal intent and let contributors propose specs.

## Planned modules

```
contracts/
├── token/          ← ERC-20 AUG-POC and AUG, with mint/burn guards
├── rounds/         ← multisig-ratified mint module (subscription + redemption)
├── governance/     ← Top-X holder panel, voting, slashing
└── mutual/         ← (Phase 3) parametric weather contracts + oracles
```

### `token/`
ERC-20 with 8 decimals (BTC-aligned). Two phases:
- **AUG-POC** : POC-phase token, mintable only via the `rounds/` module after multisig ratification. Includes redemption window logic and slashing hooks.
- **AUG** : DAO-phase token. Conversion mechanism from AUG-POC at a ratio voted by holders (≥ 67 % threshold) at DAO launch.

### `rounds/`
Multisig-ratified mint module. Receives ratified valuation reports from the off-chain agent + ratifier (or post-DAO from the holder panel vote on-chain). Mints tokens at current NAV to the wallets specified in the report. Enforces hard caps (10 % monthly, 30 % per contributor).

### `governance/`
Phase 1: simple multisig (founder + 2 advisors).
Phase 2: on-chain panel composed of the Top-X token holders with one vote each (not stake-weighted). Used for ratifying contested valuation rounds.
Phase 3: full DAO with token-weighted votes for parametric changes (rubric, rates, fees), with quorum and threshold rules.

### `mutual/`
Phase 3+. Parametric weather mutual contracts. Members deposit collateral into the mutualization pool; buyers purchase event-triggered payouts. Pricing computed off-chain by the predictor, oracle resolution via Chainlink Custom on top of NOAA/NWS feeds.

> Augure does **not** operate as a regulated insurer. See white paper, section 4.

## Toolchain

**Foundry** *(planned)*. Justification: faster compile + test cycle, integrated fuzzing, modern Solidity tooling, audited and forked widely. Hardhat could be added later if a specific deployment workflow needs it.

Solidity version: ≥ 0.8.20.
Target chain: TBD (candidates: Base, Arbitrum, Optimism). Decision criteria: gas cost, EVM compatibility, ecosystem of risk-pool / DeFi contributors, custody options for the bankroll.

## Specs to write before any code

- AUG-POC token spec (mint guard, slashing surface, transferability lock)
- Round mint module spec (ratification proof format, multisig signatures)
- Subscription pending address spec (refund flow on round refusal)
- Redemption queue spec (window, gate, lockup, NAV oracle)

Contributions welcome on the spec PRs (see [`/CONTRIBUTING.md`](../CONTRIBUTING.md)).
