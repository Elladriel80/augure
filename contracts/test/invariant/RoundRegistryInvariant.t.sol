// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {Test} from "forge-std/Test.sol";
import {StdInvariant} from "forge-std/StdInvariant.sol";

import {AugPocToken} from "../../src/token/AugPocToken.sol";
import {RoundRegistry} from "../../src/rounds/RoundRegistry.sol";
import {IAugPocToken} from "../../src/interfaces/IAugPocToken.sol";
import {IRoundRegistry} from "../../src/interfaces/IRoundRegistry.sol";
import {MonthlyMintCap} from "../../src/rounds/MonthlyMintCap.sol";

/// @title  RoundRegistryHandler — bounded harness for the invariant runner
/// @notice Drives a sequence of (propose, challenge, execute, cancel, advance-time) calls and
///         tracks ghost variables that the invariant test contract reads to assert global
///         properties.
contract RoundRegistryHandler is Test {
    AugPocToken public immutable token;
    RoundRegistry public immutable registry;
    address public immutable proposer;
    address public immutable executor;
    address public immutable canceller;

    bytes32[] public proposedHashes;
    mapping(bytes32 => bool) public hashSeen;

    address[] internal beneficiaries;

    uint256 public ghost_totalExecutedAmount;
    mapping(uint256 => uint256) public ghost_executedAmountInMonth;

    uint256 internal nonce;

    constructor(
        AugPocToken _token,
        RoundRegistry _registry,
        address _proposer,
        address _executor,
        address _canceller
    ) {
        token = _token;
        registry = _registry;
        proposer = _proposer;
        executor = _executor;
        canceller = _canceller;

        beneficiaries.push(makeAddr("ben1"));
        beneficiaries.push(makeAddr("ben2"));
        beneficiaries.push(makeAddr("ben3"));
    }

    function _pickBen(
        uint256 seed
    ) internal view returns (address) {
        return beneficiaries[seed % beneficiaries.length];
    }

    function propose(
        uint256 seed,
        uint96 amount
    ) public {
        amount = uint96(bound(amount, 1, 100_000e18));

        address[] memory bens = new address[](1);
        bens[0] = _pickBen(seed);
        uint256[] memory amts = new uint256[](1);
        amts[0] = amount;

        nonce += 1;
        string memory uri = string(abi.encodePacked("ipfs://invariant-", vm.toString(nonce)));
        bytes32 h = keccak256(abi.encode(bens, amts, uri));
        if (hashSeen[h]) return; // never duplicate

        vm.prank(proposer);
        try registry.proposeRound(h, bens, amts, uri, 7) {
            hashSeen[h] = true;
            proposedHashes.push(h);
        } catch { /* benign — bound violation */ }
    }

    function challenge(
        uint256 idx
    ) public {
        if (proposedHashes.length == 0) return;
        bytes32 h = proposedHashes[idx % proposedHashes.length];
        if (registry.statusOf(h) != IRoundRegistry.RoundStatus.Proposed) return;
        if (block.timestamp >= registry.windowEndOf(h)) return;
        registry.challengeRound(h, "ipfs://x");
    }

    function executeR(
        uint256 idx
    ) public {
        if (proposedHashes.length == 0) return;
        bytes32 h = proposedHashes[idx % proposedHashes.length];
        IRoundRegistry.RoundStatus st = registry.statusOf(h);
        if (st != IRoundRegistry.RoundStatus.Proposed && st != IRoundRegistry.RoundStatus.Challenged) return;
        if (block.timestamp < registry.windowEndOf(h)) return;

        uint256[] memory amts = registry.getRoundAmounts(h);
        uint256 total;
        for (uint256 i = 0; i < amts.length; i++) {
            total += amts[i];
        }

        // Pre-compute admissibility under the same rules the contract enforces, so we know
        // whether to expect success or revert. Mirror the lazy snapshot logic.
        uint256 monthId = MonthlyMintCap.monthIdOf(block.timestamp);
        uint256 supplyRef = registry.supplyAtMonthStart(monthId);
        uint256 alreadyMinted = registry.mintedInMonth(monthId);

        // If snapshot not taken yet, the snapshot will be the current totalSupply.
        bool snapshotTaken = (supplyRef != 0 || alreadyMinted != 0);
        if (!snapshotTaken) supplyRef = token.totalSupply();

        bool admissible = MonthlyMintCap.isMintAdmissible(supplyRef, alreadyMinted, total);

        vm.prank(executor);
        if (admissible) {
            registry.executeRound(h);
            ghost_totalExecutedAmount += total;
            ghost_executedAmountInMonth[monthId] += total;
        } else {
            try registry.executeRound(h) { /* unexpected */ } catch { /* expected revert */ }
        }
    }

    function cancel(
        uint256 idx
    ) public {
        if (proposedHashes.length == 0) return;
        bytes32 h = proposedHashes[idx % proposedHashes.length];
        IRoundRegistry.RoundStatus st = registry.statusOf(h);
        if (st != IRoundRegistry.RoundStatus.Proposed && st != IRoundRegistry.RoundStatus.Challenged) return;
        vm.prank(canceller);
        registry.cancelRound(h, "ipfs://x");
    }

    function advanceTime(
        uint64 seconds_
    ) public {
        seconds_ = uint64(bound(uint256(seconds_), 1, 30 days));
        skip(seconds_);
    }

    function proposedCount() external view returns (uint256) {
        return proposedHashes.length;
    }
}

