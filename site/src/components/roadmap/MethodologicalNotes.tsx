// components/roadmap/MethodologicalNotes.tsx
import type { Content } from "./content";

interface Props {
  title: string;
  notes: Content["notes"];
}

export function MethodologicalNotes({ title, notes }: Props) {
  return (
    <section
      className="mx-auto max-w-5xl px-6 py-16 sm:px-8"
      aria-label={title}
    >
      <h2 className="mb-10 text-xs font-mono uppercase tracking-widest text-muted">
        {title}
      </h2>

      <dl className="grid gap-5 sm:grid-cols-2">
        {notes.map((note, idx) => (
          <div
            key={idx}
            className="rounded border border-border bg-panel/30 p-5"
          >
            <dt className="font-mono text-base text-text">{note.title}</dt>
            <dd className="mt-2 text-sm font-mono leading-relaxed text-muted">
              {note.body}
            </dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
