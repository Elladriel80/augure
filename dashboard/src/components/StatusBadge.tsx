import { RoundStatus } from "@/lib/contracts";
import { getDict } from "@/lib/i18n";

const styles: Record<RoundStatus, string> = {
  [RoundStatus.None]: "bg-border text-muted",
  [RoundStatus.Proposed]: "bg-accent/20 text-accent border border-accent/40",
  [RoundStatus.Challenged]: "bg-warn/20 text-warn border border-warn/40",
  [RoundStatus.Executed]: "bg-ok/20 text-ok border border-ok/40",
  [RoundStatus.Cancelled]: "bg-err/20 text-err border border-err/40",
};

export async function StatusBadge({ status }: { status: RoundStatus }) {
  const dict = await getDict();
  const labels: Record<RoundStatus, string> = {
    [RoundStatus.None]: dict.status.none,
    [RoundStatus.Proposed]: dict.status.proposed,
    [RoundStatus.Challenged]: dict.status.challenged,
    [RoundStatus.Executed]: dict.status.executed,
    [RoundStatus.Cancelled]: dict.status.cancelled,
  };

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 text-xs font-mono rounded ${styles[status]}`}
    >
      {labels[status]}
    </span>
  );
}
