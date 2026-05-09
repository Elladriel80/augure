// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {Test} from "forge-std/Test.sol";
import {IAccessControl} from "@openzeppelin/contracts/access/IAccessControl.sol";

import {AugPocToken} from "../../src/token/AugPocToken.sol";
import {RoundRegistry} from "../../src/rounds/RoundRegistry.sol";
import {IAugPocToken} from "../../src/interfaces/IAugPocToken.sol";
import {IRoundRegistry} from "../../src/interfaces/IRoundRegistry.sol";
import {MonthlyMintCap} from "../../src/rounds/MonthlyMintCap.sol";

/// @title  RoundRegistry unit tests
/// @notice Covers the full propose / challenge / execute / cancel state machine, the lazy
///         supply snapshot, the 10% monthly cap enforcement (including the genesis
///         exception), role gates, hash integrity, and view functions. Targets ≥ 95%
///         coverage on RoundRegistry.sol.
contract RoundRegistryTest is Test {
    AugPocToken internal token;
    RoundRegistry internal registry;

    address internal admin = makeAddr("admin");
    address internal proposer = makeAddr("proposer");
    address internal executor = makeAddr("executor");
    address internal canceller = makeAddr("canceller");
    address internal alice = makeAddr("alice");
    address internal bob = makeAddr("bob");
    address internal carol = makeAddr("carol");
    address internal eve = makeAddr("eve");

    bytes32 internal constant DEFAULT_ADMIN_ROLE = 0x00;

    // 2026-05-09 00:00:00 UTC = day 20582 since Unix epoch = 20582 * 86400.
    uint256 internal constant TEST_TS = 1_778_544_000;

    function setUp() public {
        token = new AugPocToken(admin);
        registry = new RoundRegistry(admin, IAugPocToken(address(token)));

        bytes32 minterRole = token.MINTER_ROLE();
        bytes32 proposerRole = registry.ROUND_PROPOSER_ROLE();
        bytes32 executorRole = registry.ROUND_EXECUTOR_ROLE();
        bytes32 cancellerRole = registry.ROUND_CANCELLER_ROLE();

        vm.startPrank(admin);
        token.grantRole(minterRole, address(registry));
        registry.grantRole(proposerRole, proposer);
        registry.grantRole(executorRole, executor);
        registry.grantRole(cancellerRole, canceller);
        vm.stopPrank();

        vm.warp(TEST_TS);
    }

    /*//////////////////////////////////////////////////////////////
                          HELPERS
    //////////////////////////////////////////////////////////////*/

    function _hashOf(
        address[] memory bens,
        uint256[] memory amts,
        string memory uri
    ) internal pure returns (bytes32) {
        return keccak256(abi.encode(bens, amts, uri));
    }

    function _basicRoundInputs()
        internal
        view
        returns (address[] memory bens, uint256[] memory amts, string memory uri, bytes32 h)
    {
        bens = new address[](2);
        bens[0] = alice;
        bens[1] = bob;
        amts = new uint256[](2);
        amts[0] = 1000e18;
        amts[1] = 2000e18;
        uri = "ipfs://bafy-test-round";
        h = _hashOf(bens, amts, uri);
    }

    function _proposeBasicRound() internal returns (bytes32 h) {
        (address[] memory bens, uint256[] memory amts, string memory uri, bytes32 hash) = _basicRoundInputs();
        vm.prank(proposer);
        registry.proposeRound(hash, bens, amts, uri, 7);
        return hash;
    }

    /*//////////////////////////////////////////////////////////////
                          CONSTRUCTOR
    //////////////////////////////////////////////////////////////*/

    function test_Constructor_RevertsOnZeroAdmin() public {
        vm.expectRevert(IRoundRegistry.ZeroAddressAdmin.selector);
        new RoundRegistry(address(0), IAugPocToken(address(token)));
    }

    function test_Constructor_RevertsOnZeroToken() public {
        vm.expectRevert(IRoundRegistry.ZeroAddressToken.selector);
        new RoundRegistry(admin, IAugPocToken(address(0)));
    }

    function test_Constructor_GrantsAdminRole() public view {
        assertTrue(registry.hasRole(DEFAULT_ADMIN_ROLE, admin));
    }

    function test_Constructor_StoresImmutableTokenReference() public view {
        assertEq(address(registry.token()), address(token));
    }

    /*//////////////////////////////////////////////////////////////
                          PROPOSE — HAPPY PATH
    //////////////////////////////////////////////////////////////*/

    function test_Propose_StoresRoundAndEmitsEvent() public {
        (address[] memory bens, uint256[] memory amts, string memory uri, bytes32 h) = _basicRoundInputs();

        vm.expectEmit(true, false, false, true);
        emit IRoundRegistry.RoundProposed(h, uri, uint64(block.timestamp), 7, bens, amts);

        vm.prank(proposer);
        registry.proposeRound(h, bens, amts, uri, 7);

        assertEq(uint8(registry.statusOf(h)), uint8(IRoundRegistry.RoundStatus.Proposed));
        (string memory storedUri, uint64 proposedAt, uint32 win, IRoundRegistry.RoundStatus st) = registry.getRound(h);
        assertEq(storedUri, uri);
        assertEq(proposedAt, uint64(block.timestamp));
        assertEq(win, 7);
        assertEq(uint8(st), uint8(IRoundRegistry.RoundStatus.Proposed));

        address[] memory storedBens = registry.getRoundBeneficiaries(h);
        uint256[] memory storedAmts = registry.getRoundAmounts(h);
        assertEq(storedBens[0], alice);
        assertEq(storedBens[1], bob);
        assertEq(storedAmts[0], 1000e18);
        assertEq(storedAmts[1], 2000e18);
    }

    /*//////////////////////////////////////////////////////////////
                          PROPOSE — REVERT PATHS
    //////////////////////////////////////////////////////////////*/

    function test_Propose_RevertsForUnauthorizedCaller() public {
        (address[] memory bens, uint256[] memory amts, string memory uri, bytes32 h) = _basicRoundInputs();
        vm.expectRevert(
            abi.encodeWithSelector(
                IAccessControl.AccessControlUnauthorizedAccount.selector, eve, registry.ROUND_PROPOSER_ROLE()
            )
        );
        vm.prank(eve);
        registry.proposeRound(h, bens, amts, uri, 7);
    }

    function test_Propose_RevertsOnEmptyBeneficiaries() public {
        address[] memory bens = new address[](0);
        uint256[] memory amts = new uint256[](0);
        bytes32 h = _hashOf(bens, amts, "ipfs://x");
        vm.expectRevert(IRoundRegistry.EmptyBeneficiaries.selector);
        vm.prank(proposer);
        registry.proposeRound(h, bens, amts, "ipfs://x", 7);
    }

    function test_Propose_RevertsOnMismatchedArrays() public {
        address[] memory bens = new address[](2);
        bens[0] = alice;
        bens[1] = bob;
        uint256[] memory amts = new uint256[](1);
        amts[0] = 1e18;
        bytes32 h = _hashOf(bens, amts, "ipfs://x");
        vm.expectRevert(IRoundRegistry.MismatchedArrays.selector);
        vm.prank(proposer);
        registry.proposeRound(h, bens, amts, "ipfs://x", 7);
    }

    function test_Propose_RevertsOnInvalidWindow_Zero() public {
        (address[] memory bens, uint256[] memory amts, string memory uri, bytes32 h) = _basicRoundInputs();
        vm.expectRevert(IRoundRegistry.InvalidChallengeWindow.selector);
        vm.prank(proposer);
        registry.proposeRound(h, bens, amts, uri, 0);
    }

    function test_Propose_RevertsOnInvalidWindow_TooLarge() public {
        (address[] memory bens, uint256[] memory amts, string memory uri, bytes32 h) = _basicRoundInputs();
        vm.expectRevert(IRoundRegistry.InvalidChallengeWindow.selector);
        vm.prank(proposer);
        registry.proposeRound(h, bens, amts, uri, 366);
    }

    function test_Propose_RevertsOnInvalidHash() public {
        (address[] memory bens, uint256[] memory amts, string memory uri,) = _basicRoundInputs();
        bytes32 bogusHash = bytes32(uint256(0xdeadbeef));
        vm.expectRevert(IRoundRegistry.InvalidRoundHash.selector);
        vm.prank(proposer);
        registry.proposeRound(bogusHash, bens, amts, uri, 7);
    }

    function test_Propose_RevertsOnZeroBeneficiary() public {
        address[] memory bens = new address[](2);
        bens[0] = alice;
        bens[1] = address(0);
        uint256[] memory amts = new uint256[](2);
        amts[0] = 1e18;
        amts[1] = 1e18;
        bytes32 h = _hashOf(bens, amts, "ipfs://x");
        vm.expectRevert(abi.encodeWithSelector(IRoundRegistry.ZeroBeneficiary.selector, 1));
        vm.prank(proposer);
        registry.proposeRound(h, bens, amts, "ipfs://x", 7);
    }

    function test_Propose_RevertsOnZeroAmount() public {
        address[] memory bens = new address[](2);
        bens[0] = alice;
        bens[1] = bob;
        uint256[] memory amts = new uint256[](2);
        amts[0] = 1e18;
        amts[1] = 0;
        bytes32 h = _hashOf(bens, amts, "ipfs://x");
        vm.expectRevert(abi.encodeWithSelector(IRoundRegistry.ZeroAmount.selector, 1));
        vm.prank(proposer);
        registry.proposeRound(h, bens, amts, "ipfs://x", 7);
    }

    function test_Propose_RevertsOnDuplicateHash() public {
        bytes32 h = _proposeBasicRound();
        (address[] memory bens, uint256[] memory amts, string memory uri,) = _basicRoundInputs();
        vm.expectRevert(IRoundRegistry.RoundAlreadyExists.selector);
        vm.prank(proposer);
        registry.proposeRound(h, bens, amts, uri, 7);
    }

    /*//////////////////////////////////////////////////////////////
                              CHALLENGE
    //////////////////////////////////////////////////////////////*/

    function test_Challenge_TransitionsProposedToChallenged() public {
        bytes32 h = _proposeBasicRound();

        vm.expectEmit(true, true, false, true);
        emit IRoundRegistry.RoundChallenged(h, eve, "ipfs://reason");

        vm.prank(eve);
        registry.challengeRound(h, "ipfs://reason");

        assertEq(uint8(registry.statusOf(h)), uint8(IRoundRegistry.RoundStatus.Challenged));
    }

    function test_Challenge_AnyoneCanChallenge() public {
        bytes32 h = _proposeBasicRound();
        vm.prank(carol);
        registry.challengeRound(h, "ipfs://x");
        // No revert — public function.
    }

    function test_Challenge_RevertsAfterWindowExpiry() public {
        bytes32 h = _proposeBasicRound();
        vm.warp(block.timestamp + 7 days + 1);
        vm.expectRevert(IRoundRegistry.ChallengeWindowExpired.selector);
        vm.prank(eve);
        registry.challengeRound(h, "ipfs://reason");
    }

    function test_Challenge_RevertsOnExactWindowEnd() public {
        bytes32 h = _proposeBasicRound();
        vm.warp(block.timestamp + 7 days);
        vm.expectRevert(IRoundRegistry.ChallengeWindowExpired.selector);
        vm.prank(eve);
        registry.challengeRound(h, "ipfs://reason");
    }

    function test_Challenge_RevertsOnUnknownRound() public {
        bytes32 ghost = bytes32(uint256(0x42));
        vm.expectRevert(IRoundRegistry.RoundNotProposed.selector);
        vm.prank(eve);
        registry.challengeRound(ghost, "ipfs://reason");
    }

    function test_Challenge_RevertsOnAlreadyChallenged() public {
        bytes32 h = _proposeBasicRound();
        vm.prank(eve);
        registry.challengeRound(h, "ipfs://x");
        vm.expectRevert(IRoundRegistry.RoundNotProposed.selector);
        vm.prank(carol);
        registry.challengeRound(h, "ipfs://y");
    }

    /*//////////////////////////////////////////////////////////////
                              EXECUTE
    //////////////////////////////////////////////////////////////*/

    function test_Execute_GenesisMintFromZeroSupply() public {
        bytes32 h = _proposeBasicRound();
        vm.warp(block.timestamp + 7 days + 1);

        vm.prank(executor);
        registry.executeRound(h);

        assertEq(uint8(registry.statusOf(h)), uint8(IRoundRegistry.RoundStatus.Executed));
        assertEq(token.balanceOf(alice), 1000e18);
        assertEq(token.balanceOf(bob), 2000e18);
        assertEq(token.totalSupply(), 3000e18);

        // Snapshot was taken at supply == 0, so the cap remained "no constraint" for the
        // entire month — no MonthlyCapExceeded would have fired.
        uint256 monthId = MonthlyMintCap.monthIdOf(block.timestamp);
        assertEq(registry.supplyAtMonthStart(monthId), 0);
        assertEq(registry.mintedInMonth(monthId), 3000e18);
    }

    function test_Execute_RevertsBeforeWindowExpiry() public {
        bytes32 h = _proposeBasicRound();
        vm.warp(block.timestamp + 7 days - 1);
        vm.expectRevert(IRoundRegistry.ChallengeWindowNotExpired.selector);
        vm.prank(executor);
        registry.executeRound(h);
    }

    function test_Execute_PassesAtExactWindowEnd() public {
        bytes32 h = _proposeBasicRound();
        vm.warp(block.timestamp + 7 days);
        vm.prank(executor);
        registry.executeRound(h);
        assertEq(uint8(registry.statusOf(h)), uint8(IRoundRegistry.RoundStatus.Executed));
    }

    function test_Execute_AlsoWorksOnChallengedAfterWindowExpiry() public {
        bytes32 h = _proposeBasicRound();
        vm.prank(eve);
        registry.challengeRound(h, "ipfs://x");
        assertEq(uint8(registry.statusOf(h)), uint8(IRoundRegistry.RoundStatus.Challenged));

        vm.warp(block.timestamp + 7 days);
        vm.prank(executor);
        registry.executeRound(h);
        assertEq(uint8(registry.statusOf(h)), uint8(IRoundRegistry.RoundStatus.Executed));
    }

    function test_Execute_RevertsForUnauthorizedCaller() public {
        bytes32 h = _proposeBasicRound();
        vm.warp(block.timestamp + 7 days);
        vm.expectRevert(
            abi.encodeWithSelector(
                IAccessControl.AccessControlUnauthorizedAccount.selector, eve, registry.ROUND_EXECUTOR_ROLE()
            )
        );
        vm.prank(eve);
        registry.executeRound(h);
    }

    function test_Execute_RevertsIfRoundCancelled() public {
        bytes32 h = _proposeBasicRound();
        vm.prank(canceller);
        registry.cancelRound(h, "ipfs://x");
        vm.warp(block.timestamp + 7 days);
        vm.expectRevert(IRoundRegistry.RoundNotProposedOrChallenged.selector);
        vm.prank(executor);
        registry.executeRound(h);
    }

    function test_Execute_RevertsIfAlreadyExecuted() public {
        bytes32 h = _proposeBasicRound();
        vm.warp(block.timestamp + 7 days);
        vm.prank(executor);
        registry.executeRound(h);

        vm.expectRevert(IRoundRegistry.RoundNotProposedOrChallenged.selector);
        vm.prank(executor);
        registry.executeRound(h);
    }

    function test_Execute_SubsequentRoundUsesSnapshot_NotLatestSupply() public {
        // First round: small mint when supply was zero. Snapshot stored as 0.
        bytes32 h1 = _proposeBasicRound();
        vm.warp(block.timestamp + 7 days);
        vm.prank(executor);
        registry.executeRound(h1);
        assertEq(token.totalSupply(), 3000e18);

        // Second round, same UTC month, would be capped at 10% of supply at month start (=0)
        // EXCEPT for the genesis exception: when snapshot == 0, every amount is admissible.
        // We verify the state machine still works.
        address[] memory bens = new address[](1);
        bens[0] = carol;
        uint256[] memory amts = new uint256[](1);
        amts[0] = 100_000e18;
        string memory uri = "ipfs://second-round";
        bytes32 h2 = _hashOf(bens, amts, uri);
        vm.prank(proposer);
        registry.proposeRound(h2, bens, amts, uri, 7);

        vm.warp(block.timestamp + 7 days);
        vm.prank(executor);
        registry.executeRound(h2);
        assertEq(token.balanceOf(carol), 100_000e18);
    }

    function test_Execute_SecondMonthCapBindsAfterGenesis() public {
        // Genesis month: snapshot is 0, anything goes.
        bytes32 h1 = _proposeBasicRound();
        vm.warp(block.timestamp + 7 days);
        vm.prank(executor);
        registry.executeRound(h1);
        assertEq(token.totalSupply(), 3000e18);

        // Move clock to the next UTC month (45 days from initial proposal). New snapshot
        // will be taken, capturing the current totalSupply (3000e18). Cap = 300e18.
        vm.warp(block.timestamp + 45 days);

        // Try to mint 400e18 — should exceed the cap.
        address[] memory bens = new address[](1);
        bens[0] = carol;
        uint256[] memory amts = new uint256[](1);
        amts[0] = 400e18;
        string memory uri = "ipfs://month2-too-big";
        bytes32 h2 = _hashOf(bens, amts, uri);
        vm.prank(proposer);
        registry.proposeRound(h2, bens, amts, uri, 7);
        vm.warp(block.timestamp + 7 days);

        uint256 expectedMonthId = MonthlyMintCap.monthIdOf(block.timestamp);
        vm.expectRevert(
            abi.encodeWithSelector(
                IRoundRegistry.MonthlyCapExceeded.selector,
                expectedMonthId,
                300e18, // cap = 10% of 3000e18
                0,
                400e18
            )
        );
        vm.prank(executor);
        registry.executeRound(h2);
    }

    function test_Execute_SecondMonthCapAllows10PercentExactly() public {
        bytes32 h1 = _proposeBasicRound();
        vm.warp(block.timestamp + 7 days);
        vm.prank(executor);
        registry.executeRound(h1);

        vm.warp(block.timestamp + 45 days);

        address[] memory bens = new address[](1);
        bens[0] = carol;
        uint256[] memory amts = new uint256[](1);
        amts[0] = 300e18; // exactly 10% of 3000e18
        string memory uri = "ipfs://month2-exact-cap";
        bytes32 h2 = _hashOf(bens, amts, uri);
        vm.prank(proposer);
        registry.proposeRound(h2, bens, amts, uri, 7);
        vm.warp(block.timestamp + 7 days);

        vm.prank(executor);
        registry.executeRound(h2);
        assertEq(token.balanceOf(carol), 300e18);
    }

    /*//////////////////////////////////////////////////////////////
                              CANCEL
    //////////////////////////////////////////////////////////////*/

    function test_Cancel_FromProposed() public {
        bytes32 h = _proposeBasicRound();

        vm.expectEmit(true, true, false, true);
        emit IRoundRegistry.RoundCancelled(h, canceller, "ipfs://reason");

        vm.prank(canceller);
        registry.cancelRound(h, "ipfs://reason");
        assertEq(uint8(registry.statusOf(h)), uint8(IRoundRegistry.RoundStatus.Cancelled));
    }

    function test_Cancel_FromChallenged() public {
        bytes32 h = _proposeBasicRound();
        vm.prank(eve);
        registry.challengeRound(h, "ipfs://x");

        vm.prank(canceller);
        registry.cancelRound(h, "ipfs://upheld");
        assertEq(uint8(registry.statusOf(h)), uint8(IRoundRegistry.RoundStatus.Cancelled));
    }

    function test_Cancel_RevertsForUnauthorized() public {
        bytes32 h = _proposeBasicRound();
        vm.expectRevert(
            abi.encodeWithSelector(
                IAccessControl.AccessControlUnauthorizedAccount.selector, eve, registry.ROUND_CANCELLER_ROLE()
            )
        );
        vm.prank(eve);
        registry.cancelRound(h, "ipfs://x");
    }

    function test_Cancel_RevertsOnExecutedRound() public {
        bytes32 h = _proposeBasicRound();
        vm.warp(block.timestamp + 7 days);
        vm.prank(executor);
        registry.executeRound(h);

        vm.expectRevert(IRoundRegistry.RoundNotCancellable.selector);
        vm.prank(canceller);
        registry.cancelRound(h, "ipfs://x");
    }

    function test_Cancel_RevertsOnAlreadyCancelled() public {
        bytes32 h = _proposeBasicRound();
        vm.prank(canceller);
        registry.cancelRound(h, "ipfs://x");

        vm.expectRevert(IRoundRegistry.RoundNotCancellable.selector);
        vm.prank(canceller);
        registry.cancelRound(h, "ipfs://y");
    }

    function test_Cancel_RevertsOnUnknownRound() public {
        bytes32 ghost = bytes32(uint256(0x42));
        vm.expectRevert(IRoundRegistry.RoundNotCancellable.selector);
        vm.prank(canceller);
        registry.cancelRound(ghost, "ipfs://x");
    }

    /*//////////////////////////////////////////////////////////////
                              VIEWS
    //////////////////////////////////////////////////////////////*/

    function test_View_WindowEndOf_Unknown_ReturnsZero() public view {
        assertEq(registry.windowEndOf(bytes32(uint256(0x99))), 0);
    }

    function test_View_WindowEndOf_KnownRound() public {
        bytes32 h = _proposeBasicRound();
        assertEq(registry.windowEndOf(h), block.timestamp + 7 days);
    }
}
