// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {Script, console2} from "forge-std/Script.sol";

import {RoundRegistry} from "../src/rounds/RoundRegistry.sol";
import {IRoundRegistry} from "../src/interfaces/IRoundRegistry.sol";

/// @title  CancelRound — cancel a Proposed or Challenged round
/// @notice Break-glass helper. Two modes (testnet broadcast / mainnet calldata-print). Use
///         when an off-chain panel upholds a challenge, or when a typo / stale round must
///         be killed before its window expires.
///
/// @dev    Required env vars: REGISTRY_ADDRESS, ROUND_HASH, REASON_IPFS_URI.
///         Optional: BROADCAST=true + CANCELLER_PK.
contract CancelRound is Script {
    function run() external {
        RoundRegistry registry = RoundRegistry(vm.envAddress("REGISTRY_ADDRESS"));
        bytes32 roundHash = vm.envBytes32("ROUND_HASH");
        string memory reasonUri = vm.envString("REASON_IPFS_URI");
        bool broadcastMode = vm.envOr("BROADCAST", false);

        IRoundRegistry.RoundStatus status = registry.statusOf(roundHash);
        require(
            status == IRoundRegistry.RoundStatus.Proposed || status == IRoundRegistry.RoundStatus.Challenged,
            "CancelRound: round must be Proposed or Challenged"
        );

        bytes memory calldataBytes = abi.encodeCall(RoundRegistry.cancelRound, (roundHash, reasonUri));

        console2.log("== CancelRound ==");
        console2.log("Registry:    ", address(registry));
        console2.log("Round hash:");
        console2.logBytes32(roundHash);
        console2.log("Reason URI:  ", reasonUri);

        if (broadcastMode) {
            uint256 cancellerKey = vm.envUint("CANCELLER_PK");
            address canceller = vm.addr(cancellerKey);
            console2.log("Broadcast mode: canceller = ", canceller);

            vm.startBroadcast(cancellerKey);
            registry.cancelRound(roundHash, reasonUri);
            vm.stopBroadcast();

            console2.log("Round cancelled on-chain.");
        } else {
            console2.log("Dry-run mode. Paste the following calldata into Safe Transaction Builder:");
            console2.log("To:   ", address(registry));
            console2.log("Value: 0");
            console2.log("Data:");
            console2.logBytes(calldataBytes);
        }
    }
}
