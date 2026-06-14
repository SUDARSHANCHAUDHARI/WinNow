"use client";

export type TrendPoint = {
  run_id: number;
  ts: string;
  item_count: number;
  avg_trust: number;
  avg_rating: number | null;
  suspicious: number;
};

const W = 600;
const H = 200;
const PAD = { l: 34, r: 34, t: 16, b: 26 };

function line(points: [number, number][]): string {
  return points.map(([x, y], i) => `${i ? "L" : "M"}${x},${y}`).join(" ");
}

export default function TrendChart({ series }: { series: TrendPoint[] }) {
  if (series.length < 2) {
    return (
      <p className="text-sm text-[var(--muted)]">
        Run this topic again later to build a trend. One run so far - the chart
        needs at least two.
      </p>
    );
  }

  const innerW = W - PAD.l - PAD.r;
  const innerH = H - PAD.t - PAD.b;
  const x = (i: number) => PAD.l + (innerW * i) / (series.length - 1);
  const yTrust = (v: number) => PAD.t + innerH * (1 - v); // trust in [0,1]
  const yRating = (v: number) => PAD.t + innerH * (1 - v / 5); // rating in [0,5]

  const trustPts = series.map((p, i) => [x(i), yTrust(p.avg_trust)] as [number, number]);
  const ratingPts = series
    .map((p, i) => (p.avg_rating != null ? ([x(i), yRating(p.avg_rating)] as [number, number]) : null))
    .filter((p): p is [number, number] => p !== null);

  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="trust over time">
        {[0, 0.25, 0.5, 0.75, 1].map((g) => (
          <g key={g}>
            <line
              x1={PAD.l}
              x2={W - PAD.r}
              y1={yTrust(g)}
              y2={yTrust(g)}
              stroke="var(--border)"
              strokeWidth={1}
            />
            <text x={4} y={yTrust(g) + 4} fontSize={10} fill="var(--muted)">
              {g.toFixed(2)}
            </text>
          </g>
        ))}

        {/* suspicious-share bars */}
        {series.map((p, i) => {
          const share = p.item_count ? p.suspicious / p.item_count : 0;
          const h = innerH * share;
          return share > 0 ? (
            <rect
              key={p.run_id}
              x={x(i) - 5}
              y={PAD.t + innerH - h}
              width={10}
              height={h}
              fill="var(--red)"
              opacity={0.35}
            />
          ) : null;
        })}

        {/* rating line (normalized to 0..5) */}
        {ratingPts.length >= 2 && (
          <path d={line(ratingPts)} fill="none" stroke="var(--yellow)" strokeWidth={1.5} strokeDasharray="4 3" />
        )}

        {/* trust line */}
        <path d={line(trustPts)} fill="none" stroke="var(--accent)" strokeWidth={2} />
        {trustPts.map(([cx, cy], i) => (
          <circle key={i} cx={cx} cy={cy} r={3} fill="var(--accent)" />
        ))}

        {/* x labels: first and last date */}
        <text x={PAD.l} y={H - 8} fontSize={10} fill="var(--muted)">
          {new Date(series[0].ts).toLocaleDateString()}
        </text>
        <text x={W - PAD.r} y={H - 8} fontSize={10} fill="var(--muted)" textAnchor="end">
          {new Date(series[series.length - 1].ts).toLocaleDateString()}
        </text>
      </svg>

      <div className="mt-1 flex gap-4 text-xs text-[var(--muted)]">
        <span>
          <span style={{ color: "var(--accent)" }}>●</span> avg trust
        </span>
        <span>
          <span style={{ color: "var(--yellow)" }}>┈</span> avg rating (÷5)
        </span>
        <span>
          <span style={{ color: "var(--red)" }}>▮</span> suspicious share
        </span>
      </div>
    </div>
  );
}
