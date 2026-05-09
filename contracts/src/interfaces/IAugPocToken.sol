// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {IERC20Permit} from "@openzeppelin/contracts/token/ERC20/extensions/IERC20Permit.sol";
import {IAccessControl} from "@openzeppelin/contracts/access/IAccessControl.sol";

/// @title  IAugPocToken — minimal external interface of AugPocToken
/// @notice External shape RoundRegistry (M3) and the future AugConverter (Phase 2) depend on.
///         Inherits standard interfaces so consumers can target either via this single import.
interface IAugPocToken is IERC20, IERC20Permit, IAccessControl {
    /// @notice Returns the keccak256 hash of "MINTER_ROLE".
    function MINTER_ROLE() external view returns (bytes32);

    /// @notice Returns the keccak256 hash of "PAUSER_ROLE".
    function PAUSER_ROLE() external view returns (bytes32);

    /// @notice Returns the keccak256 hash of "BURNER_ROLE".
    function BURNER_ROLE() external view returns (bytes32);

    /// @notice Mints `amount` tokens to `to`. Caller must hold MINTER_ROLE.
    function mint(
        address to,
        uint256 amount
    ) external;

    /// @notice Burns `amount` tokens from `from`, consuming the caller's ERC-20 allowance.
    ///         Caller must hold BURNER_ROLE.
    function burnFrom(
        address from,
        uint256 amount
    ) external;

    /// @notice Pauses user-to-user transfers (mint and burn remain operational).
    ///         Caller must hold PAUSER_ROLE.
    function pause() external;

    /// @notice Resumes user-to-user transfers. Caller must hold PAUSER_ROLE.
    function unpause() external;

    /// @notice Returns true if user-to-user transfers are currently paused.
    function paused() external view returns (bool);
}
