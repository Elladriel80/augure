interface Props {
  label: string;
  value: React.ReactNode;
  hint?: React.ReactNode;
  /** Optional accent colour name from tailwind config (e.g. "ok", "warn", "err"). */
  accent?: "ok" | "warn" | "err" | "accent";
}

const accentClasses: Record<NonNullable<Props["accent"]>, string> = {
  ok: "text-ok",
  warn: "text-warn",
  err: "text-err",
  accent: "text-accent",
};

export function MetricCard({ label, value, hint, accent }: Props) {
  return (
    <div className="rounded-md border border-border bg-panel p-4 flex flex-col gap-1">
      <div className="text-xs uppercase tracking-wider text-muted">{label}</div>
      <div
        className={`text-2xl font-mono font-semibold ${accent ? accentClasses[accent] : "text-text"}`}
      >
        {value}
      </div>
      {hint ? <div className="text-xs text-muted">{hint}</div> : null}
    </div>
  );
}
