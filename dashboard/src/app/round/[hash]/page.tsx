import Link from "next/link";
import { notFound } from "next/navigation";
import { type Hex } from "viem";

import { AddressLink } from "@/components/AddressLink";
import { CountdownTimer } from "@/components/CountdownTimer";
import { StatusBadge } from "@/components/StatusBadge";
import { isDeployed, RoundStatus, roundStatusLabel } from "@/lib/contracts";
import { formatTokenAmount, formatUtcDate, ipfsHttpUrl } from "@/lib/format";
import { fetchAllRounds, windowEnd } from "@/lib/rounds";

export const dynamic = "force-dynamic";

interface Props {
  params: Promise<{ hash: string }>;
}

export default async function RoundDetailPage({ params }: Props) {
  const { hash } = await params;

  if (!isDeployed()) {
    return (
      <div className="rounded-md border border-warn/40 bg-warn/10 p-6 font-mono text-warn">
        Contracts not yet deployed.
      </div>
    );
  }

  const rounds = await fetchAllRounds();
  const round = rounds.find((r) => r.roundHash.toLowerCase() === hash.toLowerCase());
  if (!round) notFound();

  const winEnd = windowEnd(round);
  const isOpen =
    round.status === RoundStatus.Proposed || round.status === RoundStatus.Challenged;

  return (
    <div className="space-y-8">
      <div>
        <Link href="/rounds" className="text-sm text-muted hover:text-accent">
          ← all rounds
        </Link>
        <h1 className="text-2xl font-mono font-semibold mt-2">Round detail</h1>
        <div className="font-mono text-xs text-muted break-all mt-1">{round.roundHash}</div>
      </div>

      <section className="rounded-md border border-border bg-panel p-4 grid grid-cols-1 md:grid-cols-2 gap-4">
        <Field label="Status" value={<StatusBadge status={round.status} />} />
        <Field label="Status (numeric)" value={`${round.status} — ${roundStatusLabel[round.status]}`} />
        <Field label="Proposed at (UTC)" value={formatUtcDate(round.proposedAt)} />
        <Field
          label="Challenge window"
          value={`${round.challengeWindowDays} days`}
          hint={`ends ${formatUtcDate(winEnd)}`}
        />
        <Field label="Beneficiaries" value={round.beneficiaries.length} />
        <Field
          label="Total to mint"
          value={`${formatTokenAmount(round.totalAmount, 18)} AUG-POC`}
        />
      </section>

      {isOpen && (
        <section className="rounded-md border border-accent/40 bg-accent/10 p-4 font-mono">
          <div className="text-xs uppercase tracking-wider text-accent">Window</div>
          <div className="text-lg mt-1">
            <CountdownTimer targetUnix={winEnd} />
          </div>
        </section>
      )}

      <section>
        <h2 className="text-lg font-mono font-semibold mb-3">Allocation</h2>
        <div className="rounded-md border border-border bg-panel overflow-x-auto">
          <table className="w-full text-sm font-mono">
            <thead>
              <tr className="border-b border-border text-left text-muted">
                <th className="px-4 py-3">#</th>
                <th className="px-4 py-3">Beneficiary</th>
                <th className="px-4 py-3 text-right">Amount</th>
              </tr>
            </thead>
            <tbody>
              {round.beneficiaries.map((addr, i) => (
                <tr key={`${addr}-${i}`} className="border-b border-border/50 last:border-0">
                  <td className="px-4 py-3 text-muted">{i + 1}</td>
                  <td className="px-4 py-3">
                    <AddressLink address={addr} full />
                  </td>
                  <td className="px-4 py-3 text-right">
                    {formatTokenAmount(round.amounts[i] ?? 0n, 18)} AUG-POC
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h2 className="text-lg font-mono font-semibold mb-3">Off-chain artefacts</h2>
        <div className="rounded-md border border-border bg-panel p-4 font-mono text-sm space-y-2">
          <div>
            <span className="text-muted">IPFS URI: </span>
            {round.ipfsUri ? (
              <a
                href={ipfsHttpUrl(round.ipfsUri)}
                target="_blank"
                rel="noreferrer noopener"
                className="text-accent hover:underline break-all"
              >
                {round.ipfsUri}
              </a>
            ) : (
              <span className="text-muted">(none)</span>
            )}
          </div>
          <div className="text-xs text-muted">
            The IPFS URI points to the pinned <code>valuation_report.md</code>. The roundHash is
            <code> keccak256(abi.encode(beneficiaries, amounts, ipfsUri))</code> — anyone can
            re-derive it from these inputs and verify the on-chain commitment.
          </div>
        </div>
      </section>
    </div>
  );
}

function Field({
  label,
  value,
  hint,
}: {
  label: string;
  value: React.ReactNode;
  hint?: React.ReactNode;
}) {
  return (
    <div>
      <div className="text-xs uppercase tracking-wider text-muted">{label}</div>
      <div className="font-mono mt-1">{value}</div>
      {hint ? <div className="text-xs text-muted mt-0.5">{hint}</div> : null}
    </div>
  );
}

// Suppress the unused-import warning when Hex isn't visibly referenced.
type _Unused = Hex;
