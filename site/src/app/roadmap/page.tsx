// app/roadmap/page.tsx
import type { Metadata } from "next";
import { dict, type Locale } from "@/components/roadmap/content";
import { Hero } from "@/components/roadmap/Hero";
import { StateSection } from "@/components/roadmap/StateSection";
import { PhaseTimeline } from "@/components/roadmap/PhaseTimeline";
import { PhaseCard } from "@/components/roadmap/PhaseCard";
import { BacklogSection } from "@/components/roadmap/BacklogSection";
import { MethodologicalNotes } from "@/components/roadmap/MethodologicalNotes";

export const metadata: Metadata = {
  title: "Roadmap — Aratea",
  description:
    "La trajectoire d'Aratea — mutuelle paramétrique décentralisée et marchés prédictifs météo. État, phases, backlog.",
  openGraph: {
    title: "Roadmap — Aratea",
    description:
      "La trajectoire d'Aratea — mutuelle paramétrique décentralisée et marchés prédictifs météo.",
    type: "article",
  },
};

interface PageProps {
  searchParams?: Promise<{ lang?: string }> | { lang?: string };
}

export default async function RoadmapPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const requested = params?.lang;
  const locale: Locale = requested === "en" ? "en" : "fr";
  const c = dict[locale];
  const deliverablesLabel = locale === "fr" ? "Livrables" : "Deliverables";

  return (
    <main className="min-h-screen bg-bg text-text font-mono antialiased">
      <Hero content={c} locale={locale} />

      <StateSection state={c.state} />

      <Divider />

      <PhaseTimeline title={c.phasesTitle} phases={c.phases} />

      <section className="mx-auto max-w-5xl space-y-8 px-6 pb-8 sm:px-8">
        {c.phases.map((phase) => (
          <PhaseCard
            key={phase.id}
            phase={phase}
            statusLabel={c.status[phase.status]}
            deliverablesLabel={deliverablesLabel}
          />
        ))}
      </section>

      <Divider />

      <BacklogSection
        title={c.backlogTitle}
        backlog={c.backlog}
        priorityLabels={c.priority}
      />

      <Divider />

      <MethodologicalNotes title={c.notesTitle} notes={c.notes} />

      <footer className="mx-auto max-w-5xl border-t border-border px-6 py-10 sm:px-8">
        <p className="text-xs font-mono text-muted">{c.footer}</p>
      </footer>
    </main>
  );
}

function Divider() {
  return (
    <div
      aria-hidden="true"
      className="mx-auto h-px max-w-5xl bg-gradient-to-r from-transparent via-border to-transparent"
    />
  );
}
