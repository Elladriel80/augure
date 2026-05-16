// components/roadmap/PhaseCard.tsx
import type { Phase } from "./content";
import { StatusBadge } from "./StatusBadge";

const numberBg: Record<Phase["status"], string> = {
  done: "text-ok/10",
  "in-progress": "text-warn/15",
  planned: "text-border",
};

const cardRing: Record<Phase["status"], string> = {
  done: "border-ok/20 bg-panel/40",
  "in-progress": "border-warn/30 bg-panel/60",
  planned: "border-border bg-panel/20",
};

interface Props {
  phase: Phase;
  statusLabel: string;
  deliverablesLabel: string;
}

export function PhaseCard({ phase, statusLabel, deliverablesLabel }: Props) {
  return (
    <article
      id={phase.id}
      className={`relative scroll-mt-24 overflow-hidden rounded-lg border p-8 sm:p-10 ${
        cardRing[phase.status]
      }`}
    >
      {/* Background big number — purely decorative */}
      <span
        aria-hidden="true"
        className={`pointer-events-none absolute -right-4 -top-12 select-none font-mono text-[10rem] leading-none ${
          numberBg[phase.status]
        } sm:text-[14rem]`}
      >
        {phase.number}
      </span>

      <div className="relative">
        <StatusBadge status={phase.status} label={statusLabel} />

        <h3 className="mt-4 font-mono text-2xl font-normal tracking-tight text-text sm:text-3xl">
          {phase.title}
        </h3>

        {phase.subtitle && (
          <p className="mt-1 text-xs font-mono text-muted">{phase.subtitle}</p>
        )}

        <p className="mt-6 max-w-3xl text-sm font-mono leading-relaxed text-text">
          {phase.description}
        </p>

        <div className="mt-8">
          <h4 className="text-xs font-mono uppercase tracking-widest text-muted">
            {deliverablesLabel}
          </h4>
          <ul className="mt-4 space-y-2.5" role="list">
            {phase.deliverables.map((d, idx) => (
              <li
                key={idx}
                className="flex gap-3 text-sm font-mono text-text"
              >
                <span
                  aria-hidden="true"
                  className="mt-2 h-px w-3 flex-shrink-0 bg-muted"
                />
                <span className="leading-relaxed">{d}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </article>
  );
}
