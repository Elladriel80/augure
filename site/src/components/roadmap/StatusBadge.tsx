// components/roadmap/StatusBadge.tsx
import type { Status } from "./content";

const styles: Record<Status, string> = {
  done: "bg-ok/15 text-ok border border-ok/40",
  "in-progress": "bg-warn/15 text-warn border border-warn/40",
  planned: "bg-border text-muted border border-border",
};

interface Props {
  status: Status;
  label: string;
}

export function StatusBadge({ status, label }: Props) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 text-xs font-mono rounded ${styles[status]}`}
    >
      <span
        aria-hidden="true"
        className={`h-1.5 w-1.5 rounded-full ${
          status === "done"
            ? "bg-ok"
            : status === "in-progress"
            ? "bg-warn animate-pulse"
            : "bg-muted"
        }`}
      />
      {label}
    </span>
  );
}
