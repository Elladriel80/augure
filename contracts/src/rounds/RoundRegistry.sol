// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

import {IAugPocToken} from "../interfaces/IAugPocToken.sol";
import {IRoundRegistry} from "../interfaces/IRoundRegistry.sol";
import {MonthlyMintCap} from "./MonthlyMintCap.sol";

/// @title  RoundRegistry — on-chain lifecycle for the Augure monthly mint rounds
/// @notice Implements the propose / challenge / execute / cancel state machine described
///         in `contracts/docs/ROUND-LIFECYCLE.md` and white paper §7.3. The registry holds
///         no funds; on `executeRound` it instructs `AugPocToken` to mint to ratified
///         beneficiaries, gated by `MonthlyMintCap`'s 10% monthly cap.
///
/// @dev    Storage of the `supplyAtMonthStart` snapshot is lazy: the very first executeRound
///         in a given UTC calendar month captures `token.totalSupply()` BEFORE minting and
///         freezes that value as the cap reference for the rest of the month. Subsequent
///         rounds in the same month all measure their cumulative impact against that single
///         snapshot, regardless of how much supply has actually grown by the time they run.
///
///         Genesis behaviour: when `supplyAtMonthStart == 0` (snapshot taken on a month with
///         empty supply), `MonthlyMintCap.isMintAdmissible` returns true for every amount,
///         so the entire genesis month is unconstrained. The next month picks up a non-zero
///         snapshot and the 10% cap applies normally from then on.
contract RoundRegistry is AccessControl, ReentrancyGuard, IRoundRegistry {
    using MonthlyMintCap for uint256;

    /*//////////////////////////////////////////////////////////////
                                 ROLES
    //////////////////////////////////////////////////////////////*/

    bytes32 public constant ROUND_PROPOSER_ROLE = keccak256("ROUND_PROPOSER_ROLE");
    bytes32 public constant ROUND_EXECUTOR_ROLE = keccak256("ROUND_EXECUTOR_ROLE");
    bytes32 public constant ROUND_CANCELLER_ROLE = keccak256("ROUND_CANCELLER_ROLE");

    /*//////////////////////////////////////////////////////////////
                              CONSTANTS
    //////////////////////////////////////////////////////////////*/

    uint32 public constant MIN_CHALLENGE_WINDOW_DAYS = 1;
    uint32 public constant MAX_CHALLENGE_WINDOW_DAYS = 365;

    /*//////////////////////////////////////////////////////////////
                               STORAGE
    //////////////////////////////////////////////////////////////*/

    /// @notice The AUG-POC token the registry mints into. Immutable for the registry's lifetime.
    IAugPocToken public immutable token;

    struct Round {
        string ipfsUri;
        uint64 proposedAt;
        uint32 challengeWindowDays;
        RoundStatus status;
        address[] beneficiaries;
        uint256[] amounts;
    }

    mapping(bytes32 => Round) private _rounds;
    mapping(uint256 => uint256) private _supplyAtMonthStart;
    mapping(uint256 => uint256) private _mintedInMonth;
    mapping(uint256 => bool) private _supplySnapshotted;

    /*//////////////////////////////////////////////////////////////
                              CONSTRUCTOR
    //////////////////////////////////////////////////////////////*/

    constructor(
        address admin,
        IAugPocToken token_
    ) {
        if (admin == address(0)) revert ZeroAddressAdmin();
        if (address(token_) == address(0)) revert ZeroAddressToken();
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        token = token_;
    }

    /*//////////////////////////////////////////////////////////////
                             LIFECYCLE
    //////////////////////////////////////////////////////////////*/

    /// @inheritdoc IRoundRegistry
    function proposeRound(
        bytes32 roundHash,
        address[] calldata beneficiaries,
        uint256[] calldata amounts,
        string calldata ipfsUri,
        uint32 challengeWindowDays
    ) external onlyRole(ROUND_PROPOSER_ROLE) {
        if (beneficiaries.length == 0) revert EmptyBeneficiaries();
        if (beneficiaries.length != amounts.length) revert MismatchedArrays();
        if (challengeWindowDays < MIN_CHALLENGE_WINDOW_DAYS || challengeWindowDays > MAX_CHALLENGE_WINDOW_DAYS) {
            revert InvalidChallengeWindow();
        }

        bytes32 expectedHash = keccak256(abi.encode(beneficiaries, amounts, ipfsUri));
        if (roundHash != expectedHash) revert InvalidRoundHash();

        if (_rounds[roundHash].proposedAt != 0) revert RoundAlreadyExists();

        for (uint256 i = 0; i < beneficiaries.length; i++) {
            if (beneficiaries[i] == address(0)) revert ZeroBeneficiary(i);
            if (amounts[i] == 0) revert ZeroAmount(i);
        }

        Round storage r = _rounds[roundHash];
        r.ipfsUri = ipfsUri;
        r.proposedAt = uint64(block.timestamp);
        r.challengeWindowDays = challengeWindowDays;
        r.status = RoundStatus.Proposed;
        r.beneficiaries = beneficiaries;
        r.amounts = amounts;

        emit RoundProposed(roundHash, ipfsUri, uint64(block.timestamp), challengeWindowDays, beneficiaries, amounts);
    }

    /// @inheritdoc IRoundRegistry
    function challengeRound(
        bytes32 roundHash,
        string calldata reasonIpfsUri
    ) external {
        Round storage r = _rounds[roundHash];
        if (r.status != RoundStatus.Proposed) revert RoundNotProposed();
        if (block.timestamp >= _windowEnd(r)) revert ChallengeWindowExpired();

        r.status = RoundStatus.Challenged;
        emit RoundChallenged(roundHash, msg.sender, reasonIpfsUri);
    }

    /// @inheritdoc IRoundRegistry
    function executeRound(
        bytes32 roundHash
    ) external onlyRole(ROUND_EXECUTOR_ROLE) nonReentrant {
        Round storage r = _rounds[roundHash];
        if (r.status != RoundStatus.Proposed && r.status != RoundStatus.Challenged) {
            revert RoundNotProposedOrChallenged();
        }
        if (block.timestamp < _windowEnd(r)) revert ChallengeWindowNotExpired();

        uint256 monthId = MonthlyMintCap.monthIdOf(block.timestamp);

        if (!_supplySnapshotted[monthId]) {
            _supplyAtMonthStart[monthId] = token.totalSupply();
            _supplySnapshotted[monthId] = true;
        }

        uint256 totalMint;
        for (uint256 i = 0; i < r.amounts.length; i++) {
            totalMint += r.amounts[i];
        }

        uint256 supplyRef = _supplyAtMonthStart[monthId];
        uint256 alreadyMinted = _mintedInMonth[monthId];
        if (!MonthlyMintCap.isMintAdmissible(supplyRef, alreadyMinted, totalMint)) {
            revert MonthlyCapExceeded({
                monthId: monthId,
                cap: MonthlyMintCap.capFor(supplyRef),
                alreadyMinted: alreadyMinted,
                requested: totalMint
            });
        }

        _mintedInMonth[monthId] = alreadyMinted + totalMint;
        r.status = RoundStatus.Executed;

        // Effects → Interactions: every state change (status, mintedInMonth) is committed
        // BEFORE any mint call. Token.mint() in OpenZeppelin v5 does not call back into the
        // recipient, so reentrancy is structurally impossible; nonReentrant is defense-in-depth.
        for (uint256 i = 0; i < r.beneficiaries.length; i++) {
            token.mint(r.beneficiaries[i], r.amounts[i]);
        }

        emit RoundExecuted(roundHash, uint64(block.timestamp), totalMint);
    }

    /// @inheritdoc IRoundRegistry
    function cancelRound(
        bytes32 roundHash,
        string calldata reasonIpfsUri
    ) external onlyRole(ROUND_CANCELLER_ROLE) {
        Round storage r = _rounds[roundHash];
        if (r.status != RoundStatus.Proposed && r.status != RoundStatus.Challenged) {
            revert RoundNotCancellable();
        }
        r.status = RoundStatus.Cancelled;
        emit RoundCancelled(roundHash, msg.sender, reasonIpfsUri);
    }

    /*//////////////////////////////////////////////////////////////
                                VIEWS
    //////////////////////////////////////////////////////////////*/

    /// @inheritdoc IRoundRegistry
    function statusOf(
        bytes32 roundHash
    ) external view returns (RoundStatus) {
        return _rounds[roundHash].status;
    }

    /// @inheritdoc IRoundRegistry
    function supplyAtMonthStart(
        uint256 monthId
    ) external view returns (uint256) {
        return _supplyAtMonthStart[monthId];
    }

    /// @inheritdoc IRoundRegistry
    function mintedInMonth(
        uint256 monthId
    ) external view returns (uint256) {
        return _mintedInMonth[monthId];
    }

    /// @notice Returns the round's static fields (ipfsUri, proposedAt, challengeWindowDays,
    ///         status). Use `getRoundBeneficiaries` and `getRoundAmounts` for the arrays.
    function getRound(
        bytes32 roundHash
    ) external view returns (string memory ipfsUri, uint64 proposedAt, uint32 challengeWindowDays, RoundStatus status) {
        Round storage r = _rounds[roundHash];
        return (r.ipfsUri, r.proposedAt, r.challengeWindowDays, r.status);
    }

    /// @notice Returns the beneficiaries array of a round.
    function getRoundBeneficiaries(
        bytes32 roundHash
    ) external view returns (address[] memory) {
        return _rounds[roundHash].beneficiaries;
    }

    /// @notice Returns the amounts array of a round.
    function getRoundAmounts(
        bytes32 roundHash
    ) external view returns (uint256[] memory) {
        return _rounds[roundHash].amounts;
    }

    /// @notice Convenience: timestamp at which the challenge window closes (`proposedAt +
    ///         challengeWindowDays * 1 days`). Returns 0 for an unknown round.
    function windowEndOf(
        bytes32 roundHash
    ) external view returns (uint256) {
        Round storage r = _rounds[roundHash];
        if (r.proposedAt == 0) return 0;
        return _windowEnd(r);
    }

    /*//////////////////////////////////////////////////////////////
                              INTERNAL
    //////////////////////////////////////////////////////////////*/

    function _windowEnd(
        Round storage r
    ) private view returns (uint256) {
        return uint256(r.proposedAt) + uint256(r.challengeWindowDays) * 1 days;
    }
}
