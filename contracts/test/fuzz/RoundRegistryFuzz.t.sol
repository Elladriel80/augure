// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {Test} from "forge-std/Test.sol";

import {AugPocToken} from "../../src/token/AugPocToken.sol";
import {RoundRegistry} from "../../src/rounds/RoundRegistry.sol";
import {IAugPocToken} from "../../src/interfaces/IAugPocToken.sol";
import {IRoundRegistry} from "../../src/interfaces/IRoundRegistry.sol";
import {MonthlyMintCap} from "../../src/rounds/MonthlyMintCap.sol";

/// @notice Property-based fuzzing of RoundRegistry. 10 000 runs per test.
contract RoundRegistryFuzzTest is Test {
    AugPocToken internal token;
    RoundRegistry internal registry;

    address internal admin = makeAddr("admin");
    address internal proposer = makeAddr("proposer");
    address internal executor = makeAddr("executor");
    address internal canceller = makeAddr("canceller");

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

        // Anchor at 2026-05-09 00:00:00 UTC. Solidity wrap to handle UTC math correctly.
        vm.warp(1_778_544_000);
    }

    function _makeBensAndAmts(
        uint256 nBeneficiaries,
        uint256 maxAmount,
        uint256 seed
    ) internal pure returns (address[] memory bens, uint256[] memory amts) {
        bens = new address[](nBeneficiaries);
        amts = new uint256[](nBeneficiaries);
        for (uint256 i = 0; i < nBeneficiaries; i++) {
            // Mix the seed with the index to derive distinct addresses and bounded amounts.
            bens[i] = address(uint160(uint256(keccak256(abi.encode(seed, i, "ben"))) | 1));
            amts[i] = (uint256(keccak256(abi.encode(seed, i, "amt"))) % maxAmount) + 1;
        }
    }

    /// @dev Proposing a well-formed round always succeeds when caller is the proposer.
    function testFuzz_Propose_HappyPath(
        uint8 n,
        uint32 windowDays,
        uint128 maxAmount,
        uint256 seed
    ) public {
        n = uint8(bound(n, 1, 10));
        windowDays = uint32(bound(uint256(windowDays), 1, 365));
        maxAmount = uint128(bound(maxAmount, 1, type(uint96).max));

        (address[] memory bens, uint256[] memory amts) = _makeBensAndAmts(n, maxAmount, seed);
        string memory uri = "ipfs://fuzz-round";
        bytes32 h = keccak256(abi.encode(bens, amts, uri));

        vm.prank(proposer);
        registry.proposeRound(h, bens, amts, uri, windowDays);

        assertEq(uint8(registry.statusOf(h)), uint8(IRoundRegistry.RoundStatus.Proposed));
    }

    /// @dev An executed round mints exactly the sum of its amounts to its beneficiaries —
    ///      no over-mint, no under-mint, no leftover allowance.
    function testFuzz_Execute_GenesisExactlyTransfersSumOfAmounts(
        uint8 n,
        uint128 maxAmount,
        uint256 seed
    ) public {
        n = uint8(bound(n, 1, 8));
        maxAmount = uint128(bound(maxAmount, 1, 1_000_000e18));

        (address[] memory bens, uint256[] memory amts) = _makeBensAndAmts(n, maxAmount, seed);

        // Deduplicate beneficiary addresses to avoid accidental double-counting in the
        // balance check below. We compute the expected balance per address.
        string memory uri = "ipfs://fuzz-execute";
        bytes32 h = keccak256(abi.encode(bens, amts, uri));

        vm.prank(proposer);
        registry.proposeRound(h, bens, amts, uri, 7);

        vm.warp(block.timestamp + 7 days);

        uint256 expectedTotal;
        for (uint256 i = 0; i < n; i++) {
            expectedTotal += amts[i];
        }

        vm.prank(executor);
        registry.executeRound(h);

        assertEq(token.totalSupply(), expectedTotal);

        // Sum balances over distinct addresses.
        uint256 observedSum;
        for (uint256 i = 0; i < n; i++) {
            // Only count once per unique address.
            bool firstOccurrence = true;
            for (uint256 j = 0; j < i; j++) {
                if (bens[j] == bens[i]) {
                    firstOccurrence = false;
                    break;
                }
            }
            if (firstOccurrence) observedSum += token.balanceOf(bens[i]);
        }
        assertEq(observedSum, expectedTotal);
    }

    /// @dev Cancelling at any point before execution always lands in Cancelled state and
    ///      forbids future execution.
    function testFuzz_Cancel_ForbidsExecute(
        uint32 windowDays,
        uint256 cancelTimeOffset
    ) public {
        windowDays = uint32(bound(uint256(windowDays), 1, 30));
        cancelTimeOffset = bound(cancelTimeOffset, 0, uint256(windowDays) * 1 days + 5 days);

        address[] memory bens = new address[](1);
        bens[0] = makeAddr("ben");
        uint256[] memory amts = new uint256[](1);
        amts[0] = 1e18;
        string memory uri = "ipfs://fuzz-cancel";
        bytes32 h = keccak256(abi.encode(bens, amts, uri));

        vm.prank(proposer);
        registry.proposeRound(h, bens, amts, uri, windowDays);

        vm.warp(block.timestamp + cancelTimeOffset);

        vm.prank(canceller);
        registry.cancelRound(h, "ipfs://x");

        // Even after the window has passed, executor cannot revive a cancelled round.
        vm.warp(block.timestamp + uint256(windowDays) * 1 days + 1);
        vm.expectRevert(IRoundRegistry.RoundNotProposedOrChallenged.selector);
        vm.prank(executor);
        registry.executeRound(h);
    }

    /// @dev `executeRound` never produces total mintedInMonth above the snapshot-derived cap
    ///      when the snapshot is non-zero.
    function testFuzz_Execute_NeverExceedsCap(
        uint128 firstMonthMint,
        uint128 secondMonthAttempt
    ) public {
        firstMonthMint = uint128(bound(firstMonthMint, 1e18, 1_000_000e18));
        secondMonthAttempt = uint128(bound(secondMonthAttempt, 1, type(uint96).max));

        // First-month round (genesis): supply == 0, anything goes.
        address[] memory bens = new address[](1);
        bens[0] = makeAddr("genesis-ben");
        uint256[] memory amts = new uint256[](1);
        amts[0] = firstMonthMint;
        bytes32 h1 = keccak256(abi.encode(bens, amts, "ipfs://genesis"));

        vm.prank(proposer);
        registry.proposeRound(h1, bens, amts, "ipfs://genesis", 7);
        vm.warp(block.timestamp + 7 days);
        vm.prank(executor);
        registry.executeRound(h1);

        // Move 45 days forward to enter a new UTC month.
        vm.warp(block.timestamp + 45 days);

        // Try to execute a second-month round.
        bens[0] = makeAddr("month2-ben");
        amts[0] = secondMonthAttempt;
        bytes32 h2 = keccak256(abi.encode(bens, amts, "ipfs://month2"));
        vm.prank(proposer);
        registry.proposeRound(h2, bens, amts, "ipfs://month2", 7);
        vm.warp(block.timestamp + 7 days);

        uint256 supplyBefore = token.totalSupply();
        uint256 cap = (supplyBefore * 1000) / 10_000; // 10%

        if (secondMonthAttempt <= cap) {
            vm.prank(executor);
            registry.executeRound(h2);
            assertEq(token.totalSupply(), supplyBefore + secondMonthAttempt);
        } else {
            uint256 monthId = MonthlyMintCap.monthIdOf(block.timestamp);
            vm.expectRevert(
                abi.encodeWithSelector(
                    IRoundRegistry.MonthlyCapExceeded.selector, monthId, cap, 0, uint256(secondMonthAttempt)
                )
            );
            vm.prank(executor);
            registry.executeRound(h2);
            assertEq(token.totalSupply(), supplyBefore);
        }
    }
}
