// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

/// @title IRoundRegistry — placeholder interface (Phase 1 / Milestone M3 will fill this in)
/// @notice Real interface arrives in M3.
interface IRoundRegistry {
    enum RoundStatus {
        None,
        Proposed,
        Challenged,
        Executed,
        Cancelled
    }
}
