import Link from "next/link";

import { StatusBadge } from "@/components/StatusBadge";
import { isDeployed, RoundStatus } from "@/lib/contracts";
import { formatTokenAmount, formatUtcDate, shortAddress } from "@/lib/format";
import { fetchAllRounds, windowEnd } from "@/lib/rounds";

export const dynamic = "force-dynamic";

export default async function RoundsPage() {
  if (!isDeployed()) {
    return (
      <div className="rounded-md border border-warn/40 bg-warn/10 p-6 font-mono">
        <h1 className="text-xl mb-2 text-warn">Contracts not yet deployed</h1>
        <p className="text-sm text-muted">
          The dashboard will list rounds once the M4 deployment script has run.
        </p>
      </div>
    );
  }

  const rounds = await fetchAllRounds();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-mono font-semibold mb-2">Rounds</h1>
        <p className="text-sm text-muted">
          Every round committed to the registry, ordered by proposal date (most recent first).
        </p>
      </div>

      {rounds.length === 0 ? (
        <div className="rounded-md border border-border bg-panel p-6 font-mono text-muted">
          No rounds proposed yet. The first one will appear here once the founder runs{" "}
          <code className="text-text">script/ProposeGenesisRound.s.sol</code>.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-md border border-border bg-panel">
          <table className="w-full text-sm font-mono">
            <thead>
              <tr className="border-b border-border text-left text-muted">
                <th className="px-4 py-3">Round</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Proposed</th>
                <th className="px-4 py-3">Window ends</th>
                <th className="px-4 py-3 text-right">Total amount</th>
                <th className="px-4 py-3 text-right">Beneficiaries</th>
              </tr>
            </thead>
            <tbody>
              {rounds.map((r) => {
                const winEnd = windowEnd(r);
                return (
                  <tr key={r.roundHash} className="border-b border-border/50 last:border-0">
                    <td className="px-4 py-3">
                      <Link href={`/round/${r.roundHash}`} className="text-accent hover:underline">
                        {shortAddress(r.roundHash, 6)}
                      </Link>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={r.status} />
                    </td>
                    <td className="px-4 py-3 text-muted">{formatUtcDate(r.proposedAt)}</td>
                    <td className="px-4 py-3 text-muted">
                      {r.status === RoundStatus.Executed || r.status === RoundStatus.Cancelled
                        ? "—"
                        : formatUtcDate(winEnd)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {formatTokenAmount(r.totalAmount, 18)} AUG-POC
                    </td>
                    <td className="px-4 py-3 text-right text-muted">
                      {r.beneficiaries.length}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
