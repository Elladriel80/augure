// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {Script} from "forge-std/Script.sol";
import {console2} from "forge-std/console2.sol";

import {IReclaim} from "../src/interfaces/IReclaim.sol";
import {ReclaimWeatherSource} from "../src/sources/ReclaimWeatherSource.sol";

/// @title  DeployPOC — deploy ReclaimWeatherSource to Arbitrum Sepolia
/// @notice Deploys a single-station, single-type instance pointed at the official
///         Reclaim verifier on Arbitrum Sepolia (per docs.reclaimprotocol.org,
///         retrieved 2026-05-16). Configure overrides via env vars if needed:
///         - RECLAIM_VERIFIER_ADDRESS (defaults to Arbitrum Sepolia official)
///         - WEATHER_LOCATION_KEY     (defaults to "KJFK")
///         - WEATHER_TYPE_KEY         (defaults to "TEMP_C")
///         Required:
///         - PRIVATE_KEY (deployer)
///
///         Usage:
///         forge script script/DeployPOC.s.sol \
///             --rpc-url $RPC_ARBITRUM_SEPOLIA \
///             --broadcast \
///             --verify
contract DeployPOC is Script {
    /// @dev Official Reclaim verifier proxy on Arbitrum Sepolia.
    ///      Source: https://docs.reclaimprotocol.org/onchain/solidity/supported-networks
    address internal constant DEFAULT_RECLAIM_ARBITRUM_SEPOLIA = 0x4D1ee04EB5CeE02d4C123d4b67a86bDc7cA2E62A;

    function run() external returns (ReclaimWeatherSource source) {
        uint256 deployerKey = vm.envUint("PRIVATE_KEY");

        address verifierAddress = vm.envOr("RECLAIM_VERIFIER_ADDRESS", DEFAULT_RECLAIM_ARBITRUM_SEPOLIA);
        string memory locationKey = vm.envOr("WEATHER_LOCATION_KEY", string("KJFK"));
        string memory typeKey = vm.envOr("WEATHER_TYPE_KEY", string("TEMP_C"));

        bytes32 location = keccak256(bytes(locationKey));
        bytes32 measurementType = keccak256(bytes(typeKey));

        console2.log("Deployer:", vm.addr(deployerKey));
        console2.log("Reclaim verifier:", verifierAddress);
        console2.log("Location key:", locationKey);
        console2.log("Type key:", typeKey);

        vm.startBroadcast(deployerKey);
        source = new ReclaimWeatherSource(IReclaim(verifierAddress), location, measurementType);
        vm.stopBroadcast();

        console2.log("ReclaimWeatherSource deployed at:", address(source));
    }
}