/// @title  RoundRegistryInvariantTest — global properties of RoundRegistry
contract RoundRegistryInvariantTest is StdInvariant, Test {
    AugPocToken internal token;
    RoundRegistry internal registry;
    RoundRegistryHandler internal handler;

    address internal admin = makeAddr("inv-admin");
    address internal proposer = makeAddr("inv-proposer");
    address internal executor = makeAddr("inv-executor");
    address internal canceller = makeAddr("inv-canceller");

    function setUp() public {
        token = new AugPocToken(admin);
        registry = new RoundRegistry(admin, IAugPocToken(address(token)));

        bytes32 minterRole = token.MINTER_ROLE();
        bytes32 proposerRole = registry.ROUND_PROPOSER_ROLE();
        bytes32 executorRole = registry.ROUND_EXECUTOR_ROLE();
        bytes32 cancellerRole = registry.ROUND_CANCELLER_ROLE();

        vm.startPrank(admin);
        token.grantRole(minterRole, address(registry));
        registry.grantRole(proposerRole, proposer);
        registry.grantRole(executorRole, executor);
        registry.grantRole(cancellerRole, canceller);
        vm.stopPrank();

        vm.warp(1_778_544_000); // 2026-05-09 UTC

        handler = new RoundRegistryHandler(token, registry, proposer, executor, canceller);
        targetContract(address(handler));

        bytes4[] memory selectors = new bytes4[](5);
        selectors[0] = RoundRegistryHandler.propose.selector;
        selectors[1] = RoundRegistryHandler.challenge.selector;
        selectors[2] = RoundRegistryHandler.executeR.selector;
        selectors[3] = RoundRegistryHandler.cancel.selector;
        selectors[4] = RoundRegistryHandler.advanceTime.selector;
        targetSelector(FuzzSelector({addr: address(handler), selectors: selectors}));
    }

    /// @dev token.totalSupply() == sum of executed mint amounts tracked off-chain.
    function invariant_TotalSupplyMatchesExecutedSum() public view {
        assertEq(token.totalSupply(), handler.ghost_totalExecutedAmount());
    }

    /// @dev MINTER_ROLE is never granted to anyone other than the registry itself.
    function invariant_RegistryIsSoleMinter() public view {
        assertTrue(token.hasRole(token.MINTER_ROLE(), address(registry)));
        assertFalse(token.hasRole(token.MINTER_ROLE(), proposer));
        assertFalse(token.hasRole(token.MINTER_ROLE(), executor));
        assertFalse(token.hasRole(token.MINTER_ROLE(), canceller));
        assertFalse(token.hasRole(token.MINTER_ROLE(), admin));
    }

    /// @dev For every month with a snapshot taken, mintedInMonth ≤ cap unless the snapshot
    ///      was zero (genesis exception) — in which case any total is allowed.
    function invariant_PerMonthCapHolds() public view {
        // Probe a window of months around the current block.timestamp.
        uint256 nowMonthId = MonthlyMintCap.monthIdOf(block.timestamp);
        for (uint256 i = 0; i <= 24; i++) {
            uint256 monthId = nowMonthId - 12 + i;
            uint256 supplyRef = registry.supplyAtMonthStart(monthId);
            uint256 minted = registry.mintedInMonth(monthId);
            if (supplyRef == 0) continue; // genesis or untouched month
            uint256 cap = (supplyRef * 1000) / 10_000;
            assertLe(minted, cap);
        }
    }

    /// @dev Per-handler ghost: the total recorded by the handler equals registry's notion of
    ///      mintedInMonth across all visited months.
    function invariant_HandlerGhostMatchesContract() public view {
        uint256 nowMonthId = MonthlyMintCap.monthIdOf(block.timestamp);
        for (uint256 i = 0; i <= 24; i++) {
            uint256 monthId = nowMonthId - 12 + i;
            assertEq(handler.ghost_executedAmountInMonth(monthId), registry.mintedInMonth(monthId));
        }
    }
}
