// components/roadmap/PhaseTimeline.tsx
import type { Phase } from "./content";

const dot: Record<Phase["status"], string> = {
  done: "bg-ok border-ok text-bg",
  "in-progress": "bg-warn border-warn text-bg animate-pulse",
  planned: "bg-panel border-border text-muted",
};

const connector: Record<Phase["status"], string> = {
  done: "bg-ok/50",
  "in-progress": "bg-gradient-to-r from-warn/50 to-border",
  planned: "bg-border",
};

interface Props {
  title: string;
  phases: Phase[];
}

export function PhaseTimeline({ title, phases }: Props) {
  return (
    <section
      className="mx-auto max-w-5xl px-6 py-16 sm:px-8"
      aria-label={title}
    >
      <h2 className="mb-10 text-xs font-mono uppercase tracking-widest text-muted">
        {title}
      </h2>

      <ol className="relative grid grid-cols-5 gap-2" role="list">
        {phases.map((phase, idx) => {
          const isLast = idx === phases.length - 1;
          return (
            <li key={phase.id} className="relative flex flex-col items-center">
              {!isLast && (
                <span
                  aria-hidden="true"
                  className={`absolute left-1/2 top-6 h-px w-full ${
                    connector[phase.status]
                  }`}
                />
              )}
              <a
                href={`#${phase.id}`}
                className={`relative z-10 flex h-12 w-12 items-center justify-center rounded-full border-2 font-mono text-base transition-transform hover:scale-110 ${
                  dot[phase.status]
                }`}
                aria-current={phase.status === "in-progress" ? "step" : undefined}
                aria-label={`${phase.title} — ${phase.number}`}
              >
                {phase.number}
              </a>
              <span className="mt-3 max-w-[120px] text-center text-xs font-mono text-text">
                {phase.title}
              </span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
