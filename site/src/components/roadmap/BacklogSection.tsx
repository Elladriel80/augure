// components/roadmap/BacklogSection.tsx
import type { Content } from "./content";
import { PriorityBadge } from "./PriorityBadge";

interface Props {
  title: string;
  backlog: Content["backlog"];
  priorityLabels: Content["priority"];
}

export function BacklogSection({ title, backlog, priorityLabels }: Props) {
  return (
    <section
      className="mx-auto max-w-5xl px-6 py-16 sm:px-8"
      aria-label={title}
    >
      <h2 className="mb-10 text-xs font-mono uppercase tracking-widest text-muted">
        {title}
      </h2>

      <ul className="space-y-3" role="list">
        {backlog.map((item, idx) => (
          <li
            key={idx}
            className="rounded-lg border border-border bg-panel/40 p-5 transition-colors hover:border-accent/30 sm:p-6"
          >
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start">
              <PriorityBadge
                priority={item.priority}
                label={priorityLabels[item.priority]}
              />
              <div className="flex-1">
                <h3 className="font-mono text-base text-text">{item.title}</h3>
                <p className="mt-1.5 text-sm font-mono leading-relaxed text-muted">
                  {item.description}
                </p>
              </div>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
