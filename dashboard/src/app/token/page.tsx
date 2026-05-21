import Link from "next/link";

import { AddressLink } from "@/components/AddressLink";
import { MetricCard } from "@/components/MetricCard";
import { publicClient } from "@/lib/chain";
import {
  augPocTokenAbi,
  isDeployed,
  registryAddress,
  tokenAddress,
} from "@/lib/contracts";
import { formatTokenAmount } from "@/lib/format";
import { getDict } from "@/lib/i18n";

export const dynamic = "force-dynamic";

export default async function TokenPage() {
  const dict = await getDict();

  if (!isDeployed()) {
    return (
      <div className="rounded-md border border-warn/40 bg-warn/10 p-6 font-mono">
        <h1 className="text-xl mb-2 text-warn">{dict.common.not_deployed_title}</h1>
        <p className="text-sm text-muted">{dict.common.not_deployed_body}</p>
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
            label={dict.token.metrics.total_supply}
            value={`${formatTokenAmount(totalSupply, decimals)} ${symbol}`}
            hint={dict.token.metrics.total_supply_hint(totalSupply.toString())}
          />
          <MetricCard
            label={dict.token.metrics.pause_state}
            value={paused ? dict.token.metrics.paused : dict.token.metrics.active}
            hint={
              paused
                ? dict.token.metrics.paused_hint
                : dict.token.metrics.active_hint
            }
            accent={paused ? "warn" : "ok"}
          />
          <MetricCard
            label={dict.token.metrics.contract}
            value={<AddressLink address={tokenAddress} />}
            hint={dict.token.metrics.contract_hint}
          />
        </div>
      </section>

      <section>
        <h2 className="text-xl font-mono font-semibold mb-3">
          {dict.token.emission.heading}
        </h2>
        <p className="text-sm text-muted mb-2">{dict.token.emission.body}</p>
        <p className="text-sm text-muted">{dict.token.emission.reference}</p>
      </section>

      <section>
        <h2 className="text-xl font-mono font-semibold mb-2">
          {dict.token.rounds.heading}
        </h2>
        <p className="text-sm text-muted mb-3">
          {dict.token.rounds.intro(
            <Link href="/rounds" className="text-accent hover:underline">
              {dict.token.rounds.intro_link}
            </Link>,
          )}
        </p>
        <p className="text-sm text-muted">
          {dict.token.rounds.registry_label}{" "}
          <AddressLink address={registryAddress} />
        </p>
      </section>
    </div>
  );
}
