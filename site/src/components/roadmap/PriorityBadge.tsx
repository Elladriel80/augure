// components/roadmap/PriorityBadge.tsx
import type { Priority } from "./content";

const styles: Record<Priority, string> = {
  P1: "bg-err/15 text-err border border-err/40",
  P2: "bg-accent/15 text-accent border border-accent/40",
  P3: "bg-accent2/15 text-accent2 border border-accent2/40",
};

interface Props {
  priority: Priority;
  label: string;
}

export function PriorityBadge({ priority, label }: Props) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 text-xs font-mono rounded ${styles[priority]}`}
    >
      {label}
    </span>
  );
}
