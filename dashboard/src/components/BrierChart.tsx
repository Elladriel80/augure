import { getDict } from "@/lib/i18n";
import type { RunRecord } from "@/lib/manifest";

interface Props {
  runs: RunRecord[];
  kalshiReference: number | null;
}

const VIEWBOX_W = 800;
const VIEWBOX_H = 320;
const PAD = { top: 24, right: 88, bottom: 44, left: 56 };
const INNER_W = VIEWBOX_W - PAD.left - PAD.right;
const INNER_H = VIEWBOX_H - PAD.top - PAD.bottom;

interface Point {
  x: number;
  y: number;
  raw: number;
}

function gridYTicks(maxY: number): number[] {
  // ~5 ticks covering [0, maxY], rounded to a clean step.
  const step =
    maxY <= 0.05 ? 0.01 : maxY <= 0.1 ? 0.02 : maxY <= 0.2 ? 0.05 : 0.1;
  const ticks: number[] = [];
  for (let t = 0; t <= maxY + step / 2; t += step) ticks.push(t);
  return ticks;
}

function shortRunLabel(ts: string): string {
  // 20260511T130831Z → 05-11
  const m = ts.match(/^\d{4}(\d{2})(\d{2})T/);
  return m ? `${m[1]}-${m[2]}` : ts.slice(0, 6);
}

