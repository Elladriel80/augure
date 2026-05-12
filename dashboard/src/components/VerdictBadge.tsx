import { getDict } from "@/lib/i18n";
import type { Verdict } from "@/lib/manifest";

const styles: Record<string, string> = {
  ENSEMBLE: "bg-ok/20 text-ok border border-ok/40",
  LEARNED: "bg-ok/20 text-ok border border-ok/40",
  MARKET: "bg-err/20 text-err border border-err/40",
  TIE: "bg-warn/20 text-warn border border-warn/40",
};

export async function VerdictBadge({ verdict }: { verdict: Verdict | string }) {
  const dict = await getDict();
  const t = dict.components.verdict;
  const labels: Record<string, string> = {
    ENSEMBLE: t.ensemble,
    LEARNED: t.ensemble,
    MARKET: t.market,
    TIE: t.tie,
  };

  const key = verdict in styles ? verdict : "TIE";
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 text-xs font-mono rounded ${styles[key]}`}
      title={t.tooltip}
    >
      {labels[key] ?? verdict}
    </span>
  );
}
