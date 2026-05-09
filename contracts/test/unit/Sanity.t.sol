// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {Test} from "forge-std/Test.sol";

import {AugPocToken} from "../../src/token/AugPocToken.sol";
import {RoundRegistry} from "../../src/rounds/RoundRegistry.sol";

/// @notice M0 sanity test — ensures the toolchain (forge, OZ, forge-std) is correctly wired.
///         Once M1 lands, this test will be deleted in favor of real coverage.
contract SanityTest is Test {
    AugPocToken internal token;
    RoundRegistry internal registry;

    function setUp() public {
        token = new AugPocToken();
        registry = new RoundRegistry();
    }

    function test_PlaceholdersDeploy() public view {
        assertEq(token.PLACEHOLDER(), "M1 will replace this with the real ERC20 + AccessControl + Pausable.");
        assertEq(registry.PLACEHOLDER(), "M3 will replace this with the real round lifecycle + cap enforcement.");
    }
}
