// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {Test} from "forge-std/Test.sol";

import {AugPocToken} from "../../src/token/AugPocToken.sol";
import {RoundRegistry} from "../../src/rounds/RoundRegistry.sol";
import {IAugPocToken} from "../../src/interfaces/IAugPocToken.sol";
import {IRoundRegistry} from "../../src/interfaces/IRoundRegistry.sol";

/// @title  GenesisRoundE2E — end-to-end reproduction of the Augure genesis mint
/// @notice This test plays the exact genesis scenario described in white paper section 11
///         and the off-chain artefacts under `rounds/archives/2026-05-genesis/`:
///           - one beneficiary (the founder's EOA, holder Elladriel80)
///           - 34_039_500 sats valued labor on the imported `predictor/` POC
///           - 34_039_500 tokens (1 sat = 1 token by NAV) — i.e. 34_039_500 * 10^18 wei,
///             since AugPocToken has 18 decimals and `RoundRegistry.executeRound` calls
///             `token.mint` in wei units.
///           - 30-day extended challenge window (instead of the regular 7 days)
///         The test verifies the full lifecycle works on this concrete scenario, that the
///         mint succeeds under the genesis exception (totalSupply was zero before), and
///         that the resulting on-chain state matches what `valuation_report.md` documents.
contract GenesisRoundE2E is Test {
    AugPocToken internal token;
    RoundRegistry internal registry;

    // The actual founder EOA — see `memory/reference_addresses.md` for the chain of custody.
    address internal constant ELLADRIEL = 0x9a94552DCB67F036af6eccc9111b749856ab8EEA;

    address internal admin = makeAddr("admin");
    address internal proposer = makeAddr("proposer");
    address internal executor = makeAddr("executor");
    address internal canceller = makeAddr("canceller");

    // 34_039_500 sats translated to wei (token has 18 decimals, 1 sat ≡ 1 token by mint
    // convention). Genesis valuation per `rounds/archives/2026-05-genesis/valuation_report.md`.
    uint256 internal constant GENESIS_AMOUNT_WEI = 34_039_500 ether;

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

        // Anchor at the date of the genesis report: 2026-05-08 12:00 UTC.
        vm.warp(1_778_587_200);
    }

    function test_GenesisRound_ProposeChallengeWindowExecute() public {
        // 1. The Safe proposes the genesis round with a 30-day window.
        address[] memory beneficiaries = new address[](1);
        beneficiaries[0] = ELLADRIEL;
        uint256[] memory amounts = new uint256[](1);
        amounts[0] = GENESIS_AMOUNT_WEI;
        string memory ipfsUri = "ipfs://bafyGenesisValuationReport2026-05";
        bytes32 roundHash = keccak256(abi.encode(beneficiaries, amounts, ipfsUri));

        vm.prank(proposer);
        registry.proposeRound(roundHash, beneficiaries, amounts, ipfsUri, 30);

        assertEq(uint8(registry.statusOf(roundHash)), uint8(IRoundRegistry.RoundStatus.Proposed));
        assertEq(token.totalSupply(), 0, "supply must still be zero before execution");

        // 2. Nobody challenges. 30 days pass.
        vm.warp(block.timestamp + 30 days);

        // 3. The Safe executes the round.
        vm.prank(executor);
        registry.executeRound(roundHash);

        // 4. State matches the off-chain valuation report.
        assertEq(uint8(registry.statusOf(roundHash)), uint8(IRoundRegistry.RoundStatus.Executed));
        assertEq(token.balanceOf(ELLADRIEL), GENESIS_AMOUNT_WEI, "founder receives 34_039_500 tokens");
        assertEq(token.totalSupply(), GENESIS_AMOUNT_WEI, "supply == genesis amount");
        // Sanity check on the magnitude — humans love decimal numbers.
        assertEq(token.balanceOf(ELLADRIEL) / 1e18, 34_039_500, "balance reads as 34,039,500 in human units");
    }

    function test_GenesisRound_ChallengedThenExecuted() public {
        // What happens if a prospective investor challenges, off-chain panel dismisses,
        // and the Safe lets the window expire? The mint must still go through.
        address[] memory beneficiaries = new address[](1);
        beneficiaries[0] = ELLADRIEL;
        uint256[] memory amounts = new uint256[](1);
        amounts[0] = GENESIS_AMOUNT_WEI;
        string memory ipfsUri = "ipfs://bafyGenesis";
        bytes32 roundHash = keccak256(abi.encode(beneficiaries, amounts, ipfsUri));

        vm.prank(proposer);
        registry.proposeRound(roundHash, beneficiaries, amounts, ipfsUri, 30);

        // A prospective investor files a challenge mid-window.
        vm.warp(block.timestamp + 15 days);
        address prospectiveInvestor = makeAddr("prospectiveInvestor");
        vm.prank(prospectiveInvestor);
        registry.challengeRound(roundHash, "ipfs://challenge-rationale");
        assertEq(uint8(registry.statusOf(roundHash)), uint8(IRoundRegistry.RoundStatus.Challenged));

        // Off-chain panel dismisses the challenge. Window expires without a cancelRound.
        vm.warp(block.timestamp + 16 days);

        vm.prank(executor);
        registry.executeRound(roundHash);
        assertEq(token.balanceOf(ELLADRIEL), GENESIS_AMOUNT_WEI);
    }

    function test_GenesisRound_ChallengedThenCancelled_NoMint() public {
        // What happens if a prospective investor challenges and the off-chain panel UPHOLDS
        // the challenge? The Safe cancels and no mint happens.
        address[] memory beneficiaries = new address[](1);
        beneficiaries[0] = ELLADRIEL;
        uint256[] memory amounts = new uint256[](1);
        amounts[0] = GENESIS_AMOUNT_WEI;
        string memory ipfsUri = "ipfs://bafyGenesis";
        bytes32 roundHash = keccak256(abi.encode(beneficiaries, amounts, ipfsUri));

        vm.prank(proposer);
        registry.proposeRound(roundHash, beneficiaries, amounts, ipfsUri, 30);

        vm.prank(makeAddr("challenger"));
        registry.challengeRound(roundHash, "ipfs://reason");

        vm.prank(canceller);
        registry.cancelRound(roundHash, "ipfs://panel-upheld");

        assertEq(uint8(registry.statusOf(roundHash)), uint8(IRoundRegistry.RoundStatus.Cancelled));

        // Even after window expires, the round cannot be revived.
        vm.warp(block.timestamp + 30 days);
        vm.expectRevert(IRoundRegistry.RoundNotProposedOrChallenged.selector);
        vm.prank(executor);
        registry.executeRound(roundHash);

        assertEq(token.balanceOf(ELLADRIEL), 0, "no mint when round is cancelled");
        assertEq(token.totalSupply(), 0);
    }
}
