/**
 * Contract addresses (from env) and TypeScript-native ABIs for the read-only
 * surface the dashboard consumes. We hand-write the ABIs (rather than dump the
 * full Foundry artefacts) so they stay tight, fully typed by viem, and free of
 * irrelevant constructor / write functions.
 */

import { type Address } from "viem";

const TOKEN_ADDRESS_RAW = process.env.NEXT_PUBLIC_TOKEN_ADDRESS as `0x${string}` | undefined;
const REGISTRY_ADDRESS_RAW = process.env.NEXT_PUBLIC_REGISTRY_ADDRESS as `0x${string}` | undefined;

export const tokenAddress: Address = (TOKEN_ADDRESS_RAW ||
  "0x0000000000000000000000000000000000000000") as Address;

export const registryAddress: Address = (REGISTRY_ADDRESS_RAW ||
  "0x0000000000000000000000000000000000000000") as Address;

export const deployBlock: bigint = BigInt(process.env.NEXT_PUBLIC_DEPLOY_BLOCK || "0");

export function isDeployed(): boolean {
  const zero = "0x0000000000000000000000000000000000000000";
  return tokenAddress.toLowerCase() !== zero && registryAddress.toLowerCase() !== zero;
}

/* ------------------------------------------------------------------ */
/* AugPocToken — read-only surface                                    */
/* ------------------------------------------------------------------ */

export const augPocTokenAbi = [
  {
    type: "function",
    name: "name",
    stateMutability: "view",
    inputs: [],
    outputs: [{ type: "string" }],
  },
  {
    type: "function",
    name: "symbol",
    stateMutability: "view",
    inputs: [],
    outputs: [{ type: "string" }],
  },
  {
    type: "function",
    name: "decimals",
    stateMutability: "view",
    inputs: [],
    outputs: [{ type: "uint8" }],
  },
  {
    type: "function",
    name: "totalSupply",
    stateMutability: "view",
    inputs: [],
    outputs: [{ type: "uint256" }],
  },
  {
    type: "function",
    name: "paused",
    stateMutability: "view",
    inputs: [],
    outputs: [{ type: "bool" }],
  },
  {
    type: "function",
    name: "MINTER_ROLE",
    stateMutability: "view",
    inputs: [],
    outputs: [{ type: "bytes32" }],
  },
  {
    type: "function",
    name: "PAUSER_ROLE",
    stateMutability: "view",
    inputs: [],
    outputs: [{ type: "bytes32" }],
  },
  {
    type: "function",
    name: "BURNER_ROLE",
    stateMutability: "view",
    inputs: [],
    outputs: [{ type: "bytes32" }],
  },
  {
    type: "function",
    name: "hasRole",
    stateMutability: "view",
    inputs: [
      { name: "role", type: "bytes32" },
      { name: "account", type: "address" },
    ],
    outputs: [{ type: "bool" }],
  },
] as const;

/* ------------------------------------------------------------------ */
/* RoundRegistry — read-only surface                                  */
/* ------------------------------------------------------------------ */

export const roundRegistryAbi = [
  {
    type: "function",
    name: "statusOf",
    stateMutability: "view",
    inputs: [{ name: "roundHash", type: "bytes32" }],
    outputs: [{ type: "uint8" }],
  },
  {
    type: "function",
    name: "supplyAtMonthStart",
    stateMutability: "view",
    inputs: [{ name: "monthId", type: "uint256" }],
    outputs: [{ type: "uint256" }],
  },
  {
    type: "function",
    name: "mintedInMonth",
    stateMutability: "view",
    inputs: [{ name: "monthId", type: "uint256" }],
    outputs: [{ type: "uint256" }],
  },
  {
    type: "function",
    name: "getRound",
    stateMutability: "view",
    inputs: [{ name: "roundHash", type: "bytes32" }],
    outputs: [
      { name: "ipfsUri", type: "string" },
      { name: "proposedAt", type: "uint64" },
      { name: "challengeWindowDays", type: "uint32" },
      { name: "status", type: "uint8" },
    ],
  },
  {
    type: "function",
    name: "getRoundBeneficiaries",
    stateMutability: "view",
    inputs: [{ name: "roundHash", type: "bytes32" }],
    outputs: [{ type: "address[]" }],
  },
  {
    type: "function",
    name: "getRoundAmounts",
    stateMutability: "view",
    inputs: [{ name: "roundHash", type: "bytes32" }],
    outputs: [{ type: "uint256[]" }],
  },
  {
    type: "function",
    name: "windowEndOf",
    stateMutability: "view",
    inputs: [{ name: "roundHash", type: "bytes32" }],
    outputs: [{ type: "uint256" }],
  },
  {
    type: "function",
    name: "token",
    stateMutability: "view",
    inputs: [],
    outputs: [{ type: "address" }],
  },
  /* Events the dashboard subscribes to */
  {
    type: "event",
    name: "RoundProposed",
    inputs: [
      { name: "roundHash", type: "bytes32", indexed: true },
      { name: "ipfsUri", type: "string", indexed: false },
      { name: "proposedAt", type: "uint64", indexed: false },
      { name: "challengeWindowDays", type: "uint32", indexed: false },
      { name: "beneficiaries", type: "address[]", indexed: false },
      { name: "amounts", type: "uint256[]", indexed: false },
    ],
    anonymous: false,
  },
  {
    type: "event",
    name: "RoundChallenged",
    inputs: [
      { name: "roundHash", type: "bytes32", indexed: true },
      { name: "challenger", type: "address", indexed: true },
      { name: "reasonIpfsUri", type: "string", indexed: false },
    ],
    anonymous: false,
  },
  {
    type: "event",
    name: "RoundExecuted",
    inputs: [
      { name: "roundHash", type: "bytes32", indexed: true },
      { name: "executedAt", type: "uint64", indexed: false },
      { name: "totalMinted", type: "uint256", indexed: false },
    ],
    anonymous: false,
  },
  {
    type: "event",
    name: "RoundCancelled",
    inputs: [
      { name: "roundHash", type: "bytes32", indexed: true },
      { name: "canceller", type: "address", indexed: true },
      { name: "reasonIpfsUri", type: "string", indexed: false },
    ],
    anonymous: false,
  },
] as const;

/* ------------------------------------------------------------------ */
/* Round status enum (matches IRoundRegistry.RoundStatus)             */
/* ------------------------------------------------------------------ */

export enum RoundStatus {
  None = 0,
  Proposed = 1,
  Challenged = 2,
  Executed = 3,
  Cancelled = 4,
}

export const roundStatusLabel: Record<RoundStatus, string> = {
  [RoundStatus.None]: "None",
  [RoundStatus.Proposed]: "Proposed",
  [RoundStatus.Challenged]: "Challenged",
  [RoundStatus.Executed]: "Executed",
  [RoundStatus.Cancelled]: "Cancelled",
};
