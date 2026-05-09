> [Lire en français](README.fr.md)

# contracts

Solidity smart contracts for the Augure protocol. **Phase 1 in progress** — building the on-chain settlement layer for the labor-value mint mechanism described in [`/docs/token_model.md`](../docs/token_model.md).

## Status

Phase 1 — *active*. Milestones M0 through M5. See [`/docs/architecture.md`](../docs/architecture.md) for project-level phasing.

## Phase 1 scope

The on-chain primitives that ratify and execute the monthly mint rounds already produced off-chain (see [`/rounds/`](../rounds/)):

1. **`AugPocToken`** — ERC-20 with `ERC20Permit`, `AccessControl`, and `Pausable`. 18 decimals (Ethereum standard). No fixed cap — issuance is regulated by `RoundRegistry` enforcing the 10 % monthly cap. Four roles: `DEFAULT_ADMIN_ROLE`, `MINTER_ROLE` (RoundRegistry), `PAUSER_ROLE` (Safe), `BURNER_ROLE` (reserved for the future `AugConverter` that will execute the `AUG-POC → AUG` conversion at the Phase 2 DAO launch — see white paper §7.2). Pause blocks user-to-user transfers only; mint and burn remain operational.
2. **`RoundRegistry`** — propose / challenge / execute / cancel lifecycle for monthly mint rounds. Each round is anchored to its IPFS hash (the `valuation_report.md` snapshot from `/rounds/archives/<round-id>/`).
3. **`MonthlyMintCap`** — pure library computing the 10 % monthly cap from circulating supply at the start of each calendar month (UTC).

Out of scope in Phase 1 (scaffolded, not implemented): on-chain `AUG` governance token + `Governor`, automated NAV oracle, parametric mutual contracts, on-chain Top-X holder voting.

## Layout

```
contracts/
├── src/
│   ├── token/                      # M1 — AugPocToken
│   ├── rounds/                     # M2 (MonthlyMintCap) + M3 (RoundRegistry)
│   └── interfaces/                 # IAugPocToken, IRoundRegistry
├── test/
│   ├── unit/                       # ≥ 95% line coverage on business logic
│   ├── fuzz/                       # 10 000 runs default
│   └── invariant/                  # supply / cap / role invariants
├── script/                         # M4 — deployment + Safe calldata generators
├── docs/                           # bilingual FR/EN — architecture, security, deployment, lifecycle
├── foundry.toml
├── slither.config.json
├── remappings.txt
├── .env.example                    # placeholders for Arbitrum Sepolia
└── README.md / README.fr.md
```

## Toolchain

- **Foundry** (forge, cast, anvil) — pinned to stable releases via CI.
- **Solidity 0.8.24**, EVM `paris`, optimizer 200 runs.
- **OpenZeppelin Contracts v5.1.0** for every primitive (ERC20, AccessControl, Pausable, ReentrancyGuard, SafeERC20, ERC20Permit). No hand-rolled re-implementation.
- **`forge-std` v1.9.4** for tests and scripts.
- **Slither 0.10.4** for static analysis (CI fails on `medium`).
- **CI** at `.github/workflows/contracts-ci.yml` — runs on every push / PR touching `contracts/**`.

## Target chain

Arbitrum Sepolia (testnet) in Phase 1. Mainnet deployment is **blocked** until at least one community audit (Code4rena Arena-X, Sherlock Watson, or documented peer review) is complete.

## Build & test

> Foundry must be installed locally. See [getfoundry.sh](https://book.getfoundry.sh/getting-started/installation).

```bash
# from contracts/
forge install --no-commit foundry-rs/forge-std@v1.9.4 OpenZeppelin/openzeppelin-contracts@v5.1.0
forge build
forge test -vvv
forge coverage --report summary
```

CI runs the same commands on every PR — local install is only needed for development.

## Security model (short version)

- All privileged roles (`MINTER_ROLE`, `PAUSER_ROLE`, `ROUND_PROPOSER_ROLE`, `ROUND_EXECUTOR_ROLE`) are held by a Safe multisig on Arbitrum Sepolia. **Never an EOA.**
- No upgradeability initially. Bug fixes ship as new deployments + migration.
- Strict Checks-Effects-Interactions, `ReentrancyGuard` on every external transfer surface, `SafeERC20` for all ERC20 interactions.
- Required tests at three levels: unit (≥ 95 % coverage), fuzz (10 000 runs), invariants on critical properties (supply ≤ monthly cap; no mint without expired challenge window; `MINTER_ROLE` held only by the Safe).

Full threat model in [`docs/SECURITY.md`](docs/SECURITY.md).

## Lifecycle of a round (Phase 1)

```
   ┌────────────────────┐
   │  Off-chain agent   │  ───►  /rounds/archives/<round-id>/valuation_report.md
   │  produces report   │
   └─────────┬──────────┘
             │ founder ratifies + pins to IPFS
             ▼
   ┌────────────────────┐
   │ Safe.proposeRound  │  ───►  RoundRegistry.proposeRound()
   │  (calldata)        │        emits RoundProposed event
   └─────────┬──────────┘
             │
             ▼
   ┌────────────────────┐         ┌─────────────────────┐
   │ Challenge window   │  ───►   │  challengeRound()    │  (anyone)
   │ (7 d / 30 d genesis)│         │  → status Challenged │
   └─────────┬──────────┘         └─────────┬───────────┘
             │ window expires + status == Proposed
             ▼                               │ Safe reviews off-chain panel vote
   ┌────────────────────┐                    ▼
   │ Safe.executeRound  │              ┌─────────────────────┐
   │  → mint to bens    │              │ Safe.cancelRound() │
   │  → check 10% cap   │              └─────────────────────┘
   └────────────────────┘
```

Detail in [`docs/ROUND-LIFECYCLE.md`](docs/ROUND-LIFECYCLE.md).

## Roadmap (milestones)

| Milestone | Scope | Status |
|---|---|---|
| **M0** | Foundry scaffold, CI, threat model, bilingual doc | ✅ done |
| **M1** | `AugPocToken` (ERC20 + Permit + AccessControl + Pausable + 4 roles) | ✅ done |
| **M2** | `MonthlyMintCap` library + exhaustive fuzzing | ✅ done |
| **M3** | `RoundRegistry` (propose / challenge / execute / cancel) | ✅ done |
| **M4** | Deployment scripts on Arbitrum Sepolia + Safe integration | pending |
| **M5** | Read-only dashboard (Next.js + viem) | pending |

## License

Apache 2.0 — see [/LICENSE](../LICENSE).
