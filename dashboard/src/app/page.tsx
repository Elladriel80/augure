import Link from "next/link";

import { AddressLink } from "@/components/AddressLink";
import { MetricCard } from "@/components/MetricCard";
import { publicClient } from "@/lib/chain";
import {
  augPocTokenAbi,
  isDeployed,
  registryAddress,
  roundRegistryAbi,
  tokenAddress,
} from "@/lib/contracts";
import {
  formatPercent,
  formatTokenAmount,
  monthIdLabel,
  monthIdOf,
} from "@/lib/format";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  if (!isDeployed()) {
    return (
      <div className="rounded-md border border-warn/40 bg-warn/10 p-6 font-mono">
        <h1 className="text-xl mb-2 text-warn">Contracts not yet deployed</h1>
        <p className="text-sm text-muted">
          Set <code>NEXT_PUBLIC_TOKEN_ADDRESS</code> and{" "}
          <code>NEXT_PUBLIC_REGISTRY_ADDRESS</code> in the environment once the M4
          deployment script has run on Arbitrum Sepolia. The dashboard will then read
          the live state on the next refresh.
        </p>
      </div>
    );
  }

  // Bundle the read calls into a single multicall round-trip.
  const [name, symbol, decimals, totalSupply, paused] = await Promise.all([
    publicClient.readContract({ address: tokenAddress, abi: augPocTokenAbi, functionName: "name" }),
    publicClient.readContract({ address: tokenAddress, abi: augPocTokenAbi, functionName: "symbol" }),
    publicClient.readContract({ address: tokenAddress, abi: augPocTokenAbi, functionName: "decimals" }),
    publicClient.readContract({ address: tokenAddress, abi: augPocTokenAbi, functionName: "totalSupply" }),
    publicClient.readContract({ address: tokenAddress, abi: augPocTokenAbi, functionName: "paused" }),
  ]);

  const nowSeconds = BigInt(Math.floor(Date.now() / 1000));
  const currentMonthId = monthIdOf(nowSeconds);

  const [supplyAtMonthStart, mintedInMonth] = await Promise.all([
    publicClient.readContract({
      address: registryAddress,
      abi: roundRegistryAbi,
      functionName: "supplyAtMonthStart",
      args: [currentMonthId],
    }),
    publicClient.readContract({
      address: registryAddress,
      abi: roundRegistryAbi,
      functionName: "mintedInMonth",
      args: [currentMonthId],
    }),
  ]);

  const cap = (supplyAtMonthStart * 1000n) / 10_000n;
  const remaining = cap > mintedInMonth ? cap - mintedInMonth : 0n;
  const capBinds = supplyAtMonthStart > 0n;

  return (
    <div className="space-y-8">
      <section>
        <div className="flex items-baseline justify-between mb-4">
          <h1 className="text-2xl font-mono font-semibold">{name}</h1>
          <div className="text-sm text-muted font-mono">
            {symbol} · {decimals} decimals
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <MetricCard
            label="Total supply"
            value={`${formatTokenAmount(totalSupply, decimals)} ${symbol}`}
            hint={`${totalSupply} wei`}
          />
          <MetricCard
            label="Pause state"
            value={paused ? "PAUSED" : "active"}
            hint={
              paused
                ? "User-to-user transfers are blocked. Mint and burn paths still operate."
                : "User-to-user transfers are allowed."
            }
            accent={paused ? "warn" : "ok"}
          />
          <MetricCard
            label="Token contract"
            value={<AddressLink address={tokenAddress} />}
            hint="Verified on the explorer if `forge verify-contract` was run."
          />
        </div>
      </section>

      <section>
        <h2 className="text-xl font-mono font-semibold mb-4">
          Monthly cap — {monthIdLabel(currentMonthId)}
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <MetricCard
            label="Supply at month start"
            value={`${formatTokenAmount(supplyAtMonthStart, decimals)} ${symbol}`}
            hint={
              capBinds
                ? "Snapshot taken at the first executeRound of the month."
                : "Genesis exception — no snapshot yet."
            }
          />
          <MetricCard
            label="Minted this month"
            value={`${formatTokenAmount(mintedInMonth, decimals)} ${symbol}`}
            hint={
              capBinds
                ? `${formatPercent(mintedInMonth, cap)} of the 10% cap`
                : "Cap not binding this month."
            }
          />
          <MetricCard
            label="Remaining margin"
            value={
              capBinds
                ? `${formatTokenAmount(remaining, decimals)} ${symbol}`
                : "unconstrained"
            }
            hint={
              capBinds
                ? `Cap = ${formatTokenAmount(cap, decimals)} ${symbol}`
                : "Genesis exception"
            }
            accent={capBinds && remaining === 0n ? "err" : "accent"}
          />
        </div>
      </section>

      <section>
        <h2 className="text-xl font-mono font-semibold mb-2">Rounds</h2>
        <p className="text-sm text-muted mb-3">
          Lifecycle of every monthly mint round. See{" "}
          <Link href="/rounds" className="text-accent hover:underline">
            the rounds page
          </Link>{" "}
          for the full list.
        </p>
        <p className="text-sm text-muted">
          Registry: <AddressLink address={registryAddress} />
        </p>
      </section>
    </div>
  );
}
