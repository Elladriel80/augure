import { createPublicClient, http, type Chain } from "viem";
import { arbitrumSepolia, foundry } from "viem/chains";

const CHAIN_ID = Number(process.env.NEXT_PUBLIC_CHAIN_ID || 421614);

function resolveChain(chainId: number): Chain {
  switch (chainId) {
    case 421614:
      return arbitrumSepolia;
    case 31337:
      return foundry;
    default:
      throw new Error(`Unsupported chain id: ${chainId}`);
  }
}

export const chain = resolveChain(CHAIN_ID);

const RPC_URL = process.env.NEXT_PUBLIC_RPC_URL || chain.rpcUrls.default.http[0];

export const publicClient = createPublicClient({
  chain,
  transport: http(RPC_URL),
});

export const explorerUrl: string =
  process.env.NEXT_PUBLIC_EXPLORER_URL ||
  chain.blockExplorers?.default?.url ||
  "https://sepolia.arbiscan.io";

export function explorerAddressUrl(address: string): string {
  return `${explorerUrl}/address/${address}`;
}

export function explorerTxUrl(hash: string): string {
  return `${explorerUrl}/tx/${hash}`;
}
