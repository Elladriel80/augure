import Link from "next/link";
import { notFound } from "next/navigation";
import { type Hex } from "viem";

import { AddressLink } from "@/components/AddressLink";
import { CountdownTimer } from "@/components/CountdownTimer";
import { StatusBadge } from "@/components/StatusBadge";
import { isDeployed, RoundStatus, roundStatusLabel } from "@/lib/contracts";
import { formatTokenAmount, formatUtcDate, ipfsHttpUrl } from "@/lib/format";
import { getDict } from "@/lib/i18n";
import { fetchAllRounds, windowEnd } from "@/lib/rounds";

export const dynamic = "force-dynamic";

interface Props {
  params: Promise<{ hash: string }>;
}

export default async function RoundDetailPage({ params }: Props) {
  const dict = await getDict();
  const { hash } = await params;

  if (!isDeployed()) {
    return (
      <div className="rounded-md border border-warn/40 bg-warn/10 p-6 font-mono text-warn">
        {dict.common.not_deployed_short}
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
          {dict.round_detail.back}
        </Link>
        <h1 className="text-2xl font-mono font-semibold mt-2">
          {dict.round_detail.title}
        </h1>
        <div className="font-mono text-xs text-muted break-all mt-1">{round.roundHash}</div>
      </div>

      <section className="rounded-md border border-border bg-panel p-4 grid grid-cols-1 md:grid-cols-2 gap-4">
        <Field
          label={dict.round_detail.fields.status}
          value={<StatusBadge status={round.status} />}
        />
        <Field
          label={dict.round_detail.fields.status_numeric}
          value={`${round.status} — ${roundStatusLabel[round.status]}`}
        />
        <Field
          label={dict.round_detail.fields.proposed_at}
          value={formatUtcDate(round.proposedAt)}
        />
        <Field
          label={dict.round_detail.fields.challenge_window}
          value={dict.round_detail.fields.challenge_window_value(
            round.challengeWindowDays,
          )}
          hint={dict.round_detail.fields.challenge_window_hint(
            formatUtcDate(winEnd),
          )}
        />
        <Field
          label={dict.round_detail.fields.beneficiaries}
          value={round.beneficiaries.length}
        />
        <Field
          label={dict.round_detail.fields.total_to_mint}
          value={`${formatTokenAmount(round.totalAmount, 18)} AUG-POC`}
        />
      </section>

      {isOpen && (
        <section className="rounded-md border border-accent/40 bg-accent/10 p-4 font-mono">
          <div className="text-xs uppercase tracking-wider text-accent">
            {dict.round_detail.window_label}
          </div>
          <div className="text-lg mt-1">
            <CountdownTimer
              targetUnix={winEnd}
              labels={dict.components.countdown}
            />
          </div>
        </section>
      )}

      <section>
        <h2 className="text-lg font-mono font-semibold mb-3">
          {dict.round_detail.allocation}
        </h2>
        <div className="rounded-md border border-border bg-panel overflow-x-auto">
          <table className="w-full text-sm font-mono">
            <thead>
              <tr className="border-b border-border text-left text-muted">
                <th className="px-4 py-3">{dict.round_detail.allocation_table.index}</th>
                <th className="px-4 py-3">
                  {dict.round_detail.allocation_table.beneficiary}
                </th>
                <th className="px-4 py-3 text-right">
                  {dict.round_detail.allocation_table.amount}
                </th>
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
        <h2 className="text-lg font-mono font-semibold mb-3">
          {dict.round_detail.offchain}
        </h2>
        <div className="rounded-md border border-border bg-panel p-4 font-mono text-sm space-y-2">
          <div>
            <span className="text-muted">{dict.round_detail.ipfs_uri} </span>
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
              <span className="text-muted">{dict.round_detail.ipfs_none}</span>
            )}
          </div>
          <div className="text-xs text-muted">{dict.round_detail.ipfs_help}</div>
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
