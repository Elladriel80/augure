// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

import {IReclaim} from "../interfaces/IReclaim.sol";
import {IWeatherSource} from "../interfaces/IWeatherSource.sol";

/// @title  ReclaimWeatherSource — Reclaim-backed implementation of IWeatherSource
/// @notice POC implementation that ingests weather measurements attested by a Reclaim
///         zkFetch proof. Validates the proof through the official Reclaim verifier,
///         then stores the latest measurement for a single (location, type) pair.
/// @dev    Scope is intentionally narrow (POC, whitepaper v0.5 §5 brick #1):
///         - Single-station, single-type instance (set at construction).
///         - The contract trusts the keeper to declare value/timestamp matching the
///           proof's `context.extractedParameters`. It does NOT parse the JSON context
///           on-chain. This is acceptable for the POC because the keeper is the project
///           itself; Phase 2/3 will add `context` parsing and slashing-backed honesty.
///         - No multi-source aggregation, no dispute, no slashing. See SPEC.md and
///           docs/POC-NOTES.md for the explicit out-of-scope matrix.
///         - The Reclaim verifier is UUPS-upgradeable upstream; ReentrancyGuard protects
///           against a hypothetical compromised upgrade re-entering this contract.
contract ReclaimWeatherSource is IWeatherSource, ReentrancyGuard {
    /*//////////////////////////////////////////////////////////////
                                CONSTANTS
    //////////////////////////////////////////////////////////////*/

    /// @notice Minimum acceptable measurement value, in milliCelsius. -100.000 C is below
    ///         the lowest reliably recorded terrestrial temperature (~-89 C, Vostok 1983)
    ///         with a safe margin. Submissions outside the range indicate keeper bug or
    ///         upstream data corruption and are rejected.
    int256 public constant MIN_VALUE_MC = -100_000;

    /// @notice Maximum acceptable measurement value, in milliCelsius. +70.000 C is well
    ///         above the highest reliably recorded terrestrial temperature (~+56.7 C,
    ///         Death Valley 1913) with a safe margin.
    int256 public constant MAX_VALUE_MC = 70_000;

    /// @notice Maximum allowed future-dating of a measurement timestamp, in seconds.
    ///         Tolerates clock skew between the upstream agency and the chain.
    uint64 public constant MAX_FUTURE_SECONDS = 5 minutes;

    /// @notice Maximum allowed staleness of a measurement timestamp, in seconds.
    ///         Aligned with the keeper poll cadence (10 minutes); 6 hours gives generous
    ///         headroom for transient keeper / NWS outages without silently accepting
    ///         arbitrarily old data.
    uint64 public constant MAX_PAST_SECONDS = 6 hours;

    /*//////////////////////////////////////////////////////////////
                                IMMUTABLES
    //////////////////////////////////////////////////////////////*/

    /// @notice The Reclaim verifier this source delegates proof validation to.
    IReclaim public immutable VERIFIER;

    /// @notice The single station this POC instance accepts measurements for.
    bytes32 public immutable EXPECTED_LOCATION;

    /// @notice The single measurement type this POC instance accepts.
    bytes32 public immutable EXPECTED_MEASUREMENT_TYPE;

    /*//////////////////////////////////////////////////////////////
                                 STORAGE
    //////////////////////////////////////////////////////////////*/

    /// @dev Storage key is keccak256(location, type). For the POC there is only one entry,
    ///      but the mapping shape is Phase 2-ready.
    mapping(bytes32 storageKey => Measurement) private _latest;

    /// @dev Anti-replay: each proof can only fund one submission. Key is the hash of the
    ///      decoded Proof struct.
    mapping(bytes32 proofHash => bool consumed) private _consumedProofs;

    /*//////////////////////////////////////////////////////////////
                                ERRORS
    //////////////////////////////////////////////////////////////*/

    error ZeroAddressVerifier();
    error ZeroLocation();
    error ZeroMeasurementType();
    error ProofAlreadyConsumed();
    error FutureTimestamp(uint64 declaredTimestamp, uint256 nowTimestamp);
    error StaleMeasurement(uint64 declaredTimestamp, uint256 nowTimestamp);
    error NotMoreRecent(uint64 declaredTimestamp, uint64 storedTimestamp);
    error ValueOutOfRange(int256 declaredValue);

    /*//////////////////////////////////////////////////////////////
                              CONSTRUCTOR
    //////////////////////////////////////////////////////////////*/

    /// @param verifier The deployed Reclaim verifier contract on the target chain.
    /// @param expectedLocation The single station identifier this instance accepts
    ///        (e.g. keccak256("KJFK")).
    /// @param expectedMeasurementType The single measurement type this instance accepts
    ///        (e.g. keccak256("TEMP_C")).
    constructor(
        IReclaim verifier,
        bytes32 expectedLocation,
        bytes32 expectedMeasurementType
    ) {
        if (address(verifier) == address(0)) revert ZeroAddressVerifier();
        if (expectedLocation == bytes32(0)) revert ZeroLocation();
        if (expectedMeasurementType == bytes32(0)) revert ZeroMeasurementType();

        VERIFIER = verifier;
        EXPECTED_LOCATION = expectedLocation;
        EXPECTED_MEASUREMENT_TYPE = expectedMeasurementType;
    }

    /*//////////////////////////////////////////////////////////////
                              SUBMISSION
    //////////////////////////////////////////////////////////////*/

    /// @inheritdoc IWeatherSource
    /// @dev `encodedSubmission` is the ABI-encoded tuple
    ///      `(IReclaim.Proof proof, int256 declaredValueMc, uint64 declaredTimestamp)`.
    ///      The keeper builds this off-chain after a successful zkFetch call.
    /// @custom:slither-suppress reentrancy-no-eth — Slither flags state writes after the
    ///      VERIFIER.verifyProof external call as reentrancy. This is safe because:
    ///      (a) the function is `nonReentrant` (OZ v5 ReentrancyGuard) so any re-entry
    ///          attempt — including from a hypothetical compromised UUPS upgrade of the
    ///          verifier — reverts with ReentrancyGuardReentrantCall; covered by
    ///          test_submit_reentrancy_isBlocked;
    ///      (b) the proof-hash anti-replay check runs BEFORE the external call, so even
    ///          if the guard somehow yielded, the same proof could not be replayed within
    ///          the same call tree;
    ///      (c) VERIFIER is immutable, set at construction to the address audited at
    ///          deploy time (Reclaim official proxy on Arbitrum Sepolia).
    // slither-disable-next-line reentrancy-no-eth
    function submitMeasurement(
        bytes calldata encodedSubmission
    ) external nonReentrant {
        (IReclaim.Proof memory proof, int256 declaredValueMc, uint64 declaredTimestamp) =
            abi.decode(encodedSubmission, (IReclaim.Proof, int256, uint64));

        // ---- CHECKS (cheap, no external calls) ----

        bytes32 proofHash = keccak256(abi.encode(proof));
        if (_consumedProofs[proofHash]) revert ProofAlreadyConsumed();

        if (declaredValueMc < MIN_VALUE_MC || declaredValueMc > MAX_VALUE_MC) {
            revert ValueOutOfRange(declaredValueMc);
        }

        if (uint256(declaredTimestamp) > block.timestamp + MAX_FUTURE_SECONDS) {
            revert FutureTimestamp(declaredTimestamp, block.timestamp);
        }
        if (uint256(declaredTimestamp) + MAX_PAST_SECONDS < block.timestamp) {
            revert StaleMeasurement(declaredTimestamp, block.timestamp);
        }

        bytes32 key = _storageKey(EXPECTED_LOCATION, EXPECTED_MEASUREMENT_TYPE);
        Measurement storage stored = _latest[key];
        if (stored.timestamp != 0 && declaredTimestamp <= stored.timestamp) {
            revert NotMoreRecent(declaredTimestamp, stored.timestamp);
        }

        // ---- INTERACTION (protected by nonReentrant) ----
        // The Reclaim verifier uses `require(...)` for every invalid-proof case (no
        // signatures, wrong identifier hash, wrong number of witnesses, signer not in
        // whitelist). A non-reverting call therefore means every check passed.
        //
        // We deliberately do NOT inspect the bool return: the deployed implementation
        // on Arbitrum Sepolia omits the final `return true;` so it always returns the
        // default false even when valid. See IReclaim NatSpec for full rationale.
        // The InvalidProof() revert here is therefore reachable only via the verifier
        // bubbling its own require-revert (which propagates naturally).
        VERIFIER.verifyProof(proof);

        // ---- EFFECTS ----
        _consumedProofs[proofHash] = true;
        stored.value = declaredValueMc;
        stored.timestamp = declaredTimestamp;
        stored.location = EXPECTED_LOCATION;
        stored.measurementType = EXPECTED_MEASUREMENT_TYPE;

        emit MeasurementSubmitted(
            EXPECTED_LOCATION, EXPECTED_MEASUREMENT_TYPE, declaredValueMc, declaredTimestamp, msg.sender
        );
    }

    /*//////////////////////////////////////////////////////////////
                                 VIEWS
    //////////////////////////////////////////////////////////////*/

    /// @inheritdoc IWeatherSource
    function getLatest(
        bytes32 location,
        bytes32 measurementType
    ) external view returns (Measurement memory) {
        Measurement memory m = _latest[_storageKey(location, measurementType)];
        if (m.timestamp == 0) revert NoMeasurement(location, measurementType);
        return m;
    }

    /// @notice Returns true if `proof` has already been consumed by a previous
    ///         successful submission. Off-chain keepers can use this to skip
    ///         re-submitting an identical proof.
    function isProofConsumed(
        IReclaim.Proof calldata proof
    ) external view returns (bool) {
        return _consumedProofs[keccak256(abi.encode(proof))];
    }

    /*//////////////////////////////////////////////////////////////
                               INTERNAL
    //////////////////////////////////////////////////////////////*/

    function _storageKey(
        bytes32 location,
        bytes32 measurementType
    ) internal pure returns (bytes32) {
        return keccak256(abi.encode(location, measurementType));
    }
}
