> [Lire en français](ROUND-LIFECYCLE.fr.md)

# Round lifecycle — Augure contracts (Phase 1)

*Version 0.1 — 2026-05-09*

## 1. Round states

```
                ┌────────┐
                │  None  │  (uninitialized hash → no record)
                └───┬────┘
                    │ proposeRound()
                    │ ROUND_PROPOSER_ROLE
                    ▼
                ┌──────────┐
        ┌──────▶│ Proposed │
        │       └────┬─────┘
        │            │
        │            │ challengeRound() (anyone)         ┌──────────┐
        │            ├────────────────────────────────▶ │Challenged│
        │            │                                    └────┬─────┘
        │            │                                         │
        │            │                                         │ cancelRound()
        │            │                                         │ ADMIN_ROLE
        │            │                                         ▼
        │            │                                   ┌──────────┐
        │            │                                   │Cancelled │ (terminal)
        │            │                                   └──────────┘
        │            │
        │            │ block.timestamp ≥ proposedAt + challengeWindowDays
        │            │ AND status == Proposed
        │            │ executeRound() — ROUND_EXECUTOR_ROLE
        │            │ → mint to beneficiaries
        │            │ → enforce 10% monthly cap
        │            ▼
        │       ┌──────────┐
        └──cancelRound()──│ Executed │ (terminal)
                          └──────────┘
```

## 2. State transitions

| From | Function | Caller | Conditions | To |
|---|---|---|---|---|
| `None` | `proposeRound` | `ROUND_PROPOSER_ROLE` | `roundHash` unique; `beneficiaries.length == amounts.length`; each `amount > 0`; `challengeWindowDays > 0` | `Proposed` |
| `Proposed` | `challengeRound` | anyone | `block.timestamp < proposedAt + challengeWindowDays * 1 days` | `Challenged` |
| `Proposed` | `executeRound` | `ROUND_EXECUTOR_ROLE` | `block.timestamp ≥ proposedAt + challengeWindowDays * 1 days`; cap 10 % not exceeded | `Executed` |
| `Proposed` | `cancelRound` | `ROUND_CANCELLER_ROLE` | always | `Cancelled` |
| `Challenged` | `cancelRound` | `ROUND_CANCELLER_ROLE` | always | `Cancelled` |
| `Challenged` | (none — Safe must `cancelRound` if challenge upheld, otherwise let window expire and `executeRound`) | — | — | — |
| `Executed`, `Cancelled` | (none — terminal) | — | — | — |

## 3. Round struct (target spec for M3)

```solidity
struct Round {
    bytes32 roundHash;          // hash(beneficiaries, amounts, ipfsUri) — unique key
    string  ipfsUri;            // IPFS pointer to /rounds/archives/<round-id>/valuation_report.md snapshot
    uint64  proposedAt;         // block.timestamp at proposeRound
    uint32  challengeWindowDays;// 7 by default; 30 for genesis (per-round override)
    RoundStatus status;
    address[] beneficiaries;
    uint256[] amounts;          // in token base units (wei, 18 decimals)
}
```

`roundHash` is computed off-chain (and verified by anyone) as `keccak256(abi.encode(beneficiaries, amounts, ipfsUri))`. It is the canonical identity of a round.

## 4. Events (target spec for M3)

```solidity
event RoundProposed(
    bytes32 indexed roundHash,
    string ipfsUri,
    uint64 proposedAt,
    uint32 challengeWindowDays,
    address[] beneficiaries,
    uint256[] amounts
);

event RoundChallenged(
    bytes32 indexed roundHash,
    address indexed challenger,
    string reasonIpfsUri
);

event RoundExecuted(
    bytes32 indexed roundHash,
    uint64 executedAt,
    uint256 totalMinted
);

event RoundCancelled(
    bytes32 indexed roundHash,
    address indexed canceller,
    string reasonIpfsUri
);
```

## 5. Cap enforcement timing

The 10 % monthly cap is checked **at `executeRound` time**, not at `proposeRound` time. Rationale:

- A round can be proposed in month M-1 with a 7-day challenge window that closes in month M; the relevant supply for the cap is the supply at the start of **the month in which the mint occurs**.
- Multiple rounds proposed in the same month consume from the same monthly bucket, in order of execution.
- A round whose execution would push the month over the cap reverts; the Safe can either cancel it or wait for the next month boundary.

## 6. Genesis round special case

`2026-05-genesis` (34 039 500 tokens to `@Elladriel80`) ships with `challengeWindowDays = 30` instead of the default 7. The 10 % monthly cap is **not applicable** to the genesis round because `totalSupply` is 0 before its execution (any mint is "100 % of zero", which the cap math handles as a special "first round" branch).

For the spec: `MonthlyMintCap` returns "no cap binding" when `totalSupplyAtMonthStart == 0`. The very first mint of the protocol is unconstrained by this rule. This is intentional and is the only exception.

## 7. Off-chain ↔ on-chain bridge

```
/rounds/archives/<round-id>/         ──pin──▶  IPFS (Pinata)
                                                  │
                                                  │  CID = bafy...
                                                  ▼
                                          contract.proposeRound(
                                              roundHash,
                                              [beneficiaries...],
                                              [amounts...],
                                              "ipfs://bafy...",
                                              challengeWindowDays
                                          )
```

- The off-chain artefact is the `valuation_report.md` (and the rest of the round folder).
- The hash binds those artefacts to the on-chain record.
- The IPFS URI gives a stable retrieval pointer.
- A challenger can recompute the hash from the published files and verify the on-chain record matches.

## 8. What is intentionally NOT in the lifecycle

- **No automatic conversion of a `Challenged` round into a panel vote.** The vote happens off-chain; the Safe acts on the result. This will move on-chain in Phase 2.
- **No "appeal" path after `Cancelled`.** A cancelled round is terminal. To revive, propose a fresh round with a different `roundHash`.
- **No partial execution.** A round either mints fully to all beneficiaries or reverts.
