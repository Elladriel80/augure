// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

/// @title  IReclaim — minimal interface of the official Reclaim verifier contract
/// @notice Mirrors the public surface of `reclaimprotocol/reclaim-solidity-sdk`'s
///         `Reclaim.sol` that Aratea actually consumes. Kept intentionally minimal:
///         only the structs and the single `verifyProof` entry point are declared.
///         The full Reclaim contract exposes many more functions (epoch admin, dapp
///         registration, context parsing) that are not needed by ReclaimWeatherSource.
/// @dev    Deployed addresses (per docs.reclaimprotocol.org/onchain/solidity/supported-networks,
///         retrieved 2026-05-16):
///         - Arbitrum One:     0x9F0472FD02Ca1BC2d6C3A1702803Ba822C7C7E91
///         - Arbitrum Sepolia: 0x4D1ee04EB5CeE02d4C123d4b67a86bDc7cA2E62A
interface IReclaim {
    /*//////////////////////////////////////////////////////////////
                                  TYPES
    //////////////////////////////////////////////////////////////*/

    /// @dev Mirror of Claims.CompleteClaimData
    struct CompleteClaimData {
        bytes32 identifier;
        address owner;
        uint32 timestampS;
        uint32 epoch;
    }

    /// @dev Mirror of Claims.ClaimInfo. `parameters` and `context` are JSON strings
    ///      produced by the off-chain Reclaim SDK; the on-chain verifier only checks
    ///      that the hash of this struct matches the signed claim identifier.
    struct ClaimInfo {
        string provider;
        string parameters;
        string context;
    }

    /// @dev Mirror of Claims.SignedClaim
    struct SignedClaim {
        CompleteClaimData claim;
        bytes[] signatures;
    }

    /// @dev Mirror of Reclaim.Proof
    struct Proof {
        ClaimInfo claimInfo;
        SignedClaim signedClaim;
    }

    /*//////////////////////////////////////////////////////////////
                                FUNCTIONS
    //////////////////////////////////////////////////////////////*/

    /// @notice Asserts the cryptographic validity of a Reclaim proof. Reverts on invalid.
    /// @dev    Declared without a return value on purpose. The upstream contract is
    ///         declared `returns (bool)` but the version deployed on Arbitrum Sepolia
    ///         (`0x4D1ee04EB5CeE02d4C123d4b67a86bDc7cA2E62A`, impl `0x7bc540...`) has an
    ///         incomplete implementation: it runs every `require()` check correctly but
    ///         omits the final `return true;`, so it always returns the default `false`
    ///         even on the success path. Treating the bool as authoritative therefore
    ///         rejects valid proofs.
    ///
    ///         Truth source we rely on instead: if the call DOES NOT revert, every
    ///         `require()` inside `verifyProof` passed (signature count, identifier hash,
    ///         witness whitelist), which is what we actually need. Omitting the
    ///         `returns (bool)` from this interface lets the Solidity compiler emit a
    ///         plain external call that ignores any return data — forward-compatible
    ///         with both the current broken implementation and any future fixed one.
    ///
    ///         Not `view`: implementation is plain `public`, callers should budget gas.
    function verifyProof(
        Proof memory proof
    ) external;
}
