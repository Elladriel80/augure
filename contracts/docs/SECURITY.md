> [Lire en français](SECURITY.fr.md)

# Security & threat model — Augure contracts (Phase 1)

*Version 0.1 — 2026-05-09*

## 1. Scope

This document covers the on-chain attack surface of the Phase 1 contracts (`AugPocToken`, `RoundRegistry`, `MonthlyMintCap`) deployed on Arbitrum Sepolia.

It does **not** cover: off-chain agent integrity, IPFS pinning durability, Safe signer key management practices, or the social-layer challenge process. Those have their own threat models and live outside the contract code.

## 2. Assets to protect

| Asset | Why it matters |
|---|---|
| `AugPocToken.totalSupply` integrity | Inflation beyond the 10 % monthly cap dilutes every existing holder. |
| `RoundRegistry` round records | Falsified history breaks accountability and the audit trail. |
| `MINTER_ROLE` (and other privileged roles) | Direct mint authority. Compromise = unbounded inflation. |
| Beneficiary mint allocations | A round is supposed to mint to the wallets ratified off-chain — not to attacker-controlled addresses. |

## 3. Trust assumptions (in scope)

- The Safe multisig signers behave honestly (or, at minimum, the threshold of signers cannot collude maliciously).
- The Solidity compiler and OpenZeppelin v5.1.0 are not backdoored.
- Arbitrum Sepolia (and the Arbitrum Nitro stack) does not censor or replay transactions adversarially.
- Block timestamps drift by less than the monthly window granularity (a few minutes is irrelevant to a 1-month boundary).

## 4. Out-of-scope (acknowledged but not defended on-chain)

- **Compromise of an individual signer's key** outside the Safe threshold. Mitigation lives in Safe configuration (M-of-N + hardware wallets), not in the contract code.
- **MEV on `executeRound`**. Front-running an execution would not let an attacker change the beneficiaries (the round was committed at `proposeRound`). Worst case: someone pays the gas before the Safe — harmless.
- **Off-chain agent producing a fraudulent valuation report.** Caught by the founder's review and the public challenge window. Not the contract's job to detect fraud in the input.
- **IPFS pin loss.** The contract stores the URI; if the file is ever lost, the round is still on-chain (hash + amounts + beneficiaries) but the human-readable rationale would have to be re-published. Pinata + redundant pins.

## 5. Attack surface and mitigations

### 5.1 Privileged role compromise

| Threat | Mitigation |
|---|---|
| `MINTER_ROLE` granted to an EOA | Deploy script asserts `MINTER_ROLE` is held only by `RoundRegistry` (and `RoundRegistry`'s admin is the Safe). Post-deploy invariant test verifies. |
| `DEFAULT_ADMIN_ROLE` retained by deployer EOA after handoff | Deploy script transfers admin to the Safe, then deployer EOA renounces. Post-deploy script + script asserts no role granted to deployer. |
| Safe threshold too low | Safe is created with M-of-N where M ≥ 2. Verified out-of-band before any role is granted. |

### 5.2 Inflation beyond the 10 % monthly cap

| Threat | Mitigation |
|---|---|
| `executeRound` mints more than allowed for the month | `MonthlyMintCap` is a pure library, exhaustively fuzzed (M2). `RoundRegistry` reverts on cap excess. Invariant test enforces sum of executed mints ≤ cap each month. |
| Month boundary manipulation | Cap is computed from `block.timestamp` aligned to UTC month start. Drift of a few minutes does not enable a meaningful additional mint window. |
| Cap snapshot taken at execute time instead of round-start | Spec: cap snapshot is `totalSupply` at start-of-month UTC. Documented in `MonthlyMintCap` natspec; tested in invariant suite. |

### 5.3 Round lifecycle abuse

| Threat | Mitigation |
|---|---|
| `executeRound` called before challenge window expires | Function reverts if `block.timestamp < proposedAt + challengeWindowDays * 1 days`. |
| `executeRound` called twice on the same round | Function reverts if `status != Proposed`. After execution, status becomes `Executed`. |
| `executeRound` called on a `Cancelled` round | Same status check. |
| `proposeRound` with mismatched beneficiaries / amounts arrays | Length check + each amount > 0 enforced. |
| `proposeRound` with arbitrary IPFS URI | The URI is informational; trust comes from the off-chain ratification process, not from the URI being on a specific provider. |
| `cancelRound` abuse | Restricted to the Safe (`DEFAULT_ADMIN_ROLE` or a dedicated admin role). Documented as a break-glass for invalid rounds (e.g. typo in beneficiary address). |
| Reentrancy via `mint(beneficiary, amount)` if `beneficiary` is a malicious contract | OZ `ERC20.mint` does not call back into the receiver. No reentrancy possible. `ReentrancyGuard` still applied to `executeRound` as defense in depth. |

### 5.4 Signature / permit abuse on `AugPocToken`

| Threat | Mitigation |
|---|---|
| Replay of an `ERC20Permit` signature across chains | OZ `ERC20Permit` includes `chainid` in the EIP-712 domain. |
| Replay across deployments | OZ uses the contract address in the domain separator. |
| Permit signed with stale `deadline` | OZ enforces `deadline` check. |

### 5.5 Pause / unpause abuse

| Threat | Mitigation |
|---|---|
| `PAUSER_ROLE` held by single key, used to grief holders | `PAUSER_ROLE` held by the Safe, requiring multisig threshold. |
| Pause used to freeze mint after `executeRound` is in flight | Pause stops `transfer`, not `mint`. Mint paths in `RoundRegistry` are guarded separately by the lifecycle state machine. |

## 6. Required test categories (Phase 1)

| Category | Target | Tooling |
|---|---|---|
| Unit | ≥ 95 % line coverage on `AugPocToken`, `RoundRegistry`, `MonthlyMintCap` | `forge test`, `forge coverage` |
| Fuzz | 10 000 runs default per fuzz test | `forge test --fuzz-runs 10000` |
| Invariants | Sum of executed mints in month M ≤ cap(M); no `Executed` round without prior `Proposed` + window expiration; `MINTER_ROLE` set held = {`RoundRegistry`} | `forge test` invariant tests |
| Static analysis | No medium-or-higher Slither warning | `slither contracts/`, CI `fail-on: medium` |
| Format check | `forge fmt --check` clean | CI |

## 7. Audit plan

- **Internal:** continuous (every PR runs the full CI pipeline).
- **Pre-mainnet:** at least one of — Code4rena Arena-X, Sherlock Watson, documented peer review by 2-3 recognized Solidity engineers. **Mainnet deployment is gated on this.**
- **Bug bounty:** post-mainnet, scoped to the contracts in this repo.

## 8. Disclosure

Security issues should not be opened as public issues. Report to `<security contact TBD>` — to be filled in before mainnet.
