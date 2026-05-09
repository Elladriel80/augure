// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

/// @title  IRoundRegistry — external interface of RoundRegistry
/// @notice The on-chain anchor point for the monthly mint rounds described in white paper §7.3.
///         Each round is committed under a `roundHash` derived off-chain, traverses a
///         lifecycle (Proposed → Challenged? → Executed | Cancelled), and on execution
///         mints AUG-POC tokens to ratified beneficiaries within the 10% monthly cap.
interface IRoundRegistry {
    /*//////////////////////////////////////////////////////////////
                                  TYPES
    //////////////////////////////////////////////////////////////*/

    enum RoundStatus {
        None,
        Proposed,
        Challenged,
        Executed,
        Cancelled
    }

    /*//////////////////////////////////////////////////////////////
                                 EVENTS
    //////////////////////////////////////////////////////////////*/

    /// @notice Emitted when a new round is committed by the proposer (a Safe multisig).
    event RoundProposed(
        bytes32 indexed roundHash,
        string ipfsUri,
        uint64 proposedAt,
        uint32 challengeWindowDays,
        address[] beneficiaries,
        uint256[] amounts
    );

    /// @notice Emitted when anyone formally challenges a Proposed round during its window.
    event RoundChallenged(bytes32 indexed roundHash, address indexed challenger, string reasonIpfsUri);

    /// @notice Emitted when a round is executed: tokens have been minted to all beneficiaries
    ///         and the round is permanently sealed in the `Executed` state.
    event RoundExecuted(bytes32 indexed roundHash, uint64 executedAt, uint256 totalMinted);

    /// @notice Emitted when a round is cancelled by the canceller role (the Safe multisig).
    event RoundCancelled(bytes32 indexed roundHash, address indexed canceller, string reasonIpfsUri);

    /*//////////////////////////////////////////////////////////////
                                ERRORS
    //////////////////////////////////////////////////////////////*/

    error ZeroAddressAdmin();
    error ZeroAddressToken();
    error InvalidRoundHash();
    error RoundAlreadyExists();
    error MismatchedArrays();
    error EmptyBeneficiaries();
    error ZeroAmount(uint256 index);
    error ZeroBeneficiary(uint256 index);
    error InvalidChallengeWindow();
    error RoundNotProposedOrChallenged();
    error RoundNotProposed();
    error RoundNotCancellable();
    error ChallengeWindowNotExpired();
    error ChallengeWindowExpired();
    error MonthlyCapExceeded(uint256 monthId, uint256 cap, uint256 alreadyMinted, uint256 requested);

    /*//////////////////////////////////////////////////////////////
                              FUNCTIONS
    //////////////////////////////////////////////////////////////*/

    /// @notice Propose a new round committed under `roundHash`. The hash is computed
    ///         off-chain as `keccak256(abi.encode(beneficiaries, amounts, ipfsUri))` and
    ///         must match a re-computation from the on-chain inputs.
    /// @dev    Caller must hold ROUND_PROPOSER_ROLE (the Safe multisig).
    function proposeRound(
        bytes32 roundHash,
        address[] calldata beneficiaries,
        uint256[] calldata amounts,
        string calldata ipfsUri,
        uint32 challengeWindowDays
    ) external;

    /// @notice File a formal challenge against a Proposed round during its challenge window.
    ///         The off-chain panel resolves the challenge: if upheld, the Safe calls
    ///         `cancelRound`; if dismissed, the Safe lets the window expire and calls
    ///         `executeRound`.
    /// @dev    Public — anyone can challenge.
    function challengeRound(
        bytes32 roundHash,
        string calldata reasonIpfsUri
    ) external;

    /// @notice Execute a round whose challenge window has expired. Mints tokens to every
    ///         beneficiary, enforces the 10% monthly cap, marks the round Executed.
    /// @dev    Caller must hold ROUND_EXECUTOR_ROLE (the Safe multisig).
    function executeRound(
        bytes32 roundHash
    ) external;

    /// @notice Cancel a Proposed or Challenged round. Permanent — once cancelled the round
    ///         can never be revived.
    /// @dev    Caller must hold ROUND_CANCELLER_ROLE (the Safe multisig).
    function cancelRound(
        bytes32 roundHash,
        string calldata reasonIpfsUri
    ) external;

    /*//////////////////////////////////////////////////////////////
                                 VIEWS
    //////////////////////////////////////////////////////////////*/

    /// @notice Returns the current status of a round.
    function statusOf(
        bytes32 roundHash
    ) external view returns (RoundStatus);

    /// @notice Returns the snapshot of total supply at the start of `monthId`, or 0 if
    ///         no round has ever executed in that month.
    function supplyAtMonthStart(
        uint256 monthId
    ) external view returns (uint256);

    /// @notice Returns the cumulative amount minted in `monthId` across all executed rounds.
    function mintedInMonth(
        uint256 monthId
    ) external view returns (uint256);
}
