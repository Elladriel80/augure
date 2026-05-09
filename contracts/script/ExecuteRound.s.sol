// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {Script, console2} from "forge-std/Script.sol";

import {RoundRegistry} from "../src/rounds/RoundRegistry.sol";
import {IRoundRegistry} from "../src/interfaces/IRoundRegistry.sol";

/// @title  ExecuteRound — execute a round whose challenge window has expired
/// @notice Operational helper. Two modes:
///           - Testnet (BROADCAST=true): broadcasts `executeRound` from the executor EOA.
///           - Mainnet (BROADCAST=false): prints the Safe-compatible calldata.
///
/// @dev    Required environment variables (all):
///           - REGISTRY_ADDRESS : deployed RoundRegistry address
///           - ROUND_HASH       : 32-byte hash of the round to execute (0x-prefixed)
///         Optional:
///           - BROADCAST        : "true" to broadcast, false to dry-run (default: false)
///           - EXECUTOR_PK      : required when BROADCAST=true
contract ExecuteRound is Script {
    function run() external {
        RoundRegistry registry = RoundRegistry(vm.envAddress("REGISTRY_ADDRESS"));
        bytes32 roundHash = vm.envBytes32("ROUND_HASH");
        bool broadcastMode = vm.envOr("BROADCAST", false);

        IRoundRegistry.RoundStatus status = registry.statusOf(roundHash);
        require(
            status == IRoundRegistry.RoundStatus.Proposed || status == IRoundRegistry.RoundStatus.Challenged,
            "ExecuteRound: round must be Proposed or Challenged"
        );

        uint256 windowEnd = registry.windowEndOf(roundHash);
        require(block.timestamp >= windowEnd, "ExecuteRound: challenge window not expired yet");

        bytes memory calldataBytes = abi.encodeCall(RoundRegistry.executeRound, (roundHash));

        console2.log("== ExecuteRound ==");
        console2.log("Registry:           ", address(registry));
        console2.log("Round hash:");
        console2.logBytes32(roundHash);
        console2.log("Status (0/1/2/3/4 = None/Proposed/Challenged/Executed/Cancelled): ", uint256(status));
        console2.log("Window ended at (unix): ", windowEnd);

        if (broadcastMode) {
            uint256 executorKey = vm.envUint("EXECUTOR_PK");
            address executor = vm.addr(executorKey);
            console2.log("Broadcast mode: executor = ", executor);

            vm.startBroadcast(executorKey);
            registry.executeRound(roundHash);
            vm.stopBroadcast();

            console2.log("Round executed on-chain.");
        } else {
            console2.log("Dry-run mode. Paste the following calldata into Safe Transaction Builder:");
            console2.log("To:   ", address(registry));
            console2.log("Value: 0");
            console2.log("Data:");
            console2.logBytes(calldataBytes);
        }
    }
}
