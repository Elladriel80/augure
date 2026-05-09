// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {Script, console2} from "forge-std/Script.sol";

import {RoundRegistry} from "../src/rounds/RoundRegistry.sol";
import {IRoundRegistry} from "../src/interfaces/IRoundRegistry.sol";

/// @title  ProposeGenesisRound — proposes the Augure 2026-05-genesis round on the registry
/// @notice Propose-time helper. Two modes:
///           - Broadcast (BROADCAST=true): signs and broadcasts `proposeRound` using the
///             signer configured via Foundry CLI flags (--ledger / --private-key / etc.).
///             The signer MUST hold ROUND_PROPOSER_ROLE on the registry.
///           - Dry-run (BROADCAST=false): prints the Safe-compatible calldata so the
///             founder can paste it into the Safe Transaction Builder.
///
/// @dev    Required environment variables (broadcast mode):
///           - REGISTRY_ADDRESS    : deployed RoundRegistry address
///           - GENESIS_BENEFICIARY : address that receives the genesis mint (founder EOA)
///           - GENESIS_IPFS_URI    : `ipfs://...` pointer to the pinned valuation_report.md
///           - PROPOSER_ADDRESS    : address that signs the tx; must hold ROUND_PROPOSER_ROLE
///         Optional:
///           - BROADCAST           : "true" to broadcast, anything else to dry-run / print calldata
///
///         Invocation example with Ledger:
///           BROADCAST=true forge script script/ProposeGenesisRound.s.sol:ProposeGenesisRound \
///             --rpc-url $RPC_ARBITRUM_SEPOLIA \
///             --ledger --sender $PROPOSER_ADDRESS --hd-paths "m/44'/60'/0'/0/0" \
///             --broadcast -vv
///
///         Constants — match the off-chain valuation_report.md:
///           Genesis amount: 34_039_500 ether (= 34_039_500 sats × 10^18 wei per token)
///           Challenge window: 30 days (extended for genesis per white paper §11)
contract ProposeGenesisRound is Script {
    uint256 internal constant GENESIS_AMOUNT_WEI = 34_039_500 ether;
    uint32 internal constant GENESIS_CHALLENGE_WINDOW_DAYS = 30;

    function run() external {
        RoundRegistry registry = RoundRegistry(vm.envAddress("REGISTRY_ADDRESS"));
        address beneficiary = vm.envAddress("GENESIS_BENEFICIARY");
        string memory ipfsUri = vm.envString("GENESIS_IPFS_URI");
        bool broadcastMode = vm.envOr("BROADCAST", false);

        require(beneficiary != address(0), "ProposeGenesisRound: beneficiary is zero");
        require(bytes(ipfsUri).length > 0, "ProposeGenesisRound: empty IPFS URI");

        address[] memory beneficiaries = new address[](1);
        beneficiaries[0] = beneficiary;
        uint256[] memory amounts = new uint256[](1);
        amounts[0] = GENESIS_AMOUNT_WEI;

        bytes32 roundHash = keccak256(abi.encode(beneficiaries, amounts, ipfsUri));

        // Verify the round is not already proposed (helpful diagnostic).
        IRoundRegistry.RoundStatus existing = registry.statusOf(roundHash);
        require(
            existing == IRoundRegistry.RoundStatus.None,
            "ProposeGenesisRound: round already exists with this hash on-chain"
        );

        bytes memory calldataBytes = abi.encodeCall(
            RoundRegistry.proposeRound, (roundHash, beneficiaries, amounts, ipfsUri, GENESIS_CHALLENGE_WINDOW_DAYS)
        );

        console2.log("== ProposeGenesisRound ==");
        console2.log("Registry:           ", address(registry));
        console2.log("Beneficiary:        ", beneficiary);
        console2.log("Amount (wei):       ", GENESIS_AMOUNT_WEI);
        console2.log("Amount (tokens):    ", GENESIS_AMOUNT_WEI / 1 ether);
        console2.log("Challenge window:   ", GENESIS_CHALLENGE_WINDOW_DAYS);
        console2.log("Round hash:");
        console2.logBytes32(roundHash);

        if (broadcastMode) {
            address proposer = vm.envAddress("PROPOSER_ADDRESS");
            require(proposer != address(0), "ProposeGenesisRound: PROPOSER_ADDRESS is zero");
            console2.log("Broadcast mode: proposer = ", proposer);

            vm.startBroadcast(proposer);
            registry.proposeRound(roundHash, beneficiaries, amounts, ipfsUri, GENESIS_CHALLENGE_WINDOW_DAYS);
            vm.stopBroadcast();

            console2.log("Round proposed on-chain.");
        } else {
            console2.log("Dry-run mode. Paste the following calldata into Safe Transaction Builder:");
            console2.log("");
            console2.log("To:   ", address(registry));
            console2.log("Value: 0");
            console2.log("Data:");
            console2.logBytes(calldataBytes);
        }
    }
}
