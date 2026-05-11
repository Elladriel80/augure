const styles: Record<string, string> = {
  active: "bg-ok/20 text-ok border border-ok/40",
  experimental: "bg-accent/20 text-accent border border-accent/40",
  dropped: "bg-err/20 text-err border border-err/40",
  retired: "bg-border text-muted border border-border",
};

export function FeatureStatusBadge({ status }: { status: string }) {
  const style = styles[status] ?? "bg-border text-muted border border-border";
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider rounded ${style}`}
    >
      {status}
    </span>
  );
}
