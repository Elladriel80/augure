// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {Test} from "forge-std/Test.sol";
import {IAccessControl} from "@openzeppelin/contracts/access/IAccessControl.sol";
import {IERC20Errors} from "@openzeppelin/contracts/interfaces/draft-IERC6093.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";

import {AugPocToken} from "../../src/token/AugPocToken.sol";

/// @title  AugPocToken fuzz tests
/// @notice Probes mint / transfer / burn / pause boundaries with arbitrary amounts and accounts.
///         Configured for ≥ 10_000 runs per test via foundry.toml.
contract AugPocTokenFuzzTest is Test {
    AugPocToken internal token;

    address internal admin = makeAddr("admin");
    address internal minter = makeAddr("minter");
    address internal pauser = makeAddr("pauser");
    address internal burner = makeAddr("burner");

    function setUp() public {
        token = new AugPocToken(admin);

        vm.startPrank(admin);
        token.grantRole(token.MINTER_ROLE(), minter);
        token.grantRole(token.PAUSER_ROLE(), pauser);
        token.grantRole(token.BURNER_ROLE(), burner);
        vm.stopPrank();
    }

    function _assumeStdReceiver(
        address account
    ) internal view {
        vm.assume(account != address(0));
        vm.assume(account.code.length == 0);
        vm.assume(account != address(token));
    }

    /// @dev mint(any non-zero EOA recipient, any amount) increases totalSupply and balance by the
    ///      exact amount, and never overflows for a single mint up to type(uint256).max.
    function testFuzz_Mint_IncreasesSupplyAndBalanceExactly(
        address recipient,
        uint256 amount
    ) public {
        _assumeStdReceiver(recipient);

        uint256 supplyBefore = token.totalSupply();
        uint256 balanceBefore = token.balanceOf(recipient);

        vm.prank(minter);
        token.mint(recipient, amount);

        assertEq(token.totalSupply(), supplyBefore + amount);
        assertEq(token.balanceOf(recipient), balanceBefore + amount);
    }

    /// @dev Any caller without MINTER_ROLE always reverts on mint, regardless of amount.
    function testFuzz_Mint_RevertsForRandomCaller(
        address caller,
        address recipient,
        uint256 amount
    ) public {
        vm.assume(caller != minter);
        vm.assume(!token.hasRole(token.MINTER_ROLE(), caller));
        _assumeStdReceiver(recipient);

        vm.expectRevert(
            abi.encodeWithSelector(
                IAccessControl.AccessControlUnauthorizedAccount.selector, caller, token.MINTER_ROLE()
            )
        );
        vm.prank(caller);
        token.mint(recipient, amount);
    }

    /// @dev transfer(amount > balance) always reverts with ERC20InsufficientBalance.
    function testFuzz_Transfer_RevertsWhenAmountExceedsBalance(
        address sender,
        address recipient,
        uint256 minted,
        uint256 attempted
    ) public {
        _assumeStdReceiver(sender);
        _assumeStdReceiver(recipient);
        vm.assume(sender != recipient);
        attempted = bound(attempted, 1, type(uint128).max);
        minted = bound(minted, 0, attempted - 1);

        vm.prank(minter);
        token.mint(sender, minted);

        vm.expectRevert(
            abi.encodeWithSelector(IERC20Errors.ERC20InsufficientBalance.selector, sender, minted, attempted)
        );
        vm.prank(sender);
        token.transfer(recipient, attempted);
    }

    /// @dev transfer(amount ≤ balance) always succeeds with no pause and conserves totalSupply.
    function testFuzz_Transfer_ConservesTotalSupply(
        address sender,
        address recipient,
        uint256 minted,
        uint256 sent
    ) public {
        _assumeStdReceiver(sender);
        _assumeStdReceiver(recipient);
        vm.assume(sender != recipient);
        minted = bound(minted, 0, type(uint128).max);
        sent = bound(sent, 0, minted);

        vm.prank(minter);
        token.mint(sender, minted);

        uint256 supplyBefore = token.totalSupply();

        vm.prank(sender);
        token.transfer(recipient, sent);

        assertEq(token.totalSupply(), supplyBefore);
        assertEq(token.balanceOf(sender), minted - sent);
        assertEq(token.balanceOf(recipient), sent);
    }

    /// @dev burnFrom(authorised, amount ≤ allowance ≤ balance) decreases supply by amount and is
    ///      never blocked by pause.
    function testFuzz_BurnFrom_DecreasesSupplyEvenWhenPaused(
        address holder,
        uint256 minted,
        uint256 burned
    ) public {
        _assumeStdReceiver(holder);
        minted = bound(minted, 0, type(uint128).max);
        burned = bound(burned, 0, minted);

        vm.prank(minter);
        token.mint(holder, minted);

        vm.prank(holder);
        token.approve(burner, burned);

        // Pause user-to-user transfers; burn must remain operational.
        vm.prank(pauser);
        token.pause();

        uint256 supplyBefore = token.totalSupply();

        vm.prank(burner);
        token.burnFrom(holder, burned);

        assertEq(token.totalSupply(), supplyBefore - burned);
        assertEq(token.balanceOf(holder), minted - burned);
    }

    /// @dev When paused, every user-to-user transfer reverts with EnforcedPause.
    function testFuzz_Pause_BlocksAllUserTransfers(
        address sender,
        address recipient,
        uint256 amount
    ) public {
        _assumeStdReceiver(sender);
        _assumeStdReceiver(recipient);
        vm.assume(sender != recipient);
        amount = bound(amount, 1, type(uint128).max);

        vm.prank(minter);
        token.mint(sender, amount);

        vm.prank(pauser);
        token.pause();

        vm.expectRevert(Pausable.EnforcedPause.selector);
        vm.prank(sender);
        token.transfer(recipient, amount);
    }

    /// @dev grantRole(role, randomAccount) by admin always sets hasRole to true.
    function testFuzz_Admin_CanGrantArbitraryRoleToArbitraryAccount(
        bytes32 role,
        address account
    ) public {
        vm.assume(account != address(0));

        vm.prank(admin);
        token.grantRole(role, account);

        assertTrue(token.hasRole(role, account));
    }
}
