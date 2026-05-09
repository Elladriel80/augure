> [Lire en français](DEPLOYMENT.fr.md)

# Deployment — Augure contracts (Phase 1)

*Version 0.1 — 2026-05-09 — placeholder, will be filled in detail at Milestone M4.*

## 1. Target

Phase 1 deploys to **Arbitrum Sepolia testnet only**. Mainnet deployment is gated on a community audit (see [`SECURITY.md`](SECURITY.md) §7).

## 2. Prerequisites (filled at M4)

Before running the deploy scripts, the founder must have:

- A funded EOA on Arbitrum Sepolia (a few ETH-Sepolia from a faucet — gas only).
- A Safe multisig deployed on Arbitrum Sepolia (M-of-N, hardware-wallet signers, threshold M ≥ 2).
- An Arbiscan API key (free).
- A Pinata API key (for round IPFS pinning at M5+).
- `.env` filled in from `.env.example`.

## 3. Deployment flow (high level)

```
┌──────────────┐    ┌──────────────────┐    ┌──────────────────┐    ┌────────────────────┐
│ deployer EOA │───▶│ Deploy AugPoc    │───▶│ Deploy           │───▶│ Wire roles:        │
│ (admin temp) │    │ Token            │    │ RoundRegistry    │    │ - Token MINTER →   │
└──────────────┘    └──────────────────┘    └──────────────────┘    │   RoundRegistry    │
                                                                     │ - Token PAUSER →   │
                                                                     │   Safe             │
                                                                     │ - Registry admin → │
                                                                     │   Safe             │
                                                                     └─────────┬──────────┘
                                                                               │
                                                                               ▼
                                                                     ┌────────────────────┐
                                                                     │ Transfer DEFAULT_  │
                                                                     │ ADMIN_ROLE to Safe │
                                                                     │ on every contract  │
                                                                     └─────────┬──────────┘
                                                                               │
                                                                               ▼
                                                                     ┌────────────────────┐
                                                                     │ Deployer EOA       │
                                                                     │ renounces all roles│
                                                                     └─────────┬──────────┘
                                                                               │
                                                                               ▼
                                                                     ┌────────────────────┐
                                                                     │ Verify on Arbiscan │
                                                                     └─────────┬──────────┘
                                                                               │
                                                                               ▼
                                                                     ┌────────────────────┐
                                                                     │ Post-deploy        │
                                                                     │ invariant tests    │
                                                                     │ on live deployment │
                                                                     └────────────────────┘
```

## 4. Scripts (filled at M4)

| Script | Purpose | Caller |
|---|---|---|
| `script/DeployToken.s.sol` | Deploy `AugPocToken`, grant initial roles to deployer EOA | Deployer EOA |
| `script/DeployRegistry.s.sol` | Deploy `RoundRegistry`, wire `MINTER_ROLE` from token | Deployer EOA |
| `script/HandoffToSafe.s.sol` | Transfer admin to Safe, renounce on deployer | Deployer EOA |
| `script/ProposeRound.s.sol` | Generate Safe Transaction Builder calldata for `proposeRound` | Off-chain helper (founder) |
| `script/ExecuteRound.s.sol` | Generate Safe Transaction Builder calldata for `executeRound` | Off-chain helper (founder) |

Privileged actions (`proposeRound`, `executeRound`, `cancelRound`) are **never** executed from an EOA. The scripts emit calldata that the Safe signs and broadcasts.

## 5. Post-deploy verification

A Foundry script `script/VerifyDeployment.s.sol` runs against the live testnet deployment and asserts:

- `token.MINTER_ROLE()` is held only by `RoundRegistry`.
- `token.DEFAULT_ADMIN_ROLE()` is held only by the Safe.
- `registry.DEFAULT_ADMIN_ROLE()` is held only by the Safe.
- The deployer EOA holds **zero** roles on either contract.

## 6. Genesis round execution (M5)

After deployment is verified, the genesis round (`2026-05-genesis`, 34 039 500 tokens to `@Elladriel80`'s wallet) is executed via:

1. Founder pins `valuation_report.md` to IPFS (Pinata).
2. Founder runs `script/ProposeRound.s.sol` to generate the calldata, with a `challengeWindowDays = 30`.
3. Safe executes `proposeRound` — round status becomes `Proposed`.
4. 30 days pass. If no challenge filed and Safe judges the off-chain process clean, `executeRound` calldata is generated and signed.
5. Mint occurs to the beneficiary wallet. `totalSupply` becomes 34 039 500 × 10^18.

## 7. Rollback / break-glass

- A `Proposed` round can be cancelled by the Safe at any point during the challenge window via `cancelRound`.
- A `Challenged` round can be cancelled by the Safe based on the off-chain panel vote outcome.
- A bug discovered in a deployed contract triggers a new deployment + migration. There is no upgradeability switch.
