// components/roadmap/StateSection.tsx
import type { Content } from "./content";

interface Props {
  state: Content["state"];
}

export function StateSection({ state }: Props) {
  return (
    <section
      className="mx-auto max-w-5xl px-6 py-16 sm:px-8"
      aria-label={state.title}
    >
      <h2 className="mb-12 text-xs font-mono uppercase tracking-widest text-muted">
        {state.title}
      </h2>

      <div className="grid gap-10 lg:grid-cols-2">
        {/* Done */}
        <div>
          <h3 className="mb-5 flex items-center gap-3 font-mono text-lg text-text">
            <span aria-hidden="true" className="h-2 w-2 rounded-full bg-ok" />
            {state.doneLabel}
            <span className="text-xs text-muted">{state.done.length}</span>
          </h3>
          <ul className="space-y-2.5" role="list">
            {state.done.map((item, idx) => (
              <li
                key={idx}
                className="flex gap-3 text-sm font-mono leading-relaxed text-text"
              >
                <span
                  aria-hidden="true"
                  className="mt-1.5 h-1 w-1 flex-shrink-0 rounded-full bg-ok/70"
                />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* In progress */}
        <div>
          <h3 className="mb-5 flex items-center gap-3 font-mono text-lg text-text">
            <span
              aria-hidden="true"
              className="h-2 w-2 animate-pulse rounded-full bg-warn"
            />
            {state.inProgressLabel}
            <span className="text-xs text-muted">{state.inProgress.length}</span>
          </h3>
          <ul className="space-y-3" role="list">
            {state.inProgress.map((item, idx) => (
              <li
                key={idx}
                className="rounded border border-warn/30 bg-warn/5 p-4 text-sm font-mono leading-relaxed text-text"
              >
                {item}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
