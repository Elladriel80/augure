// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {IReclaim} from "../../src/interfaces/IReclaim.sol";

/// @title  MockReclaimVerifier — test double for the Reclaim verifier
/// @notice Used exclusively in Foundry tests. Production tests against the real Reclaim
///         contract require a live attestor and a freshly-generated proof; that is the
///         keeper's job (PR 2) and is exercised end-to-end on Arbitrum Sepolia, not in
///         Foundry CI.
/// @dev    Behaviour is controllable per-test:
///         - `setNextVerdict(true)`  : next verifyProof() returns true
///         - `setNextVerdict(false)` : next verifyProof() returns false
///         - `setShouldRevert(true)` : next verifyProof() reverts with MockRevert()
///         - `setShouldReenter(target, encodedSubmission)` : next verifyProof() calls
///           submitMeasurement on `target` BEFORE returning. Used to assert that the
///           ReentrancyGuard on the source contract holds.
///         Verdict/revert/reenter are sticky until explicitly reset.
contract MockReclaimVerifier is IReclaim {
    bool public nextVerdict = true;
    bool public shouldRevert;

    address public reentrancyTarget;
    bytes public reentrancyPayload;

    uint256 public verifyProofCallCount;

    error MockRevert();

    function setNextVerdict(
        bool verdict
    ) external {
        nextVerdict = verdict;
    }

    function setShouldRevert(
        bool revertOnCall
    ) external {
        shouldRevert = revertOnCall;
    }

    function setShouldReenter(
        address target,
        bytes calldata encodedSubmission
    ) external {
        reentrancyTarget = target;
        reentrancyPayload = encodedSubmission;
    }

    function clearReentrancy() external {
        reentrancyTarget = address(0);
        delete reentrancyPayload;
    }

    /// @inheritdoc IReclaim
    function verifyProof(
        IReclaim.Proof memory /* proof */
    ) external returns (bool) {
        verifyProofCallCount += 1;

        if (reentrancyTarget != address(0)) {
            // Best-effort reentrancy attempt; the source contract should revert with
            // ReentrancyGuardReentrantCall, which we let propagate to the test.
            (bool ok, bytes memory ret) =
                reentrancyTarget.call(abi.encodeWithSignature("submitMeasurement(bytes)", reentrancyPayload));
            if (!ok) {
                // Bubble the inner revert so the test can assert on it.
                assembly {
                    revert(add(ret, 0x20), mload(ret))
                }
            }
        }

        if (shouldRevert) revert MockRevert();
        return nextVerdict;
    }
}
