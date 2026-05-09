// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {Test} from "forge-std/Test.sol";

import {MonthlyMintCap} from "../../src/rounds/MonthlyMintCap.sol";

contract MonthlyMintCapHarness {
    function monthIdOf(
        uint256 timestamp
    ) external pure returns (uint256) {
        return MonthlyMintCap.monthIdOf(timestamp);
    }

    function isMintAdmissible(
        uint256 supply,
        uint256 already,
        uint256 requested
    ) external pure returns (bool) {
        return MonthlyMintCap.isMintAdmissible(supply, already, requested);
    }

    function capFor(
        uint256 supply
    ) external pure returns (uint256) {
        return MonthlyMintCap.capFor(supply);
    }

    function remainingMargin(
        uint256 supply,
        uint256 already
    ) external pure returns (uint256) {
        return MonthlyMintCap.remainingMargin(supply, already);
    }
}

/// @title  MonthlyMintCap fuzz tests
/// @notice Property-based exploration of cap math and the calendar conversion.
contract MonthlyMintCapFuzzTest is Test {
    MonthlyMintCapHarness internal h;

    // Bound timestamps to a reasonable range to keep monthId small enough for arithmetic
    // composition without saturating uint256. 2^40 seconds ≈ year 36812; far beyond any
    // realistic block.timestamp.
    uint256 internal constant MAX_TIMESTAMP = (1 << 40) - 1;

    function setUp() public {
        h = new MonthlyMintCapHarness();
    }

    /*//////////////////////////////////////////////////////////////
                              CALENDAR
    //////////////////////////////////////////////////////////////*/

    /// @dev monthIdOf is monotone non-decreasing as timestamp increases.
    function testFuzz_MonthIdOf_Monotone(
        uint256 t1,
        uint256 t2
    ) public view {
        t1 = bound(t1, 0, MAX_TIMESTAMP);
        t2 = bound(t2, t1, MAX_TIMESTAMP);
        assertGe(h.monthIdOf(t2), h.monthIdOf(t1));
    }

    /// @dev Two timestamps within the same UTC day always share the same monthId.
    function testFuzz_MonthIdOf_SameDay_SameBucket(
        uint256 dayIndex,
        uint256 secondsIntoDay1,
        uint256 secondsIntoDay2
    ) public view {
        dayIndex = bound(dayIndex, 0, MAX_TIMESTAMP / 86_400);
        secondsIntoDay1 = bound(secondsIntoDay1, 0, 86_399);
        secondsIntoDay2 = bound(secondsIntoDay2, 0, 86_399);

        uint256 t1 = dayIndex * 86_400 + secondsIntoDay1;
        uint256 t2 = dayIndex * 86_400 + secondsIntoDay2;
        assertEq(h.monthIdOf(t1), h.monthIdOf(t2));
    }

    /// @dev When stepping by exactly 31 days from any timestamp, the month bucket increases
    ///      by AT LEAST 1 (since no calendar month is longer than 31 days).
    function testFuzz_MonthIdOf_StepBy31Days_IncreasesByAtLeastOne(
        uint256 anchor
    ) public view {
        anchor = bound(anchor, 0, MAX_TIMESTAMP - 31 days);
        uint256 idBefore = h.monthIdOf(anchor);
        uint256 idAfter = h.monthIdOf(anchor + 31 days);
        assertGe(idAfter, idBefore + 1);
    }

    /*//////////////////////////////////////////////////////////////
                              CAP MATH
    //////////////////////////////////////////////////////////////*/

    /// @dev capFor is monotone non-decreasing in supply (modulo the genesis sentinel).
    function testFuzz_CapFor_MonotoneInSupply(
        uint256 s1,
        uint256 s2
    ) public view {
        s1 = bound(s1, 1, type(uint128).max);
        s2 = bound(s2, s1, type(uint128).max);
        assertGe(h.capFor(s2), h.capFor(s1));
    }

    /// @dev capFor(supply) ≤ supply / 10 + 1 (small precision tolerance for integer div).
    function testFuzz_CapFor_NeverExceedsTenPercent(
        uint256 supply
    ) public view {
        supply = bound(supply, 1, type(uint128).max);
        uint256 cap = h.capFor(supply);
        assertLe(cap, supply / 10 + 1);
    }

    /// @dev Any single admitted mint never pushes (already + requested) above the cap when
    ///      supply > 0.
    function testFuzz_IsMintAdmissible_NeverExceedsCap(
        uint256 supply,
        uint256 already,
        uint256 requested
    ) public view {
        supply = bound(supply, 1, type(uint128).max);
        already = bound(already, 0, type(uint128).max);
        requested = bound(requested, 0, type(uint128).max);

        if (h.isMintAdmissible(supply, already, requested)) {
            uint256 cap = h.capFor(supply);
            // requested == 0 is admissible regardless of `already` — that is intentional
            // (no inflation), so guard the assertion against the over-cap defensive case.
            if (requested > 0) {
                assertLe(already + requested, cap);
            }
        }
    }

    /// @dev Sequential mints that respect the cap on each step never exceed the cap in
    ///      cumulative total. Simulates a few steps of incremental admission.
    function testFuzz_IsMintAdmissible_Cumulative(
        uint256 supply,
        uint256 m1,
        uint256 m2,
        uint256 m3
    ) public view {
        supply = bound(supply, 100, type(uint128).max);
        uint256 cap = h.capFor(supply);
        m1 = bound(m1, 0, cap);
        m2 = bound(m2, 0, cap);
        m3 = bound(m3, 0, cap);

        uint256 already = 0;
        if (h.isMintAdmissible(supply, already, m1)) already += m1;
        if (h.isMintAdmissible(supply, already, m2)) already += m2;
        if (h.isMintAdmissible(supply, already, m3)) already += m3;

        assertLe(already, cap);
    }

    /// @dev remainingMargin + already == cap (in the non-genesis non-saturated case).
    function testFuzz_RemainingMargin_PlusAlreadyEqualsCap(
        uint256 supply,
        uint256 already
    ) public view {
        supply = bound(supply, 100, type(uint128).max);
        uint256 cap = h.capFor(supply);
        already = bound(already, 0, cap);

        uint256 margin = h.remainingMargin(supply, already);
        assertEq(margin + already, cap);
    }

    /// @dev capFor(supply == 0) is the max-uint sentinel.
    function testFuzz_CapFor_ZeroSupplyIsSentinel(
        uint256 noise
    ) public view {
        noise; // unused — just to signal this is a fuzz function
        assertEq(h.capFor(0), type(uint256).max);
    }

    /// @dev When supply == 0, every requested amount is admissible.
    function testFuzz_GenesisException_AllowsAnyAmount(
        uint256 already,
        uint256 requested
    ) public view {
        assertTrue(h.isMintAdmissible(0, already, requested));
    }
}
