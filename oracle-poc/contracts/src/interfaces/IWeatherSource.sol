// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

/// @title  IWeatherSource — Aratea weather oracle source interface
/// @notice Common interface every on-chain weather source must implement. Designed
///         to be the lone integration surface consumed by the Phase 2 OracleAggregator
///         (whitepaper v0.5 §5, Couche B), so multiple sources (Reclaim, Chainlink,
///         WeatherXM, native attestors) can be swapped behind it.
/// @dev    POC scope is single-station, single-measurement-type. The interface is
///         already generic (location + type are first-class) so a multi-station
///         aggregator can plug in without an interface change.
interface IWeatherSource {
    /*//////////////////////////////////////////////////////////////
                                  TYPES
    //////////////////////////////////////////////////////////////*/

    /// @notice A single weather observation, post-verification.
    /// @dev    `value` is stored in milliCelsius (mC). A value of -50_000 means -50.000 C,
    ///         +60_000 means +60.000 C. int256 gives unbounded headroom for future units.
    ///         `timestamp` is the unix time the measurement was taken (per the upstream
    ///         agency), NOT the time the proof was submitted on-chain.
    struct Measurement {
        int256 value;
        uint64 timestamp;
        bytes32 location;
        bytes32 measurementType;
    }

    /*//////////////////////////////////////////////////////////////
                                 EVENTS
    //////////////////////////////////////////////////////////////*/

    /// @notice Emitted on every successful submission. The submitter is the EOA/contract
    ///         that paid the gas, not a cryptographic attestor — authority comes from the
    ///         underlying proof (e.g. Reclaim), not from msg.sender.
    event MeasurementSubmitted(
        bytes32 indexed location,
        bytes32 indexed measurementType,
        int256 value,
        uint64 timestamp,
        address indexed submitter
    );

    /*//////////////////////////////////////////////////////////////
                                ERRORS
    //////////////////////////////////////////////////////////////*/

    error NoMeasurement(bytes32 location, bytes32 measurementType);

    /*//////////////////////////////////////////////////////////////
                              FUNCTIONS
    //////////////////////////////////////////////////////////////*/

    /// @notice Submit a verified measurement extracted from a source-specific proof.
    /// @dev    Each implementation defines its own encoding for `encodedSubmission`
    ///         (Reclaim proof + declared value/timestamp for ReclaimWeatherSource,
    ///         a Chainlink round answer for ChainlinkWeatherSource, etc.).
    ///         Reverts on any validation failure; success path emits MeasurementSubmitted.
    function submitMeasurement(
        bytes calldata encodedSubmission
    ) external;

    /// @notice Read the latest stored measurement for a (location, type) pair.
    /// @dev    Reverts with NoMeasurement if no submission has ever been stored.
    function getLatest(
        bytes32 location,
        bytes32 measurementType
    ) external view returns (Measurement memory);
}
