// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {Test} from "forge-std/Test.sol";

import {MonthlyMintCap} from "../../src/rounds/MonthlyMintCap.sol";

/// @notice Test harness that exposes MonthlyMintCap's internal functions to the test runner.
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

/// @title  MonthlyMintCap unit tests
/// @notice Covers calendar conversion (Howard Hinnant), cap math, genesis exception,
///         boundary behaviours. Targets 100% coverage on the library.
contract MonthlyMintCapTest is Test {
    MonthlyMintCapHarness internal h;

    // Reference UTC timestamps. Anchor: 2026-01-01 = day 20454 since 1970-01-01 epoch
    //  (56 years × 365 days + 14 leap years from 1972 to 2024 = 20440 + 14 = 20454).
    // From there, multiply day count × 86400 for the timestamp at 00:00:00 UTC.
    uint256 internal constant TS_1970_01_01 = 0;
    uint256 internal constant TS_2026_05_01 = 1_777_593_600; // day 20574 (= 20454 + 120)
    uint256 internal constant TS_2026_05_31_LAST_SEC = 1_780_271_999; // day 20604 + 86399 sec
    uint256 internal constant TS_2026_06_01 = 1_780_272_000; // day 20605
    uint256 internal constant TS_2024_02_29 = 1_709_164_800; // day 19782, leap day 2024
    uint256 internal constant TS_2100_03_01 = 4_107_542_400; // day 47541, 2100 NOT leap

    function setUp() public {
        h = new MonthlyMintCapHarness();
    }

    /*//////////////////////////////////////////////////////////////
                          CALENDAR — KNOWN DATES
    //////////////////////////////////////////////////////////////*/

    function test_MonthIdOf_Epoch() public view {
        // 1970-01-01 → year=1970, month=1 → 1970*12 + 0 = 23640
        assertEq(h.monthIdOf(TS_1970_01_01), 23_640);
    }

    function test_MonthIdOf_May_2026_Start() public view {
        // 2026-05-01 → 2026*12 + 4 = 24316
        assertEq(h.monthIdOf(TS_2026_05_01), 24_316);
    }

    function test_MonthIdOf_May_2026_LastSecond() public view {
        // Last second of May 2026 still in same bucket as 2026-05-01.
        assertEq(h.monthIdOf(TS_2026_05_31_LAST_SEC), 24_316);
    }

    function test_MonthIdOf_June_2026_Start_IncrementsByOne() public view {
        assertEq(h.monthIdOf(TS_2026_06_01), 24_317);
    }

    function test_MonthIdOf_LeapDay_2024() public view {
        // 2024-02-29 → 2024*12 + 1 = 24289
        assertEq(h.monthIdOf(TS_2024_02_29), 24_289);
    }

    function test_MonthIdOf_NonLeap_Year_2100() public view {
        // 2100 is divisible by 100 but not by 400 → NOT a leap year. March 1 2100.
        // 2100*12 + 2 = 25202
        assertEq(h.monthIdOf(TS_2100_03_01), 25_202);
    }

    function test_MonthIdOf_AllMonthsOfYear_2026_AreContiguous() public view {
        // 2026-01 through 2026-12: month ids should be 24312..24323.
        uint256 base = h.monthIdOf(1_767_225_600); // 2026-01-01 UTC
        assertEq(base, 24_312);
        for (uint256 i = 0; i < 12; i++) {
            // Sample mid-month timestamp for each month of 2026.
            uint256 mid = 1_767_225_600 + (i + 1) * 30 days - 15 days;
            uint256 expected = base + i;
            assertEq(h.monthIdOf(mid), expected, "month bucket mismatch within 2026");
        }
    }

    /*//////////////////////////////////////////////////////////////
                              CAP MATH
    //////////////////////////////////////////////////////////////*/

    function test_CapFor_Zero_ReturnsSentinelMax() public view {
        assertEq(h.capFor(0), type(uint256).max);
    }

    function test_CapFor_OneThousand_ReturnsTen() public view {
        // 1000 * 1000 / 10000 = 100. Wait — 10% of 1000 is 100. Update assertion.
        assertEq(h.capFor(1000), 100);
    }

    function test_CapFor_OneMillion_Tokens() public view {
        // 10% of 1_000_000 = 100_000
        assertEq(h.capFor(1_000_000e18), 100_000e18);
    }

    function test_CapFor_PrecisionLossUnderTen() public view {
        // 9 * 1000 / 10000 = 0 (integer division). Acceptable for a cap.
        assertEq(h.capFor(9), 0);
    }

    function test_CapFor_ExactlyTen() public view {
        assertEq(h.capFor(10), 1);
    }

    /*//////////////////////////////////////////////////////////////
                         IS MINT ADMISSIBLE
    //////////////////////////////////////////////////////////////*/

    function test_IsMintAdmissible_GenesisAlwaysTrue() public view {
        assertTrue(h.isMintAdmissible(0, 0, 0));
        assertTrue(h.isMintAdmissible(0, 0, 1));
        assertTrue(h.isMintAdmissible(0, 0, type(uint256).max));
    }

    function test_IsMintAdmissible_ZeroAmountAlwaysAdmissible() public view {
        assertTrue(h.isMintAdmissible(1000e18, 0, 0));
        assertTrue(h.isMintAdmissible(1000e18, 100e18, 0));
    }

    function test_IsMintAdmissible_ExactCap() public view {
        // 10% of 1000 = 100. With 0 already minted, request 100 → admissible.
        assertTrue(h.isMintAdmissible(1000, 0, 100));
    }

    function test_IsMintAdmissible_OneOverCap() public view {
        assertFalse(h.isMintAdmissible(1000, 0, 101));
    }

    function test_IsMintAdmissible_PartialAlreadyMinted() public view {
        // Cap = 100, 60 already minted → 40 left to mint.
        assertTrue(h.isMintAdmissible(1000, 60, 40));
        assertFalse(h.isMintAdmissible(1000, 60, 41));
    }

    function test_IsMintAdmissible_AlreadyMintedExceedsCap_Defensive() public view {
        // Defensive branch: should never happen in normal operation, but the library must
        // not revert and must return false for any positive request.
        assertFalse(h.isMintAdmissible(1000, 200, 1));
        assertTrue(h.isMintAdmissible(1000, 200, 0)); // requesting 0 still passes
    }

    /*//////////////////////////////////////////////////////////////
                          REMAINING MARGIN
    //////////////////////////////////////////////////////////////*/

    function test_RemainingMargin_Genesis_IsMaxSentinel() public view {
        assertEq(h.remainingMargin(0, 0), type(uint256).max);
    }

    function test_RemainingMargin_FullCapAvailable() public view {
        assertEq(h.remainingMargin(1000, 0), 100);
    }

    function test_RemainingMargin_Partial() public view {
        assertEq(h.remainingMargin(1000, 30), 70);
    }

    function test_RemainingMargin_Exhausted() public view {
        assertEq(h.remainingMargin(1000, 100), 0);
        assertEq(h.remainingMargin(1000, 150), 0); // defensive over-budget case
    }
}
