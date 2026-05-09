// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {Script, console2} from "forge-std/Script.sol";

import {AugPocToken} from "../src/token/AugPocToken.sol";
import {RoundRegistry} from "../src/rounds/RoundRegistry.sol";

/// @title  VerifyDeployment — read-only sanity check on a live deployment
/// @notice Re-asserts every role-wiring property that DeployAugurePhase1 set up. Designed to
///         be run independently from the deploy (e.g. from a CI runner or from a different
///         machine) to confirm that the on-chain state matches what was intended.
///
/// @dev    Required environment variables:
///           - TOKEN_ADDRESS    : deployed AugPocToken address
///           - REGISTRY_ADDRESS : deployed RoundRegistry address
///           - ADMIN_ADDRESS    : the address that should hold DEFAULT_ADMIN_ROLE on both
///
///         No private key required — pure read.
contract VerifyDeployment is Script {
    function run() external view {
        AugPocToken token = AugPocToken(vm.envAddress("TOKEN_ADDRESS"));
        RoundRegistry registry = RoundRegistry(vm.envAddress("REGISTRY_ADDRESS"));
        address admin = vm.envAddress("ADMIN_ADDRESS");

        console2.log("== VerifyDeployment ==");
        console2.log("Token:    ", address(token));
        console2.log("Registry: ", address(registry));
        console2.log("Admin:    ", admin);

        // --- Token assertions ---
        require(token.hasRole(token.DEFAULT_ADMIN_ROLE(), admin), "token: admin missing DEFAULT_ADMIN_ROLE");
        require(token.hasRole(token.MINTER_ROLE(), address(registry)), "token: registry missing MINTER_ROLE");
        require(!token.hasRole(token.MINTER_ROLE(), admin), "token: admin must NOT hold MINTER_ROLE");
        require(token.hasRole(token.PAUSER_ROLE(), admin), "token: admin missing PAUSER_ROLE");
        require(!token.hasRole(token.BURNER_ROLE(), admin), "token: admin must NOT hold BURNER_ROLE");
        require(!token.hasRole(token.BURNER_ROLE(), address(registry)), "token: registry must NOT hold BURNER_ROLE");
        require(!token.paused(), "token: must be unpaused at deploy");

        // --- Registry assertions ---
        require(registry.hasRole(registry.DEFAULT_ADMIN_ROLE(), admin), "registry: admin missing DEFAULT_ADMIN_ROLE");
        require(registry.hasRole(registry.ROUND_PROPOSER_ROLE(), admin), "registry: admin missing ROUND_PROPOSER_ROLE");
        require(registry.hasRole(registry.ROUND_EXECUTOR_ROLE(), admin), "registry: admin missing ROUND_EXECUTOR_ROLE");
        require(
            registry.hasRole(registry.ROUND_CANCELLER_ROLE(), admin), "registry: admin missing ROUND_CANCELLER_ROLE"
        );
        require(address(registry.token()) == address(token), "registry: token reference mismatch");

        // --- Token-specific sanity ---
        require(token.totalSupply() == 0, "token: totalSupply must be 0 at fresh deploy");
        require(keccak256(bytes(token.name())) == keccak256(bytes("Augure POC Token")), "token: name mismatch");
        require(keccak256(bytes(token.symbol())) == keccak256(bytes("AUG-POC")), "token: symbol mismatch");
        require(token.decimals() == 18, "token: decimals must be 18");

        console2.log("== All assertions passed ==");
    }
}