export async function BrierChart({ runs, kalshiReference }: Props) {
  const dict = await getDict();
  const t = dict.components.brier_chart;

  if (runs.length === 0) {
    return (
      <div className="rounded-md border border-border bg-panel p-6 font-mono text-sm text-muted">
        {t.empty}
      </div>
    );
  }

  const sorted = [...runs].sort((a, b) => a.ts.localeCompare(b.ts));
  const allYs: number[] = [];
  for (const r of sorted) {
    if (typeof r.brier_test === "number") allYs.push(r.brier_test);
    if (typeof r.brier_kalshi_mid_test === "number")
      allYs.push(r.brier_kalshi_mid_test);
  }
  if (typeof kalshiReference === "number") allYs.push(kalshiReference);
  const maxY = Math.max(0.05, ...allYs) * 1.1;
  const ticks = gridYTicks(maxY);

  const xOf = (i: number): number => {
    if (sorted.length === 1) return PAD.left + INNER_W / 2;
    return PAD.left + (i / (sorted.length - 1)) * INNER_W;
  };
  const yOf = (v: number): number => PAD.top + INNER_H * (1 - v / maxY);

  const learned: Point[] = sorted
    .map((r, i) =>
      typeof r.brier_test === "number"
        ? { x: xOf(i), y: yOf(r.brier_test), raw: r.brier_test }
        : null,
    )
    .filter((p): p is Point => p !== null);

  const kalshi: Point[] = sorted
    .map((r, i) =>
      typeof r.brier_kalshi_mid_test === "number"
        ? {
            x: xOf(i),
            y: yOf(r.brier_kalshi_mid_test),
            raw: r.brier_kalshi_mid_test,
          }
        : null,
    )
    .filter((p): p is Point => p !== null);

  const path = (pts: Point[]): string =>
    pts.length === 0
      ? ""
      : pts
          .map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(2)} ${p.y.toFixed(2)}`)
          .join(" ");

  // Feature-set transition markers: vertical dashed line whenever the
  // feature_set changes between consecutive runs (or first run).
  const transitions: { x: number; label: string }[] = [];
  let prevSet: string | null = null;
  sorted.forEach((r, i) => {
    if (r.feature_set && r.feature_set !== prevSet) {
      transitions.push({ x: xOf(i), label: r.feature_set });
      prevSet = r.feature_set;
    }
  });

  return (
    <div className="rounded-md border border-border bg-panel p-4 overflow-x-auto">
      <svg
        viewBox={`0 0 ${VIEWBOX_W} ${VIEWBOX_H}`}
        role="img"
        aria-label="Brier trajectory chart: learned model vs kalshi_mid across training runs"
        className="w-full h-auto font-mono"
      >
        {/* Y-axis grid + labels */}
        {ticks.map((t) => (
          <g key={t}>
            <line
              x1={PAD.left}
              x2={PAD.left + INNER_W}
              y1={yOf(t)}
              y2={yOf(t)}
              stroke="#1f262e"
              strokeWidth={1}
            />
            <text
              x={PAD.left - 8}
              y={yOf(t) + 4}
              textAnchor="end"
              fontSize="10"
              fill="#6b7480"
            >
              {t.toFixed(t < 0.05 ? 3 : 2)}
            </text>
          </g>
        ))}

        {/* X-axis baseline */}
        <line
          x1={PAD.left}
          x2={PAD.left + INNER_W}
          y1={PAD.top + INNER_H}
          y2={PAD.top + INNER_H}
          stroke="#1f262e"
          strokeWidth={1}
        />

        {/* Feature-set transition markers */}
        {transitions.map((t, i) => (
          <g key={i}>
            <line
              x1={t.x}
              x2={t.x}
              y1={PAD.top}
              y2={PAD.top + INNER_H}
              stroke="#a48dff"
              strokeWidth={1}
              strokeDasharray="3 3"
              opacity={0.5}
            />
            <text
              x={t.x}
              y={PAD.top - 8}
              textAnchor="middle"
              fontSize="10"
              fill="#a48dff"
            >
              {t.label}
            </text>
          </g>
        ))}

        {/* All-time kalshi_mid reference */}
        {typeof kalshiReference === "number" && (
          <g>
            <line
              x1={PAD.left}
              x2={PAD.left + INNER_W}
              y1={yOf(kalshiReference)}
              y2={yOf(kalshiReference)}
              stroke="#6b7480"
              strokeWidth={1}
              strokeDasharray="2 4"
            />
            <text
              x={PAD.left + INNER_W + 6}
              y={yOf(kalshiReference) + 4}
              fontSize="10"
              fill="#6b7480"
            >
              bench ({kalshiReference.toFixed(4)})
            </text>
          </g>
        )}

        {/* Lines */}
        <path d={path(kalshi)} fill="none" stroke="#e2b341" strokeWidth={2} />
        <path d={path(learned)} fill="none" stroke="#5fa8d3" strokeWidth={2} />

        {/* Points */}
        {kalshi.map((p, i) => (
          <circle
            key={`k-${i}`}
            cx={p.x}
            cy={p.y}
            r={3.5}
            fill="#e2b341"
            stroke="#0b0d10"
            strokeWidth={1}
          >
            <title>kalshi_mid Brier: {p.raw.toFixed(4)}</title>
          </circle>
        ))}
        {learned.map((p, i) => (
          <circle
            key={`l-${i}`}
            cx={p.x}
            cy={p.y}
            r={3.5}
            fill="#5fa8d3"
            stroke="#0b0d10"
            strokeWidth={1}
          >
            <title>learned Brier: {p.raw.toFixed(4)}</title>
          </circle>
        ))}

        {/* X-axis labels */}
        {sorted.map((r, i) => (
          <text
            key={r.ts}
            x={xOf(i)}
            y={PAD.top + INNER_H + 16}
            textAnchor="middle"
            fontSize="10"
            fill="#6b7480"
          >
            {shortRunLabel(r.ts)}
          </text>
        ))}

        {/* Axis titles */}
        <text
          x={PAD.left}
          y={VIEWBOX_H - 6}
          fontSize="10"
          fill="#6b7480"
        >
          {t.axis_x}
        </text>
        <text
          transform={`translate(14 ${PAD.top + INNER_H / 2}) rotate(-90)`}
          textAnchor="middle"
          fontSize="10"
          fill="#6b7480"
        >
          {t.axis_y}
        </text>

        {/* Legend */}
        <g transform={`translate(${PAD.left} ${PAD.top - 12})`}>
          <rect width="8" height="2" y={4} fill="#5fa8d3" />
          <text x="14" y="8" fontSize="11" fill="#e4e8ec">
            {t.legend_learned}
          </text>
          <rect x="110" width="8" height="2" y={4} fill="#e2b341" />
          <text x="124" y="8" fontSize="11" fill="#e4e8ec">
            {t.legend_kalshi}
          </text>
        </g>
      </svg>
    </div>
  );
}
