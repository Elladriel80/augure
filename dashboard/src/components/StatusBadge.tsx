import { RoundStatus } from "@/lib/contracts";

const styles: Record<RoundStatus, string> = {
  [RoundStatus.None]: "bg-border text-muted",
  [RoundStatus.Proposed]: "bg-accent/20 text-accent border border-accent/40",
  [RoundStatus.Challenged]: "bg-warn/20 text-warn border border-warn/40",
  [RoundStatus.Executed]: "bg-ok/20 text-ok border border-ok/40",
  [RoundStatus.Cancelled]: "bg-err/20 text-err border border-err/40",
};

const labels: Record<RoundStatus, string> = {
  [RoundStatus.None]: "Unknown",
  [RoundStatus.Proposed]: "Proposed",
  [RoundStatus.Challenged]: "Challenged",
  [RoundStatus.Executed]: "Executed",
  [RoundStatus.Cancelled]: "Cancelled",
};

export function StatusBadge({ status }: { status: RoundStatus }) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 text-xs font-mono rounded ${styles[status]}`}
    >
      {labels[status]}
    </span>
  );
}
