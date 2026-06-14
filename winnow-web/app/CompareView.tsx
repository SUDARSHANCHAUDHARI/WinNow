"use client";

import { CompareEntity, CompareResult, TRUST_COLOR } from "./types";

function trustColor(t: number | null) {
  if (t == null) return "var(--muted)";
  if (t >= 0.75) return TRUST_COLOR.trusted;
  if (t >= 0.45) return TRUST_COLOR.mixed;
  return TRUST_COLOR.suspicious;
}

export default function CompareView({ result }: { result: CompareResult }) {
  const ents = result.entities;
  return (
    <section className="mt-6">
      {result.verdict && (
        <p className="mb-4 rounded-xl border border-[var(--accent)] bg-[var(--accent)]/10 px-4 py-3 text-sm">
          <span className="font-semibold">Verdict: </span>
          {result.verdict}
        </p>
      )}

      <div className="overflow-x-auto rounded-xl border border-[var(--border)]">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-[var(--muted)]">
              <th className="px-4 py-2 font-medium">Metric</th>
              {ents.map((e) => (
                <th key={e.topic} className="px-4 py-2 font-semibold text-[var(--text)]">
                  {e.topic}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <Row label="Items" ents={ents} render={(e) => String(e.item_count)} />
            <Row label="Avg rating" ents={ents} render={(e) => (e.avg_rating ?? "-") + ""} />
            <Row
              label="Avg trust"
              ents={ents}
              render={(e) => (
                <span style={{ color: trustColor(e.avg_trust) }}>
                  {e.avg_trust ?? "-"}
                </span>
              )}
            />
            <Row
              label="Suspicious"
              ents={ents}
              render={(e) => `${e.suspicious} (${Math.round(e.suspicious_share * 100)}%)`}
            />
          </tbody>
        </table>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        {ents.map((e) => (
          <div key={e.topic} className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
            <h3 className="mb-2 font-semibold">{e.topic}</h3>
            {e.top_praise && (
              <p className="mb-2 text-sm">
                <span style={{ color: TRUST_COLOR.trusted }}>▲ praise</span>{" "}
                <span className="text-[var(--muted)]">
                  ({e.top_praise.rating ?? "?"}★, trust {e.top_praise.trust})
                </span>
                : “{e.top_praise.text}”
              </p>
            )}
            {e.top_complaint && (
              <p className="text-sm">
                <span style={{ color: TRUST_COLOR.suspicious }}>▼ complaint</span>{" "}
                <span className="text-[var(--muted)]">
                  ({e.top_complaint.rating ?? "?"}★, trust {e.top_complaint.trust})
                </span>
                : “{e.top_complaint.text}”
              </p>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

function Row({
  label,
  ents,
  render,
}: {
  label: string;
  ents: CompareEntity[];
  render: (e: CompareEntity) => React.ReactNode;
}) {
  return (
    <tr className="border-t border-[var(--border)]">
      <td className="px-4 py-2 text-[var(--muted)]">{label}</td>
      {ents.map((e) => (
        <td key={e.topic} className="px-4 py-2">
          {render(e)}
        </td>
      ))}
    </tr>
  );
}
