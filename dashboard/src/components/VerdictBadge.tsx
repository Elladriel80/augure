import type { Verdict } from "@/lib/manifest";

const styles: Record<string, string> = {
  ENSEMBLE: "bg-ok/20 text-ok border border-ok/40",
  LEARNED: "bg-ok/20 text-ok border border-ok/40",
  MARKET: "bg-err/20 text-err border border-err/40",
  TIE: "bg-warn/20 text-warn border border-warn/40",
};

const labels: Record<string, string> = {
  ENSEMBLE: "ENSEMBLE WINS",
  LEARNED: "ENSEMBLE WINS",
  MARKET: "MARKET WINS",
  TIE: "TIE",
};

export function VerdictBadge({ verdict }: { verdict: Verdict | string }) {
  const key = verdict in styles ? verdict : "TIE";
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 text-xs font-mono rounded ${styles[key]}`}
      title="Comparison of test-set Brier vs kalshi_mid on the same rows"
    >
      {labels[key] ?? verdict}
    </span>
  );
}
