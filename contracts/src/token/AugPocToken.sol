// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {ERC20Permit} from "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";
import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";

/// @title  AugPocToken — Augure Phase 1 labor-value token (AUG-POC)
/// @notice ERC-20 token representing the labor-value pool of the Augure protocol during Phase 1.
///         Issuance is regulated externally by RoundRegistry (M3), which holds MINTER_ROLE and
///         enforces the 10% monthly cap derived from circulating supply.
/// @dev    18 decimals (Ethereum standard). The "1 sat = 1 token" convention is imposed at mint
///         time by the agent that values contributions in sats: RoundRegistry calls mint() with
///         `amount = sats * 10^18`. The decimal count is independent of the convention.
///
///         Roles (all governed by DEFAULT_ADMIN_ROLE):
///           - DEFAULT_ADMIN_ROLE : grants and revokes the other roles
///           - MINTER_ROLE        : issues new tokens (granted to RoundRegistry at deploy)
///           - PAUSER_ROLE        : pauses/unpauses user-to-user transfers
///           - BURNER_ROLE        : burns existing tokens; reserved for the future AugConverter
///                                  contract that will execute AUG-POC → AUG conversion at the
///                                  Phase 2 DAO launch (see white paper §7.2). NOT granted at
///                                  deploy — granted later by admin vote.
///
///         Pause semantics: pause blocks user-to-user transfers only. Mint and burn paths remain
///         operational so an in-flight round execution or a critical conversion cannot be frozen
///         by a defensive pause. See contracts/docs/SECURITY.md §5.5.
contract AugPocToken is ERC20, ERC20Permit, AccessControl, Pausable {
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");
    bytes32 public constant BURNER_ROLE = keccak256("BURNER_ROLE");

    error ZeroAddressAdmin();

    /// @param admin Address that will hold DEFAULT_ADMIN_ROLE. On mainnet this MUST be a Safe
    ///              multisig with threshold M ≥ 2 (per contracts/docs/SECURITY.md). On Sepolia
    ///              testnet, an EOA is acceptable while iterating.
    constructor(
        address admin
    ) ERC20("Augure POC Token", "AUG-POC") ERC20Permit("Augure POC Token") {
        if (admin == address(0)) revert ZeroAddressAdmin();
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
    }

    /// @notice Mint `amount` tokens to `to`. Restricted to MINTER_ROLE.
    /// @dev    No cap is enforced here — the caller (RoundRegistry on mainnet) is responsible for
    ///         enforcing the 10% monthly cap. Mint is intentionally NOT blocked by pause.
    function mint(
        address to,
        uint256 amount
    ) external onlyRole(MINTER_ROLE) {
        _mint(to, amount);
    }

    /// @notice Burn `amount` tokens from `from`. Restricted to BURNER_ROLE.
    /// @dev    Caller must have an ERC-20 allowance from `from` for at least `amount`. The
    ///         allowance is decreased by the burned amount (same semantics as
    ///         OpenZeppelin's ERC20Burnable.burnFrom). Burn is intentionally NOT blocked by pause.
    function burnFrom(
        address from,
        uint256 amount
    ) external onlyRole(BURNER_ROLE) {
        _spendAllowance(from, _msgSender(), amount);
        _burn(from, amount);
    }

    /// @notice Pause user-to-user transfers. Mint and burn remain operational.
    function pause() external onlyRole(PAUSER_ROLE) {
        _pause();
    }

    /// @notice Resume user-to-user transfers.
    function unpause() external onlyRole(PAUSER_ROLE) {
        _unpause();
    }

    /// @dev Override ERC20._update to enforce pause on user-to-user transfers only.
    ///      Mint paths (from == address(0)) and burn paths (to == address(0)) bypass the pause
    ///      check intentionally — see SECURITY.md §5.5 and the natspec on this contract.
    function _update(
        address from,
        address to,
        uint256 value
    ) internal override {
        if (from != address(0) && to != address(0)) {
            _requireNotPaused();
        }
        super._update(from, to, value);
    }
}
