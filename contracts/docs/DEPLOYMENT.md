> [Lire en français](DEPLOYMENT.fr.md)

# Deployment — Augure contracts (Phase 1)

*Version 1.0 — 2026-05-09*

This document covers the end-to-end deployment of the Phase 1 settlement layer
on Arbitrum Sepolia: token + registry + role wiring, post-deploy verification,
Arbiscan source verification, and the genesis round propose/execute flow.
Mainnet deployment notes live at the bottom — they require a Safe multisig.

## 1. Prerequisites

### One-time setup

- **Foundry** installed locally — see [getfoundry.sh](https://book.getfoundry.sh/getting-started/installation).
- **Forge dependencies installed** in `contracts/`:
  ```bash
  cd contracts
  forge install --no-git foundry-rs/forge-std@v1.9.4
  forge install --no-git OpenZeppelin/openzeppelin-contracts@v5.1.0
  ```
- **Arbiscan API key** (free, 5 min) — register at [arbiscan.io](https://arbiscan.io).
- **Funded EOA on Arbitrum Sepolia** with a small amount of test ETH:
  - Faucet: [faucet.quicknode.com/arbitrum/sepolia](https://faucet.quicknode.com/arbitrum/sepolia)
  - Or bridge from Sepolia ETH: [bridge.arbitrum.io](https://bridge.arbitrum.io)
  - 0.01 ETH-Sepolia is plenty for the entire flow.
- **Pinata account** (free, 1 GB) for round IPFS pinning — register at [pinata.cloud](https://pinata.cloud).

### Per-deployment setup

- Copy `.env.example` to `.env` and fill in:
  - `RPC_ARBITRUM_SEPOLIA` — your RPC endpoint (default public works).
  - `ADMIN_ADDRESS` — the address that will hold `DEFAULT_ADMIN_ROLE`. On Phase 1
    testnet this is the founder's Ledger EOA.
  - `ETHERSCAN_API_KEY` — Etherscan API V2 key (the unified key works for Arbitrum
    Sepolia too — no separate Arbiscan key needed since the V2 API).

The signer is configured via Foundry CLI flags (`--ledger`, `--private-key`, etc.) —
not via the `.env` file. This makes the script reusable with a hardware wallet, a
hot key, or a multisig without code changes.

## 2. Deployment

```bash
cd contracts
source .env

# With a Ledger hardware wallet (Phase 1 testnet):
forge script script/DeployAugurePhase1.s.sol:DeployAugurePhase1 \
  --rpc-url $RPC_ARBITRUM_SEPOLIA \
  --ledger \
  --sender $ADMIN_ADDRESS \
  --hd-paths "m/44'/60'/0'/0/0" \
  --broadcast \
  --verify \
  --etherscan-api-key $ETHERSCAN_API_KEY \
  -vv
```

If your Ledger account was created via Ledger Live, the path may be
`m/44'/60'/<index>'/0/0` instead (one path per account). If Foundry
cannot derive `ADMIN_ADDRESS` from the supplied path, it will refuse to
broadcast — try the alternative path or check the address you imported.

```bash
# With a raw private key (CI / one-shot deploy from a hot wallet):
forge script script/DeployAugurePhase1.s.sol:DeployAugurePhase1 \
  --rpc-url $RPC_ARBITRUM_SEPOLIA \
  --private-key $DEPLOYER_PK \
  --sender $ADMIN_ADDRESS \
  --broadcast \
  --verify \
  --etherscan-api-key $ETHERSCAN_API_KEY \
  -vv
```

Either way, expect to **sign 7 transactions** in sequence (1 token deploy + 1
registry deploy + 5 grantRole calls). On a Ledger this means 7 physical
confirmations on the device.

The script logs the two deployed addresses. Note them — you'll need them for
every subsequent step:

```
AugPocToken deployed at:    0x...
RoundRegistry deployed at:  0x...
```

What it does:
1. Deploys `AugPocToken` with `ADMIN_ADDRESS` as `DEFAULT_ADMIN_ROLE` holder.
2. Deploys `RoundRegistry` with `ADMIN_ADDRESS` as `DEFAULT_ADMIN_ROLE` holder
   and the token reference set immutably.
3. Grants `MINTER_ROLE` on the token to the registry (so `executeRound` can mint).
4. Grants `PAUSER_ROLE` on the token to the admin.
5. Grants `ROUND_PROPOSER_ROLE`, `ROUND_EXECUTOR_ROLE`, `ROUND_CANCELLER_ROLE`
   on the registry to the admin.
6. **`BURNER_ROLE` is NOT granted** — reserved for the future `AugConverter`
   contract that will execute the AUG-POC → AUG conversion at the Phase 2 DAO
   launch (see white paper §7.2).
7. Asserts every role-wiring property in-script before returning.

The `--verify` flag uses your Arbiscan API key to upload the source code, so the
contract's "Code" tab on Arbiscan shows the verified source instead of bytecode.

## 3. Post-deploy verification

Run from a clean shell (or a different machine — useful as an independent check):

```bash
export TOKEN_ADDRESS=0x... # from step 2
export REGISTRY_ADDRESS=0x... # from step 2
export ADMIN_ADDRESS=0x... # same as deployer

forge script script/VerifyDeployment.s.sol:VerifyDeployment \
  --rpc-url $RPC_ARBITRUM_SEPOLIA
```

If the script ends with `== All assertions passed ==`, the on-chain state is
exactly what we expect. Any revert means a wiring problem and **you must not
proceed to genesis** until it is resolved.

## 4. Pin the genesis round to IPFS

```bash
# Pin the entire 2026-05-genesis folder via Pinata's web UI or CLI.
# The recommended approach is to pin the folder itself so the resulting CID
# resolves to the directory listing of all 4 files.

# Once pinned, you get a CID like bafyXXX. The IPFS URI to use is:
#   ipfs://bafyXXX/valuation_report.md

# Save this URI — it is the GENESIS_IPFS_URI env var below.
```

The CID is what binds the on-chain `roundHash` to the off-chain artefacts. If
the file is ever lost from Pinata, the round record on-chain still stands (hash
+ amounts + beneficiaries are immutable), but the human-readable rationale
would have to be republished.

## 5. Genesis round lifecycle

### 5.1 Propose

```bash
export REGISTRY_ADDRESS=0x... # from step 2
export GENESIS_BENEFICIARY=0x... # founder EOA receiving 34_039_500 tokens
export GENESIS_IPFS_URI=ipfs://bafyXXX/valuation_report.md
export PROPOSER_ADDRESS=$ADMIN_ADDRESS # same Ledger EOA in Phase 1 testnet
export BROADCAST=true

forge script script/ProposeGenesisRound.s.sol:ProposeGenesisRound \
  --rpc-url $RPC_ARBITRUM_SEPOLIA \
  --ledger --sender $PROPOSER_ADDRESS --hd-paths "m/44'/60'/0'/0/0" \
  --broadcast \
  -vv
```

The script logs the computed `roundHash`. **Save it** — you'll need it to
execute or cancel later. After this step, the round is live on-chain in the
`Proposed` state with a 30-day challenge window.

### 5.2 Wait

The genesis challenge window is 30 days (per white paper §11) — extended from
the regular 7 days to give prospective investors time to review before
committing.

During this window, anyone can call `challengeRound(roundHash, reasonIpfsUri)`
publicly to flag the valuation. If a challenge is filed:
- The off-chain panel of Top-X holders (X = 5 in Phase 1) reviews and votes.
- If the panel **upholds** the challenge → run §5.3 (Cancel).
- If the panel **dismisses** the challenge → simply let the window expire, then
  run §5.4 (Execute) — the contract executes Challenged rounds the same as
  Proposed ones once the window has passed.

### 5.3 Cancel (only if a challenge is upheld)

```bash
export ROUND_HASH=0x... # from step 5.1
export REASON_IPFS_URI=ipfs://bafyYYY/cancel-rationale.md
export CANCELLER_ADDRESS=$ADMIN_ADDRESS
export BROADCAST=true

forge script script/CancelRound.s.sol:CancelRound \
  --rpc-url $RPC_ARBITRUM_SEPOLIA \
  --ledger --sender $CANCELLER_ADDRESS --hd-paths "m/44'/60'/0'/0/0" \
  --broadcast \
  -vv
```

A cancelled round is permanent. Restarting the genesis flow requires a new
valuation report under a new IPFS CID, which produces a new `roundHash`.

### 5.4 Execute (after 30 days, if not cancelled)

```bash
export ROUND_HASH=0x... # from step 5.1
export EXECUTOR_ADDRESS=$ADMIN_ADDRESS
export BROADCAST=true

forge script script/ExecuteRound.s.sol:ExecuteRound \
  --rpc-url $RPC_ARBITRUM_SEPOLIA \
  --ledger --sender $EXECUTOR_ADDRESS --hd-paths "m/44'/60'/0'/0/0" \
  --broadcast \
  -vv
```

This mints the 34 039 500 AUG-POC tokens to the founder EOA. After execution:
- The round status becomes `Executed` (terminal).
- `token.totalSupply()` becomes `34_039_500 * 10^18`.
- The first month's snapshot is captured at `0` (genesis exception), so
  `MonthlyMintCap` does not bind for this month. From the next UTC month
  onward, the 10% cap kicks in normally.

## 6. Mainnet flow (later)

Phase 1 mainnet deployment is **gated** on:
1. A community audit (Code4rena Arena-X, Sherlock Watson, or documented peer
   review by 2-3 recognized Solidity engineers — see SECURITY.md §7).
2. A Safe multisig deployed on Arbitrum mainnet with at least 2 hardware-wallet
   signers, threshold M ≥ 2.

The deploy flow then differs from §2:
- `ADMIN_ADDRESS` is the Safe multisig address, NOT the deployer EOA.
- `DeployAugurePhase1.s.sol` will refuse to run because of the
  `deployer == admin` assertion. Use the alternate `WireRoles.s.sol` flow
  (planned in a follow-up PR) where the deploy and the role-granting steps
  are split: the deploy is broadcast from the deployer EOA with no role
  wiring, then the role grants are executed by the Safe via the Transaction
  Builder UI.
- All operational scripts (`ProposeGenesisRound`, `ExecuteRound`, `CancelRound`)
  default to `BROADCAST=false` and print Safe-compatible calldata. Paste the
  calldata into the Safe Transaction Builder, get the multisig signatures,
  broadcast.

## 7. Rollback / break-glass

- A `Proposed` or `Challenged` round can be cancelled by the canceller role at
  any time. Cancellation is permanent.
- A bug discovered in a deployed contract triggers a fresh deployment + a
  documented migration. There is no upgradeability switch — see white paper
  §7.2 and ARCHITECTURE.md §7.
- The pause function on the token blocks user-to-user transfers but **does
  not** block mint or burn (intentional — see SECURITY.md §5.5). Use only as
  a defensive measure during incident triage.
