// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {Test} from "forge-std/Test.sol";
import {StdInvariant} from "forge-std/StdInvariant.sol";

import {AugPocToken} from "../../src/token/AugPocToken.sol";

/// @title  AugPocTokenHandler — invariant fuzzing harness for AugPocToken
/// @notice Wraps every external action a privileged actor can perform on the token, plus the
///         user-level transfer/approve calls. Each action records ghost variables that the
///         invariant test contract reads to assert global properties.
contract AugPocTokenHandler is Test {
    AugPocToken public immutable token;
    address public immutable admin;
    address public immutable minter;
    address public immutable pauser;
    address public immutable burner;

    address[] public actors;

    uint256 public ghost_totalMinted;
    uint256 public ghost_totalBurned;
    uint256 public ghost_pauseToggles;

    constructor(
        AugPocToken _token,
        address _admin,
        address _minter,
        address _pauser,
        address _burner
    ) {
        token = _token;
        admin = _admin;
        minter = _minter;
        pauser = _pauser;
        burner = _burner;

        actors.push(makeAddr("actor1"));
        actors.push(makeAddr("actor2"));
        actors.push(makeAddr("actor3"));
        actors.push(makeAddr("actor4"));
    }

    function _pickActor(
        uint256 seed
    ) internal view returns (address) {
        return actors[seed % actors.length];
    }

    function _safeBound(
        uint256 amount,
        uint256 max
    ) internal pure returns (uint256) {
        if (max == 0) return 0;
        return amount % (max + 1);
    }

    /// @notice Mint a bounded amount of tokens to a random tracked actor.
    function mint(
        uint256 actorSeed,
        uint256 amount
    ) public {
        address recipient = _pickActor(actorSeed);
        amount = _safeBound(amount, type(uint96).max);

        vm.prank(minter);
        token.mint(recipient, amount);

        ghost_totalMinted += amount;
    }

    /// @notice Burn a bounded amount of tokens from a random tracked actor (with allowance).
    function burnFrom(
        uint256 actorSeed,
        uint256 amount
    ) public {
        address holder = _pickActor(actorSeed);
        uint256 holderBalance = token.balanceOf(holder);
        if (holderBalance == 0) return;

        amount = _safeBound(amount, holderBalance);
        if (amount == 0) return;

        vm.prank(holder);
        token.approve(burner, amount);

        vm.prank(burner);
        token.burnFrom(holder, amount);

        ghost_totalBurned += amount;
    }

    /// @notice Move a bounded amount between two tracked actors. Skipped if paused.
    function transfer(
        uint256 fromSeed,
        uint256 toSeed,
        uint256 amount
    ) public {
        if (token.paused()) return;

        address from = _pickActor(fromSeed);
        address to = _pickActor(toSeed);
        if (from == to) return;

        uint256 balance = token.balanceOf(from);
        if (balance == 0) return;

        amount = _safeBound(amount, balance);
        if (amount == 0) return;

        vm.prank(from);
        token.transfer(to, amount);
    }

    /// @notice Toggle the pause state. Mint and burn must remain operational either way.
    function togglePause() public {
        if (token.paused()) {
            vm.prank(pauser);
            token.unpause();
        } else {
            vm.prank(pauser);
            token.pause();
        }
        ghost_pauseToggles += 1;
    }
}

/// @title  AugPocTokenInvariantTest — global properties of AugPocToken
/// @notice Drives the AugPocTokenHandler with random sequences and asserts global invariants
///         after each call. Configured for 256 runs × 64 calls/run via foundry.toml.
contract AugPocTokenInvariantTest is StdInvariant, Test {
    AugPocToken internal token;
    AugPocTokenHandler internal handler;

    address internal admin = makeAddr("inv-admin");
    address internal minter = makeAddr("inv-minter");
    address internal pauser = makeAddr("inv-pauser");
    address internal burner = makeAddr("inv-burner");

    function setUp() public {
        token = new AugPocToken(admin);

        vm.startPrank(admin);
        token.grantRole(token.MINTER_ROLE(), minter);
        token.grantRole(token.PAUSER_ROLE(), pauser);
        token.grantRole(token.BURNER_ROLE(), burner);
        vm.stopPrank();

        handler = new AugPocTokenHandler(token, admin, minter, pauser, burner);

        targetContract(address(handler));

        bytes4[] memory selectors = new bytes4[](4);
        selectors[0] = AugPocTokenHandler.mint.selector;
        selectors[1] = AugPocTokenHandler.burnFrom.selector;
        selectors[2] = AugPocTokenHandler.transfer.selector;
        selectors[3] = AugPocTokenHandler.togglePause.selector;
        targetSelector(FuzzSelector({addr: address(handler), selectors: selectors}));
    }

    /// @dev totalSupply tracks (mints − burns) exactly. No spontaneous inflation.
    function invariant_TotalSupplyEqualsMintsMinusBurns() public view {
        assertEq(token.totalSupply(), handler.ghost_totalMinted() - handler.ghost_totalBurned());
    }

    /// @dev Sum of tracked actor balances equals totalSupply (since only tracked actors hold).
    function invariant_SumOfActorBalancesEqualsTotalSupply() public view {
        uint256 sum;
        for (uint256 i = 0; i < 4; i++) {
            sum += token.balanceOf(handler.actors(i));
        }
        assertEq(sum, token.totalSupply());
    }

    /// @dev Privileged role assignments are stable: handler does not grant or revoke roles, so
    ///      the configured actors retain their roles throughout the run.
    function invariant_RolesRemainAssigned() public view {
        assertTrue(token.hasRole(token.MINTER_ROLE(), minter));
        assertTrue(token.hasRole(token.PAUSER_ROLE(), pauser));
        assertTrue(token.hasRole(token.BURNER_ROLE(), burner));
        assertTrue(token.hasRole(0x00, admin)); // DEFAULT_ADMIN_ROLE
    }

    /// @dev BURNER_ROLE is never granted to any tracked actor — only the dedicated burner has it.
    ///      Guards against the worst regression: an actor inadvertently gaining burn authority.
    function invariant_NoActorEverGainsBurnerRole() public view {
        bytes32 burnerRole = token.BURNER_ROLE();
        for (uint256 i = 0; i < 4; i++) {
            assertFalse(token.hasRole(burnerRole, handler.actors(i)));
        }
    }
}
