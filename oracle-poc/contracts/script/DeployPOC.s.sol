// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {Script} from "forge-std/Script.sol";
import {console2} from "forge-std/console2.sol";

import {IReclaim} from "../src/interfaces/IReclaim.sol";
import {ReclaimWeatherSource} from "../src/sources/ReclaimWeatherSource.sol";

/// @title  DeployPOC — deploy ReclaimWeatherSource to Arbitrum Sepolia
/// @notice Signer convention matches Aratea/contracts/script/DeployArateaPhase1.s.sol:
///         deployer address from env, actual signer from CLI flag (--ledger / etc).
///         Required env:  DEPLOYER_ADDRESS
///         Optional env:  RECLAIM_VERIFIER_ADDRESS / WEATHER_LOCATION_KEY / WEATHER_TYPE_KEY
contract DeployPOC is Script {
    /// @dev Official Reclaim verifier proxy on Arbitrum Sepolia.
    ///      Source: https://docs.reclaimprotocol.org/onchain/solidity/supported-networks
    address internal constant DEFAULT_RECLAIM_ARBITRUM_SEPOLIA = 0x4D1ee04EB5CeE02d4C123d4b67a86bDc7cA2E62A;

    function run() external returns (ReclaimWeatherSource source) {
        address deployer = vm.envAddress("DEPLOYER_ADDRESS");
        require(deployer != address(0), "DeployPOC: DEPLOYER_ADDRESS is the zero address");

        address verifierAddress = vm.envOr("RECLAIM_VERIFIER_ADDRESS", DEFAULT_RECLAIM_ARBITRUM_SEPOLIA);
        string memory locationKey = vm.envOr("WEATHER_LOCATION_KEY", string("KJFK"));
        string memory typeKey = vm.envOr("WEATHER_TYPE_KEY", string("TEMP_C"));

        bytes32 location = keccak256(bytes(locationKey));
        bytes32 measurementType = keccak256(bytes(typeKey));

        console2.log("== DeployPOC ==");
        console2.log("Deployer:", deployer);
        console2.log("Reclaim verifier:", verifierAddress);
        console2.log("Location key:", locationKey);
        console2.log("Type key:", typeKey);

        vm.startBroadcast(deployer);
        source = new ReclaimWeatherSource(IReclaim(verifierAddress), location, measurementType);
        vm.stopBroadcast();

        console2.log("ReclaimWeatherSource deployed at:", address(source));
    }
}
