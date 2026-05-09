// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {Test} from "forge-std/Test.sol";
import {IAccessControl} from "@openzeppelin/contracts/access/IAccessControl.sol";
import {IERC20Errors} from "@openzeppelin/contracts/interfaces/draft-IERC6093.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";
import {ECDSA} from "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import {MessageHashUtils} from "@openzeppelin/contracts/utils/cryptography/MessageHashUtils.sol";

import {AugPocToken} from "../../src/token/AugPocToken.sol";

/// @title  AugPocToken unit tests
/// @notice Covers constructor, role-gated mint/burn/pause, transfer pause semantics, and ERC-2612
///         permit. Targets ≥ 95% line coverage on the contract under test.
contract AugPocTokenTest is Test {
    AugPocToken internal token;

    address internal admin = makeAddr("admin");
    address internal minter = makeAddr("minter");
    address internal pauser = makeAddr("pauser");
    address internal burner = makeAddr("burner");
    address internal alice = makeAddr("alice");
    address internal bob = makeAddr("bob");
    address internal eve = makeAddr("eve");

    bytes32 internal constant DEFAULT_ADMIN_ROLE = 0x00;

    bytes32 internal constant PERMIT_TYPEHASH =
        keccak256("Permit(address owner,address spender,uint256 value,uint256 nonce,uint256 deadline)");

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Paused(address account);
    event Unpaused(address account);

    function setUp() public {
        token = new AugPocToken(admin);

        vm.startPrank(admin);
        token.grantRole(token.MINTER_ROLE(), minter);
        token.grantRole(token.PAUSER_ROLE(), pauser);
        token.grantRole(token.BURNER_ROLE(), burner);
        vm.stopPrank();
    }

    /*//////////////////////////////////////////////////////////////
                              CONSTRUCTOR
    //////////////////////////////////////////////////////////////*/

    function test_Constructor_SetsNameAndSymbol() public view {
        assertEq(token.name(), "Augure POC Token");
        assertEq(token.symbol(), "AUG-POC");
    }

    function test_Constructor_HasEighteenDecimals() public view {
        assertEq(token.decimals(), 18);
    }

    function test_Constructor_GrantsAdminRoleToAdmin() public view {
        assertTrue(token.hasRole(DEFAULT_ADMIN_ROLE, admin));
    }

    function test_Constructor_DoesNotGrantOtherRolesAtDeploy() public view {
        assertFalse(token.hasRole(token.MINTER_ROLE(), admin));
        assertFalse(token.hasRole(token.PAUSER_ROLE(), admin));
        assertFalse(token.hasRole(token.BURNER_ROLE(), admin));
    }

    function test_Constructor_StartsUnpausedAndEmpty() public view {
        assertFalse(token.paused());
        assertEq(token.totalSupply(), 0);
    }

    function test_Constructor_RevertsOnZeroAdmin() public {
        vm.expectRevert(AugPocToken.ZeroAddressAdmin.selector);
        new AugPocToken(address(0));
    }

    /*//////////////////////////////////////////////////////////////
                                 MINT
    //////////////////////////////////////////////////////////////*/

    function test_Mint_IncreasesSupplyAndBalance() public {
        vm.prank(minter);
        token.mint(alice, 1000e18);
        assertEq(token.totalSupply(), 1000e18);
        assertEq(token.balanceOf(alice), 1000e18);
    }

    function test_Mint_EmitsTransferFromZero() public {
        vm.expectEmit(true, true, false, true);
        emit Transfer(address(0), alice, 42e18);
        vm.prank(minter);
        token.mint(alice, 42e18);
    }

    function test_Mint_RevertsForUnauthorized() public {
        vm.expectRevert(
            abi.encodeWithSelector(IAccessControl.AccessControlUnauthorizedAccount.selector, eve, token.MINTER_ROLE())
        );
        vm.prank(eve);
        token.mint(alice, 1e18);
    }

    function test_Mint_RevertsForAdminWithoutMinterRole() public {
        vm.expectRevert(
            abi.encodeWithSelector(IAccessControl.AccessControlUnauthorizedAccount.selector, admin, token.MINTER_ROLE())
        );
        vm.prank(admin);
        token.mint(alice, 1e18);
    }

    function test_Mint_NotBlockedByPause() public {
        vm.prank(pauser);
        token.pause();

        vm.prank(minter);
        token.mint(alice, 7e18);
        assertEq(token.balanceOf(alice), 7e18);
    }

    function test_Mint_ToZeroAddressReverts() public {
        vm.expectRevert(abi.encodeWithSelector(IERC20Errors.ERC20InvalidReceiver.selector, address(0)));
        vm.prank(minter);
        token.mint(address(0), 1e18);
    }

    /*//////////////////////////////////////////////////////////////
                               BURN FROM
    //////////////////////////////////////////////////////////////*/

    function _giveAlice(
        uint256 amount
    ) internal {
        vm.prank(minter);
        token.mint(alice, amount);
    }

    function test_BurnFrom_DecreasesSupplyAndBalance() public {
        _giveAlice(1000e18);
        vm.prank(alice);
        token.approve(burner, 400e18);

        vm.prank(burner);
        token.burnFrom(alice, 400e18);

        assertEq(token.totalSupply(), 600e18);
        assertEq(token.balanceOf(alice), 600e18);
    }

    function test_BurnFrom_DecreasesAllowance() public {
        _giveAlice(1000e18);
        vm.prank(alice);
        token.approve(burner, 400e18);

        vm.prank(burner);
        token.burnFrom(alice, 250e18);

        assertEq(token.allowance(alice, burner), 150e18);
    }

    function test_BurnFrom_EmitsTransferToZero() public {
        _giveAlice(1000e18);
        vm.prank(alice);
        token.approve(burner, 100e18);

        vm.expectEmit(true, true, false, true);
        emit Transfer(alice, address(0), 100e18);
        vm.prank(burner);
        token.burnFrom(alice, 100e18);
    }

    function test_BurnFrom_RevertsForUnauthorized() public {
        _giveAlice(1000e18);
        vm.prank(alice);
        token.approve(eve, type(uint256).max);

        vm.expectRevert(
            abi.encodeWithSelector(IAccessControl.AccessControlUnauthorizedAccount.selector, eve, token.BURNER_ROLE())
        );
        vm.prank(eve);
        token.burnFrom(alice, 1e18);
    }

    function test_BurnFrom_RevertsWithoutAllowance() public {
        _giveAlice(1000e18);

        vm.expectRevert(abi.encodeWithSelector(IERC20Errors.ERC20InsufficientAllowance.selector, burner, 0, 1e18));
        vm.prank(burner);
        token.burnFrom(alice, 1e18);
    }

    function test_BurnFrom_RevertsWhenAllowanceTooLow() public {
        _giveAlice(1000e18);
        vm.prank(alice);
        token.approve(burner, 50e18);

        vm.expectRevert(abi.encodeWithSelector(IERC20Errors.ERC20InsufficientAllowance.selector, burner, 50e18, 100e18));
        vm.prank(burner);
        token.burnFrom(alice, 100e18);
    }

    function test_BurnFrom_RevertsWhenBalanceTooLow() public {
        _giveAlice(10e18);
        vm.prank(alice);
        token.approve(burner, type(uint256).max);

        vm.expectRevert(abi.encodeWithSelector(IERC20Errors.ERC20InsufficientBalance.selector, alice, 10e18, 50e18));
        vm.prank(burner);
        token.burnFrom(alice, 50e18);
    }

    function test_BurnFrom_NotBlockedByPause() public {
        _giveAlice(1000e18);
        vm.prank(alice);
        token.approve(burner, 200e18);

        vm.prank(pauser);
        token.pause();

        vm.prank(burner);
        token.burnFrom(alice, 200e18);

        assertEq(token.balanceOf(alice), 800e18);
    }

    function test_BurnFrom_InfiniteAllowanceNotDecreased() public {
        _giveAlice(1000e18);
        vm.prank(alice);
        token.approve(burner, type(uint256).max);

        vm.prank(burner);
        token.burnFrom(alice, 100e18);

        assertEq(token.allowance(alice, burner), type(uint256).max);
    }

    /*//////////////////////////////////////////////////////////////
                              PAUSE / UNPAUSE
    //////////////////////////////////////////////////////////////*/

    function test_Pause_BlocksUserToUserTransfer() public {
        _giveAlice(1000e18);

        vm.prank(pauser);
        token.pause();

        vm.expectRevert(Pausable.EnforcedPause.selector);
        vm.prank(alice);
        token.transfer(bob, 1e18);
    }

    function test_Pause_BlocksTransferFrom() public {
        _giveAlice(1000e18);
        vm.prank(alice);
        token.approve(eve, 100e18);

        vm.prank(pauser);
        token.pause();

        vm.expectRevert(Pausable.EnforcedPause.selector);
        vm.prank(eve);
        token.transferFrom(alice, bob, 50e18);
    }

    function test_Pause_EmitsPausedEvent() public {
        vm.expectEmit(true, false, false, true);
        emit Paused(pauser);
        vm.prank(pauser);
        token.pause();
    }

    function test_Pause_RevertsForUnauthorized() public {
        vm.expectRevert(
            abi.encodeWithSelector(IAccessControl.AccessControlUnauthorizedAccount.selector, eve, token.PAUSER_ROLE())
        );
        vm.prank(eve);
        token.pause();
    }

    function test_Unpause_RestoresTransfers() public {
        _giveAlice(1000e18);

        vm.prank(pauser);
        token.pause();
        vm.prank(pauser);
        token.unpause();

        vm.prank(alice);
        token.transfer(bob, 100e18);
        assertEq(token.balanceOf(bob), 100e18);
    }

    function test_Unpause_EmitsUnpausedEvent() public {
        vm.prank(pauser);
        token.pause();

        vm.expectEmit(true, false, false, true);
        emit Unpaused(pauser);
        vm.prank(pauser);
        token.unpause();
    }

    function test_Unpause_RevertsForUnauthorized() public {
        vm.prank(pauser);
        token.pause();

        vm.expectRevert(
            abi.encodeWithSelector(IAccessControl.AccessControlUnauthorizedAccount.selector, eve, token.PAUSER_ROLE())
        );
        vm.prank(eve);
        token.unpause();
    }

    /*//////////////////////////////////////////////////////////////
                            ACCESS CONTROL
    //////////////////////////////////////////////////////////////*/

    function test_AdminCanGrantAndRevokeMinterRole() public {
        bytes32 minterRole = token.MINTER_ROLE();

        vm.startPrank(admin);
        token.grantRole(minterRole, bob);
        assertTrue(token.hasRole(minterRole, bob));
        token.revokeRole(minterRole, bob);
        vm.stopPrank();

        assertFalse(token.hasRole(minterRole, bob));
    }

    function test_NonAdminCannotGrantMinterRole() public {
        bytes32 minterRole = token.MINTER_ROLE();

        vm.expectRevert(
            abi.encodeWithSelector(IAccessControl.AccessControlUnauthorizedAccount.selector, eve, DEFAULT_ADMIN_ROLE)
        );
        vm.prank(eve);
        token.grantRole(minterRole, bob);
    }

    function test_RevokingMinterStopsFurtherMints() public {
        bytes32 minterRole = token.MINTER_ROLE();

        vm.prank(minter);
        token.mint(alice, 100e18);

        vm.prank(admin);
        token.revokeRole(minterRole, minter);

        vm.expectRevert(
            abi.encodeWithSelector(IAccessControl.AccessControlUnauthorizedAccount.selector, minter, minterRole)
        );
        vm.prank(minter);
        token.mint(alice, 1e18);
    }

    function test_AdminCanRenounceItsOwnRole() public {
        vm.prank(admin);
        token.renounceRole(DEFAULT_ADMIN_ROLE, admin);
        assertFalse(token.hasRole(DEFAULT_ADMIN_ROLE, admin));
    }

    /*//////////////////////////////////////////////////////////////
                          ERC20 STANDARD BEHAVIOR
    //////////////////////////////////////////////////////////////*/

    function test_Transfer_MovesBalance() public {
        _giveAlice(500e18);
        vm.prank(alice);
        token.transfer(bob, 200e18);

        assertEq(token.balanceOf(alice), 300e18);
        assertEq(token.balanceOf(bob), 200e18);
    }

    function test_Approve_TransferFrom() public {
        _giveAlice(500e18);
        vm.prank(alice);
        token.approve(eve, 200e18);

        vm.prank(eve);
        token.transferFrom(alice, bob, 200e18);

        assertEq(token.balanceOf(bob), 200e18);
        assertEq(token.allowance(alice, eve), 0);
    }

    /*//////////////////////////////////////////////////////////////
                              ERC2612 PERMIT
    //////////////////////////////////////////////////////////////*/

    function test_Permit_GrantsAllowanceViaSignature() public {
        uint256 ownerKey = 0xA11CE;
        address owner = vm.addr(ownerKey);
        uint256 value = 123e18;
        uint256 deadline = block.timestamp + 1 hours;

        bytes32 digest = _permitDigest(owner, bob, value, token.nonces(owner), deadline);
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(ownerKey, digest);

        token.permit(owner, bob, value, deadline, v, r, s);

        assertEq(token.allowance(owner, bob), value);
        assertEq(token.nonces(owner), 1);
    }

    function test_Permit_RevertsOnExpiredDeadline() public {
        uint256 ownerKey = 0xA11CE;
        address owner = vm.addr(ownerKey);
        uint256 deadline = block.timestamp - 1;

        bytes32 digest = _permitDigest(owner, bob, 1e18, token.nonces(owner), deadline);
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(ownerKey, digest);

        // OZ uses ERC2612ExpiredSignature(uint256 deadline) — match by sighash to stay decoupled.
        vm.expectRevert(abi.encodeWithSignature("ERC2612ExpiredSignature(uint256)", deadline));
        token.permit(owner, bob, 1e18, deadline, v, r, s);
    }

    function test_Permit_RevertsOnReusedNonce() public {
        uint256 ownerKey = 0xA11CE;
        address owner = vm.addr(ownerKey);
        uint256 deadline = block.timestamp + 1 hours;
        uint256 nonceAtSign = token.nonces(owner);

        bytes32 digest = _permitDigest(owner, bob, 1e18, nonceAtSign, deadline);
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(ownerKey, digest);

        token.permit(owner, bob, 1e18, deadline, v, r, s);

        // The original signature is now bound to a stale nonce; replay attempt must revert.
        vm.expectRevert();
        token.permit(owner, bob, 1e18, deadline, v, r, s);
    }

    function _permitDigest(
        address owner,
        address spender,
        uint256 value,
        uint256 nonce,
        uint256 deadline
    ) internal view returns (bytes32) {
        bytes32 structHash = keccak256(abi.encode(PERMIT_TYPEHASH, owner, spender, value, nonce, deadline));
        return MessageHashUtils.toTypedDataHash(token.DOMAIN_SEPARATOR(), structHash);
    }
}
