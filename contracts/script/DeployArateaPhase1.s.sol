// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {Script, console2} from "forge-std/Script.sol";

import {AugPocToken} from "../src/token/AugPocToken.sol";
import {RoundRegistry} from "../src/rounds/RoundRegistry.sol";
import {IAugPocToken} from "../src/interfaces/IAugPocToken.sol";

/// @title  DeployAugurePhase1 — deploys the Aratea Phase 1 settlement layer
/// @notice Deploys AugPocToken and RoundRegistry, then wires the roles correctly. The
///         signer is configured EXTERNALLY through Foundry's CLI flags — the script does
///         not read a private key from the environment, which makes it usable with a
///         Ledger hardware wallet, a mnemonic, a keystore, or a raw private key without
///         any code change.
///
///         The deployer (the address that broadcasts the txs) MUST equal the admin (the
///         address that receives `DEFAULT_ADMIN_ROLE`). The script's role-granting steps
///         can only succeed when called by the holder of `DEFAULT_ADMIN_ROLE` — and that
///         is the admin, because the constructor grants the admin role only.
///
/// @dev    Required environment variable:
///           - ADMIN_ADDRESS : address that receives DEFAULT_ADMIN_ROLE on both
///                             contracts AND that broadcasts the deployment.
///                             Phase 1 testnet: founder Ledger EOA.
///                             Mainnet: Safe multisig (broadcast via Safe Tx Builder).
///
///         Invocation examples:
///           # Ledger (Phase 1 testnet)
///           forge script script/DeployAugurePhase1.s.sol:DeployAugurePhase1 \
///             --rpc-url $RPC_ARBITRUM_SEPOLIA \
///             --ledger \
///             --sender $ADMIN_ADDRESS \
///             --hd-paths "m/44'/60'/0'/0/0" \
///             --broadcast --verify --etherscan-api-key $ETHERSCAN_API_KEY -vv
///
///           # Raw private key (CI / one-shot deploy from a hot wallet)
///           forge script script/DeployAugurePhase1.s.sol:DeployAugurePhase1 \
///             --rpc-url $RPC_ARBITRUM_SEPOLIA \
///             --private-key $DEPLOYER_PK \
///             --sender $ADMIN_ADDRESS \
///             --broadcast --verify --etherscan-api-key $ETHERSCAN_API_KEY -vv
///           (the address derived from DEPLOYER_PK MUST equal ADMIN_ADDRESS)
///
///         Role wiring done by this script:
///           AugPocToken:
///             DEFAULT_ADMIN_ROLE   → ADMIN_ADDRESS    (granted by constructor)
///             MINTER_ROLE          → RoundRegistry    (granted here, once registry exists)
///             PAUSER_ROLE          → ADMIN_ADDRESS    (granted here)
///             BURNER_ROLE          → nobody           (reserved for AraConverter at Phase 2)
///           RoundRegistry:
///             DEFAULT_ADMIN_ROLE   → ADMIN_ADDRESS    (granted by constructor)
///             ROUND_PROPOSER_ROLE  → ADMIN_ADDRESS    (granted here)
///             ROUND_EXECUTOR_ROLE  → ADMIN_ADDRESS    (granted here)
///             ROUND_CANCELLER_ROLE → ADMIN_ADDRESS    (granted here)
contract DeployAugurePhase1 is Script {
    struct DeploymentResult {
        AugPocToken token;
        RoundRegistry registry;
        address admin;
    }

    function run() external returns (DeploymentResult memory result) {
        address admin = vm.envAddress("ADMIN_ADDRESS");
        require(admin != address(0), "DeployAugurePhase1: ADMIN_ADDRESS is the zero address");

        console2.log("== DeployAugurePhase1 ==");
        console2.log("Admin (deployer + role recipient):", admin);

        // The signer is provided by Foundry's CLI flags (--ledger / --private-key /
        // --account / --mnemonic). Calling vm.startBroadcast(admin) tells Foundry to
        // route every subsequent state-changing call through whatever signer was
        // configured to sign for `admin`. If the configured signer cannot sign for
        // `admin` (wrong --hd-paths, wrong key), Foundry reverts before broadcasting.
        vm.startBroadcast(admin);

        // --- 1. Deploy AugPocToken with admin as DEFAULT_ADMIN_ROLE holder ---
        AugPocToken token = new AugPocToken(admin);
        console2.log("AugPocToken deployed at:    ", address(token));

        // --- 2. Deploy RoundRegistry with admin as DEFAULT_ADMIN_ROLE holder ---
        RoundRegistry registry = new RoundRegistry(admin, IAugPocToken(address(token)));
        console2.log("RoundRegistry deployed at:  ", address(registry));

        // --- 3. Wire roles ---
        // grantRole succeeds because the signer is `admin`, who holds DEFAULT_ADMIN_ROLE
        // (granted by the constructor of each contract).
        token.grantRole(token.MINTER_ROLE(), address(registry));
        token.grantRole(token.PAUSER_ROLE(), admin);

        registry.grantRole(registry.ROUND_PROPOSER_ROLE(), admin);
        registry.grantRole(registry.ROUND_EXECUTOR_ROLE(), admin);
        registry.grantRole(registry.ROUND_CANCELLER_ROLE(), admin);

        vm.stopBroadcast();

        // --- 4. Post-deploy assertions (read-only, no broadcast) ---
        _assertRoleWiring(token, registry, admin);

        console2.log("== Deployment complete ==");
        console2.log("Run `script/VerifyDeployment.s.sol` to re-check from a fresh VM.");

        return DeploymentResult({token: token, registry: registry, admin: admin});
    }

    function _assertRoleWiring(
        AugPocToken token,
        RoundRegistry registry,
        address admin
    ) private view {
        // Token roles
        require(token.hasRole(token.DEFAULT_ADMIN_ROLE(), admin), "token: admin missing DEFAULT_ADMIN_ROLE");
        require(token.hasRole(token.MINTER_ROLE(), address(registry)), "token: registry missing MINTER_ROLE");
        require(!token.hasRole(token.MINTER_ROLE(), admin), "token: admin must NOT hold MINTER_ROLE");
        require(token.hasRole(token.PAUSER_ROLE(), admin), "token: admin missing PAUSER_ROLE");
        // BURNER_ROLE must NOT be granted at deploy. We can only spot-check known actors
        // (admin, registry, deployer) — there is no on-chain enumeration of role members in
        // base AccessControl. The intention is documented in SECURITY.md and AugPocToken.sol.
        require(!token.hasRole(token.BURNER_ROLE(), admin), "token: admin must NOT hold BURNER_ROLE at deploy");
        require(
            !token.hasRole(token.BURNER_ROLE(), address(registry)),
            "token: registry must NOT hold BURNER_ROLE at deploy"
        );

        // Registry roles
        require(registry.hasRole(registry.DEFAULT_ADMIN_ROLE(), admin), "registry: admin missing DEFAULT_ADMIN_ROLE");
        require(registry.hasRole(registry.ROUND_PROPOSER_ROLE(), admin), "registry: admin missing ROUND_PROPOSER_ROLE");
        require(registry.hasRole(registry.ROUND_EXECUTOR_ROLE(), admin), "registry: admin missing ROUND_EXECUTOR_ROLE");
        require(
            registry.hasRole(registry.ROUND_CANCELLER_ROLE(), admin), "registry: admin missing ROUND_CANCELLER_ROLE"
        );
        require(address(registry.token()) == address(token), "registry: token reference mismatch");
    }
}
