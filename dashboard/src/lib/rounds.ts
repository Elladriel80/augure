/**
 * Read all rounds known to the registry by scanning the four lifecycle events
 * (RoundProposed / Challenged / Executed / Cancelled) from `deployBlock` to
 * the current head. Folds them into one record per roundHash with the latest
 * status. Pure read-only — never broadcasts.
 */

import { type Address, type Hex } from "viem";

import { publicClient } from "./chain";
import { deployBlock, registryAddress, roundRegistryAbi, RoundStatus } from "./contracts";

export interface RoundSummary {
  roundHash: Hex;
  ipfsUri: string;
  proposedAt: bigint;
  challengeWindowDays: number;
  status: RoundStatus;
  beneficiaries: readonly Address[];
  amounts: readonly bigint[];
  totalAmount: bigint;
  /** Block number of the most recent on-chain event for this round. */
  lastEventBlock: bigint;
}

/**
 * Fetch every round committed to the registry and return them sorted by
 * proposedAt descending (most recent first). Best-effort: any round whose
 * Proposed event we can't decode is silently skipped.
 */
export async function fetchAllRounds(): Promise<RoundSummary[]> {
  const proposedLogs = await publicClient.getContractEvents({
    address: registryAddress,
    abi: roundRegistryAbi,
    eventName: "RoundProposed",
    fromBlock: deployBlock,
    toBlock: "latest",
  });

  const challengedLogs = await publicClient.getContractEvents({
    address: registryAddress,
    abi: roundRegistryAbi,
    eventName: "RoundChallenged",
    fromBlock: deployBlock,
    toBlock: "latest",
  });

  const executedLogs = await publicClient.getContractEvents({
    address: registryAddress,
    abi: roundRegistryAbi,
    eventName: "RoundExecuted",
    fromBlock: deployBlock,
    toBlock: "latest",
  });

  const cancelledLogs = await publicClient.getContractEvents({
    address: registryAddress,
    abi: roundRegistryAbi,
    eventName: "RoundCancelled",
    fromBlock: deployBlock,
    toBlock: "latest",
  });

  const rounds = new Map<Hex, RoundSummary>();

  for (const log of proposedLogs) {
    if (!log.args.roundHash) continue;
    const ben = (log.args.beneficiaries ?? []) as readonly Address[];
    const amts = (log.args.amounts ?? []) as readonly bigint[];
    const total = amts.reduce((acc, a) => acc + a, 0n);
    rounds.set(log.args.roundHash, {
      roundHash: log.args.roundHash,
      ipfsUri: log.args.ipfsUri ?? "",
      proposedAt: log.args.proposedAt ?? 0n,
      challengeWindowDays: Number(log.args.challengeWindowDays ?? 0),
      status: RoundStatus.Proposed,
      beneficiaries: ben,
      amounts: amts,
      totalAmount: total,
      lastEventBlock: log.blockNumber ?? 0n,
    });
  }

  // Apply later events in chronological order so the final status is correct.
  const laterEvents = [
    ...challengedLogs.map((l) => ({ log: l, status: RoundStatus.Challenged })),
    ...executedLogs.map((l) => ({ log: l, status: RoundStatus.Executed })),
    ...cancelledLogs.map((l) => ({ log: l, status: RoundStatus.Cancelled })),
  ].sort((a, b) => Number((a.log.blockNumber ?? 0n) - (b.log.blockNumber ?? 0n)));

  for (const { log, status } of laterEvents) {
    const hash = (log.args as { roundHash?: Hex }).roundHash;
    if (!hash) continue;
    const existing = rounds.get(hash);
    if (!existing) continue;
    existing.status = status;
    existing.lastEventBlock = log.blockNumber ?? existing.lastEventBlock;
  }

  return Array.from(rounds.values()).sort((a, b) => Number(b.proposedAt - a.proposedAt));
}

/**
 * Compute when the challenge window of a round closes.
 */
export function windowEnd(round: RoundSummary): bigint {
  return round.proposedAt + BigInt(round.challengeWindowDays) * 86_400n;
}
