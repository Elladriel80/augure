// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {Test} from "forge-std/Test.sol";

import {DeployAugurePhase1} from "../../script/DeployAugurePhase1.s.sol";
import {AugPocToken} from "../../src/token/AugPocToken.sol";
import {RoundRegistry} from "../../src/rounds/RoundRegistry.sol";

/// @title  DeployAugurePhase1Test — script-as-test for the deployment flow
/// @notice Runs the entire DeployAugurePhase1 script against a fresh in-memory chain and
///         asserts that every wiring property holds. The same code path is what runs on
///         Arbitrum Sepolia at M4 — just without the actual RPC.
/// @dev    Revert paths of the script's underlying constructors (zero admin, zero token)
///         are already covered by RoundRegistry.t.sol and AugPocToken.t.sol; this file
///         restricts itself to the end-to-end happy path to avoid polluting Foundry's
///         process-wide environment between sibling tests.
contract DeployAugurePhase1Test is Test {
    // Deterministic test key — Anvil default account #0. Public test key from Foundry's
    // built-in mnemonic. The corresponding address is the canonical
    // 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266.
    uint256 internal constant ANVIL_TEST_KEY = 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80;
    address internal constant ANVIL_TEST_ADDR = 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266;

    function test_Deploy_WiresEverythingCorrectly() public {
        // Both DEPLOYER_PK and ADMIN_ADDRESS resolve to the same EOA — the Phase 1 testnet
        // flow described in the script's @dev block.
        vm.setEnv("DEPLOYER_PK", vm.toString(bytes32(ANVIL_TEST_KEY)));
        vm.setEnv("ADMIN_ADDRESS", "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266");

        DeployAugurePhase1 deploy = new DeployAugurePhase1();
        DeployAugurePhase1.DeploymentResult memory result = deploy.run();

        AugPocToken token = result.token;
        RoundRegistry registry = result.registry;

        assertEq(result.admin, ANVIL_TEST_ADDR, "admin should match env var");
        assertGt(uint256(uint160(address(token))), 0, "token deployed");
        assertGt(uint256(uint160(address(registry))), 0, "registry deployed");

        // Token role wiring.
        assertTrue(token.hasRole(token.DEFAULT_ADMIN_ROLE(), ANVIL_TEST_ADDR));
        assertTrue(token.hasRole(token.MINTER_ROLE(), address(registry)));
        assertFalse(token.hasRole(token.MINTER_ROLE(), ANVIL_TEST_ADDR));
        assertTrue(token.hasRole(token.PAUSER_ROLE(), ANVIL_TEST_ADDR));
        assertFalse(token.hasRole(token.BURNER_ROLE(), ANVIL_TEST_ADDR));
        assertFalse(token.hasRole(token.BURNER_ROLE(), address(registry)));

        // Registry role wiring.
        assertTrue(registry.hasRole(registry.DEFAULT_ADMIN_ROLE(), ANVIL_TEST_ADDR));
        assertTrue(registry.hasRole(registry.ROUND_PROPOSER_ROLE(), ANVIL_TEST_ADDR));
        assertTrue(registry.hasRole(registry.ROUND_EXECUTOR_ROLE(), ANVIL_TEST_ADDR));
        assertTrue(registry.hasRole(registry.ROUND_CANCELLER_ROLE(), ANVIL_TEST_ADDR));

        // Token reference is wired.
        assertEq(address(registry.token()), address(token));

        // State sanity.
        assertEq(token.totalSupply(), 0);
        assertFalse(token.paused());
        assertEq(token.decimals(), 18);
        assertEq(token.name(), "Augure POC Token");
        assertEq(token.symbol(), "AUG-POC");
    }
}
