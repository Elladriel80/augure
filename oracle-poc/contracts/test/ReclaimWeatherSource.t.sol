// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {Test} from "forge-std/Test.sol";

import {IReclaim} from "../src/interfaces/IReclaim.sol";
import {IWeatherSource} from "../src/interfaces/IWeatherSource.sol";
import {ReclaimWeatherSource} from "../src/sources/ReclaimWeatherSource.sol";
import {MockReclaimVerifier} from "./mocks/MockReclaimVerifier.sol";

contract ReclaimWeatherSourceTest is Test {
    /*//////////////////////////////////////////////////////////////
                                FIXTURES
    //////////////////////////////////////////////////////////////*/

    MockReclaimVerifier internal verifier;
    ReclaimWeatherSource internal source;

    bytes32 internal constant LOCATION_KJFK = keccak256("KJFK");
    bytes32 internal constant TYPE_TEMP_C = keccak256("TEMP_C");

    address internal constant KEEPER = address(0xBEEF);

    /// @dev Pin block.timestamp to a value that gives generous headroom on both sides of
    ///      the timestamp window, so test arithmetic stays in the positive int range and
    ///      humans can read the values.
    uint256 internal constant FIXED_NOW = 1_800_000_000; // ~2027-01-15

    /*//////////////////////////////////////////////////////////////
                                 SETUP
    //////////////////////////////////////////////////////////////*/

    function setUp() public {
        vm.warp(FIXED_NOW);

        verifier = new MockReclaimVerifier();
        source = new ReclaimWeatherSource(IReclaim(address(verifier)), LOCATION_KJFK, TYPE_TEMP_C);
    }

    /*//////////////////////////////////////////////////////////////
                              CONSTRUCTOR
    //////////////////////////////////////////////////////////////*/

    function test_constructor_setsImmutables() public view {
        assertEq(address(source.VERIFIER()), address(verifier));
        assertEq(source.EXPECTED_LOCATION(), LOCATION_KJFK);
        assertEq(source.EXPECTED_MEASUREMENT_TYPE(), TYPE_TEMP_C);
    }

    function test_constructor_zeroVerifier_reverts() public {
        vm.expectRevert(ReclaimWeatherSource.ZeroAddressVerifier.selector);
        new ReclaimWeatherSource(IReclaim(address(0)), LOCATION_KJFK, TYPE_TEMP_C);
    }

    function test_constructor_zeroLocation_reverts() public {
        vm.expectRevert(ReclaimWeatherSource.ZeroLocation.selector);
        new ReclaimWeatherSource(IReclaim(address(verifier)), bytes32(0), TYPE_TEMP_C);
    }

    function test_constructor_zeroMeasurementType_reverts() public {
        vm.expectRevert(ReclaimWeatherSource.ZeroMeasurementType.selector);
        new ReclaimWeatherSource(IReclaim(address(verifier)), LOCATION_KJFK, bytes32(0));
    }

    /*//////////////////////////////////////////////////////////////
                            SUBMIT — SUCCESS
    //////////////////////////////////////////////////////////////*/

    function test_submit_validProof_storesMeasurement() public {
        int256 valueMc = 23_500; // 23.5 C
        uint64 ts = uint64(FIXED_NOW - 30); // 30 seconds ago

        bytes memory submission = _encodeSubmission(_proofWithSalt(1), valueMc, ts);

        vm.expectEmit(true, true, true, true, address(source));
        emit IWeatherSource.MeasurementSubmitted(LOCATION_KJFK, TYPE_TEMP_C, valueMc, ts, KEEPER);

        vm.prank(KEEPER);
        source.submitMeasurement(submission);

        IWeatherSource.Measurement memory m = source.getLatest(LOCATION_KJFK, TYPE_TEMP_C);
        assertEq(m.value, valueMc);
        assertEq(m.timestamp, ts);
        assertEq(m.location, LOCATION_KJFK);
        assertEq(m.measurementType, TYPE_TEMP_C);

        assertEq(verifier.verifyProofCallCount(), 1);
    }

    function test_submit_then_newerProof_overwritesMeasurement() public {
        bytes memory first = _encodeSubmission(_proofWithSalt(1), 10_000, uint64(FIXED_NOW - 300));
        bytes memory second = _encodeSubmission(_proofWithSalt(2), 12_000, uint64(FIXED_NOW - 60));

        source.submitMeasurement(first);
        source.submitMeasurement(second);

        IWeatherSource.Measurement memory m = source.getLatest(LOCATION_KJFK, TYPE_TEMP_C);
        assertEq(m.value, 12_000);
        assertEq(m.timestamp, uint64(FIXED_NOW - 60));
    }

    /*//////////////////////////////////////////////////////////////
                            SUBMIT — REVERTS
    //////////////////////////////////////////////////////////////*/

    function test_submit_invalidProof_reverts() public {
        verifier.setNextVerdict(false);

        bytes memory submission = _encodeSubmission(_proofWithSalt(1), 20_000, uint64(FIXED_NOW - 30));

        vm.expectRevert(ReclaimWeatherSource.InvalidProof.selector);
        source.submitMeasurement(submission);
    }

    function test_submit_verifierReverts_bubblesUp() public {
        verifier.setShouldRevert(true);

        bytes memory submission = _encodeSubmission(_proofWithSalt(1), 20_000, uint64(FIXED_NOW - 30));

        vm.expectRevert(MockReclaimVerifier.MockRevert.selector);
        source.submitMeasurement(submission);
    }

    function test_submit_replay_reverts() public {
        bytes memory submission = _encodeSubmission(_proofWithSalt(1), 20_000, uint64(FIXED_NOW - 30));

        source.submitMeasurement(submission);

        vm.expectRevert(ReclaimWeatherSource.ProofAlreadyConsumed.selector);
        source.submitMeasurement(submission);
    }

    function test_submit_futureTimestamp_reverts() public {
        uint64 farFuture = uint64(FIXED_NOW + 10 minutes);
        bytes memory submission = _encodeSubmission(_proofWithSalt(1), 20_000, farFuture);

        vm.expectRevert(abi.encodeWithSelector(ReclaimWeatherSource.FutureTimestamp.selector, farFuture, FIXED_NOW));
        source.submitMeasurement(submission);
    }

    function test_submit_staleTimestamp_reverts() public {
        uint64 farPast = uint64(FIXED_NOW - 7 hours);
        bytes memory submission = _encodeSubmission(_proofWithSalt(1), 20_000, farPast);

        vm.expectRevert(abi.encodeWithSelector(ReclaimWeatherSource.StaleMeasurement.selector, farPast, FIXED_NOW));
        source.submitMeasurement(submission);
    }

    function test_submit_notMoreRecent_reverts() public {
        bytes memory first = _encodeSubmission(_proofWithSalt(1), 20_000, uint64(FIXED_NOW - 60));
        bytes memory stale = _encodeSubmission(_proofWithSalt(2), 15_000, uint64(FIXED_NOW - 600));

        source.submitMeasurement(first);

        vm.expectRevert(
            abi.encodeWithSelector(
                ReclaimWeatherSource.NotMoreRecent.selector, uint64(FIXED_NOW - 600), uint64(FIXED_NOW - 60)
            )
        );
        source.submitMeasurement(stale);
    }

    function test_submit_sameTimestamp_reverts() public {
        uint64 ts = uint64(FIXED_NOW - 60);
        bytes memory first = _encodeSubmission(_proofWithSalt(1), 20_000, ts);
        bytes memory dup = _encodeSubmission(_proofWithSalt(2), 25_000, ts);

        source.submitMeasurement(first);

        vm.expectRevert(abi.encodeWithSelector(ReclaimWeatherSource.NotMoreRecent.selector, ts, ts));
        source.submitMeasurement(dup);
    }

    function test_submit_valueTooLow_reverts() public {
        int256 tooLow = source.MIN_VALUE_MC() - 1;
        bytes memory submission = _encodeSubmission(_proofWithSalt(1), tooLow, uint64(FIXED_NOW - 30));

        vm.expectRevert(abi.encodeWithSelector(ReclaimWeatherSource.ValueOutOfRange.selector, tooLow));
        source.submitMeasurement(submission);
    }

    function test_submit_valueTooHigh_reverts() public {
        int256 tooHigh = source.MAX_VALUE_MC() + 1;
        bytes memory submission = _encodeSubmission(_proofWithSalt(1), tooHigh, uint64(FIXED_NOW - 30));

        vm.expectRevert(abi.encodeWithSelector(ReclaimWeatherSource.ValueOutOfRange.selector, tooHigh));
        source.submitMeasurement(submission);
    }

    function test_submit_reentrancy_isBlocked() public {
        bytes memory innerSubmission = _encodeSubmission(_proofWithSalt(2), 18_000, uint64(FIXED_NOW - 60));
        verifier.setShouldReenter(address(source), innerSubmission);

        bytes memory outerSubmission = _encodeSubmission(_proofWithSalt(1), 20_000, uint64(FIXED_NOW - 30));

        // The inner submitMeasurement call from inside verifyProof must hit the
        // ReentrancyGuard and revert; the mock bubbles that revert. OZ v5
        // ReentrancyGuard uses ReentrancyGuardReentrantCall().
        vm.expectRevert(bytes4(keccak256("ReentrancyGuardReentrantCall()")));
        source.submitMeasurement(outerSubmission);
    }

    /*//////////////////////////////////////////////////////////////
                                 VIEWS
    //////////////////////////////////////////////////////////////*/

    function test_getLatest_noMeasurement_reverts() public {
        vm.expectRevert(abi.encodeWithSelector(IWeatherSource.NoMeasurement.selector, LOCATION_KJFK, TYPE_TEMP_C));
        source.getLatest(LOCATION_KJFK, TYPE_TEMP_C);
    }

    function test_getLatest_unknownPair_reverts() public {
        bytes32 unknown = keccak256("UNKNOWN");
        vm.expectRevert(abi.encodeWithSelector(IWeatherSource.NoMeasurement.selector, unknown, TYPE_TEMP_C));
        source.getLatest(unknown, TYPE_TEMP_C);
    }

    function test_isProofConsumed_tracksFlag() public {
        IReclaim.Proof memory p = _proofWithSalt(1);
        assertFalse(source.isProofConsumed(p));

        bytes memory submission = _encodeSubmission(p, 20_000, uint64(FIXED_NOW - 30));
        source.submitMeasurement(submission);

        assertTrue(source.isProofConsumed(p));
    }

    /*//////////////////////////////////////////////////////////////
                                FUZZING
    //////////////////////////////////////////////////////////////*/

    function testFuzz_submit_validValueRange_succeeds(
        int256 valueMc,
        uint32 ageSeconds
    ) public {
        valueMc = bound(valueMc, source.MIN_VALUE_MC(), source.MAX_VALUE_MC());
        ageSeconds = uint32(bound(uint256(ageSeconds), 1, uint256(source.MAX_PAST_SECONDS()) - 1));
        uint64 ts = uint64(FIXED_NOW - ageSeconds);

        bytes memory submission = _encodeSubmission(_proofWithSalt(1), valueMc, ts);
        source.submitMeasurement(submission);

        IWeatherSource.Measurement memory m = source.getLatest(LOCATION_KJFK, TYPE_TEMP_C);
        assertEq(m.value, valueMc);
        assertEq(m.timestamp, ts);
    }

    function testFuzz_submit_valueOutOfRange_alwaysReverts(
        int256 valueMc
    ) public {
        vm.assume(valueMc < source.MIN_VALUE_MC() || valueMc > source.MAX_VALUE_MC());
        bytes memory submission = _encodeSubmission(_proofWithSalt(1), valueMc, uint64(FIXED_NOW - 30));
        vm.expectRevert(abi.encodeWithSelector(ReclaimWeatherSource.ValueOutOfRange.selector, valueMc));
        source.submitMeasurement(submission);
    }

    /*//////////////////////////////////////////////////////////////
                               HELPERS
    //////////////////////////////////////////////////////////////*/

    /// @dev Build a Proof struct whose ABI-encoded form is distinct per `salt`. The
    ///      mock doesn't validate the contents, so the only thing that matters for
    ///      anti-replay tests is that two proofs hash to different keys.
    function _proofWithSalt(
        uint256 salt
    ) internal pure returns (IReclaim.Proof memory) {
        bytes[] memory sigs = new bytes[](1);
        sigs[0] = abi.encodePacked(bytes32(salt));

        return IReclaim.Proof({
            claimInfo: IReclaim.ClaimInfo({
                provider: "http",
                parameters: string(abi.encodePacked('{"url":"https://api.weather.gov/test/', _toString(salt), '"}')),
                context: string(abi.encodePacked('{"extractedParameters":{"salt":"', _toString(salt), '"}}'))
            }),
            signedClaim: IReclaim.SignedClaim({
                claim: IReclaim.CompleteClaimData({
                    identifier: keccak256(abi.encodePacked("identifier", salt)),
                    owner: address(uint160(salt + 0xCAFE)),
                    timestampS: uint32(1_700_000_000 + salt),
                    epoch: 1
                }),
                signatures: sigs
            })
        });
    }

    function _encodeSubmission(
        IReclaim.Proof memory proof,
        int256 valueMc,
        uint64 ts
    ) internal pure returns (bytes memory) {
        return abi.encode(proof, valueMc, ts);
    }

    function _toString(
        uint256 n
    ) internal pure returns (string memory) {
        if (n == 0) return "0";
        uint256 len;
        uint256 tmp = n;
        while (tmp != 0) {
            len++;
            tmp /= 10;
        }
        bytes memory buf = new bytes(len);
        while (n != 0) {
            len--;
            buf[len] = bytes1(uint8(48 + n % 10));
            n /= 10;
        }
        return string(buf);
    }
}
