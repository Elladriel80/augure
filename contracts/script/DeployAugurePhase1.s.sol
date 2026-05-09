// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {Script, console2} from "forge-std/Script.sol";

import {AugPocToken} from "../src/token/AugPocToken.sol";
import {RoundRegistry} from "../src/rounds/RoundRegistry.sol";
import {IAugPocToken} from "../src/interfaces/IAugPocToken.sol";

/// @title  DeployAugurePhase1 — deploys the Augure Phase 1 settlement layer
/// @notice Deploys AugPocToken and RoundRegistry, then wires the roles correctly. Designed
///         to be safe to run end-to-end on Arbitrum Sepolia from a deployer EOA. On mainnet,
///         the same script runs but the `admin` should be a Safe multisig address (the
///         deployer EOA runs the script, but DEFAULT_ADMIN_ROLE goes straight to the Safe;
///         the deployer never becomes admin).
///
/// @dev    Required environment variables:
///           - DEPLOYER_PK     : private key of the deployer EOA (broadcasts the txs)
///           - ADMIN_ADDRESS   : address that receives DEFAULT_ADMIN_ROLE on both contracts.
///                               Phase 1 testnet: founder EOA. Mainnet: Safe multisig.
///
///         Role wiring done by this script:
///           AugPocToken:
///             DEFAULT_ADMIN_ROLE   → ADMIN_ADDRESS    (granted by constructor)
///             MINTER_ROLE          → RoundRegistry    (granted here, once registry exists)
///             PAUSER_ROLE          → ADMIN_ADDRESS    (granted here)
///             BURNER_ROLE          → nobody           (reserved for AugConverter at Phase 2)
///           RoundRegistry:
///             DEFAULT_ADMIN_ROLE   → ADMIN_ADDRESS    (granted by constructor)
///             ROUND_PROPOSER_ROLE  → ADMIN_ADDRESS    (granted here)
///             ROUND_EXECUTOR_ROLE  → ADMIN_ADDRESS    (granted here)
///             ROUND_CANCELLER_ROLE → ADMIN_ADDRESS    (granted here)
///
///         The deployer EOA does NOT receive any role — it merely broadcasts the
///         constructor and `grantRole` transactions on behalf of the admin. After the
///         script returns, the deployer can walk away cleanly.
contract DeployAugurePhase1 is Script {
    struct DeploymentResult {
        AugPocToken token;
        RoundRegistry registry;
        address admin;
    }

    function run() external returns (DeploymentResult memory result) {
        uint256 deployerKey = vm.envUint("DEPLOYER_PK");
        address admin = vm.envAddress("ADMIN_ADDRESS");
        require(admin != address(0), "DeployAugurePhase1: ADMIN_ADDRESS is the zero address");

        address deployer = vm.addr(deployerKey);
        console2.log("== DeployAugurePhase1 ==");
        console2.log("Deployer (broadcaster):", deployer);
        console2.log("Admin (role recipient): ", admin);

        vm.startBroadcast(deployerKey);

        // --- 1. Deploy AugPocToken with admin as DEFAULT_ADMIN_ROLE holder ---
        AugPocToken token = new AugPocToken(admin);
        console2.log("AugPocToken deployed at:    ", address(token));

        // --- 2. Deploy RoundRegistry with admin as DEFAULT_ADMIN_ROLE holder ---
        RoundRegistry registry = new RoundRegistry(admin, IAugPocToken(address(token)));
        console2.log("RoundRegistry deployed at:  ", address(registry));

        // --- 3. Wire roles ---
        // The deployer cannot grantRole on the contracts unless it has DEFAULT_ADMIN_ROLE.
        // Two-path strategy:
        //   - If `deployer == admin`, the broadcasted txs originate from the admin and
        //     `grantRole` calls succeed normally.
        //   - If `deployer != admin`, the role-granting transactions need a separate signer.
        //     We refuse to deploy in that mode because the script is meant to be self-
        //     contained on testnet. On mainnet, run the deploy under `deployer == admin`
        //     where admin is the Safe (use the Safe's tx-builder to broadcast this script's
        //     calldata) — or run a follow-up script `WireRoles.s.sol` (not in this PR).
        require(
            deployer == admin, "DeployAugurePhase1: deployer must equal admin for role wiring (Phase 1 testnet flow)"
        );

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
