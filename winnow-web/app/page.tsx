"use client";

import { useState } from "react";
import { Brief, BriefItem, CompareResult, SOURCES, Source, TRUST_COLOR } from "./types";
import TrendChart, { TrendPoint } from "./TrendChart";
import CompareView from "./CompareView";
import { downloadBrief } from "./exportHtml";

export default function Home() {
  const [topic, setTopic] = useState("");
  const [vs, setVs] = useState("");
  const [exclude, setExclude] = useState("");
  const [sources, setSources] = useState<Source[]>(["appstore"]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [brief, setBrief] = useState<Brief | null>(null);
  const [trend, setTrend] = useState<TrendPoint[] | null>(null);
  const [comparison, setComparison] = useState<CompareResult | null>(null);

  function toggle(s: Source) {
    setSources((cur) =>
      cur.includes(s) ? cur.filter((x) => x !== s) : [...cur, s],
    );
  }

  async function run() {
    if (!topic.trim() || sources.length === 0) return;
    setLoading(true);
    setError(null);
    setBrief(null);
    setTrend(null);
    setComparison(null);
    const vsList = vs.split(",").map((v) => v.trim()).filter(Boolean);
    try {
      if (vsList.length > 0) {
        // Competitor diff mode.
        const res = await fetch("/api/compare", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ topic, vs: vsList, sources, contextExclude: exclude }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error ?? "request failed");
        setComparison(data as CompareResult);
        return;
      }
      const res = await fetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic, sources, limit: 25, contextExclude: exclude }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error ?? "request failed");
      setBrief(data as Brief);
      // Fetch accumulated history for this topic (best-effort).
      try {
        const tRes = await fetch(`/api/trends?topic=${encodeURIComponent(topic)}`);
        const tData = await tRes.json();
        if (tRes.ok) setTrend(tData.series as TrendPoint[]);
      } catch {
        setTrend(null);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto max-w-3xl px-5 pb-24 pt-10">
      <header className="mb-2">
        <h1 className="text-3xl font-bold">Winnow</h1>
        <p className="text-sm text-[var(--muted)]">
          Last-30-days research ranked by authenticity, not raw engagement.
        </p>
      </header>

      <section className="mt-6 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
        <div className="flex gap-2">
          <input
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && run()}
            placeholder="App name, package id, or topic…"
            className="flex-1 rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-[var(--text)] outline-none focus:border-[var(--accent)]"
          />
          <button
            onClick={run}
            disabled={loading || !topic.trim() || sources.length === 0}
            className="rounded-lg bg-[var(--accent)] px-5 py-2 font-semibold text-white disabled:opacity-40"
          >
            {loading ? "Running…" : "Winnow"}
          </button>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          {SOURCES.map((s) => (
            <button
              key={s}
              onClick={() => toggle(s)}
              className={`rounded-full border px-3 py-1 text-xs ${
                sources.includes(s)
                  ? "border-[var(--accent)] text-[var(--text)]"
                  : "border-[var(--border)] text-[var(--muted)]"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
        <div className="mt-3 grid gap-2 sm:grid-cols-2">
          <input
            value={vs}
            onChange={(e) => setVs(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && run()}
            placeholder="Compare vs… (e.g. Obsidian, comma-separated)"
            className="rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-sm text-[var(--text)] outline-none focus:border-[var(--accent)]"
          />
          <input
            value={exclude}
            onChange={(e) => setExclude(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && run()}
            placeholder="Exclude terms… (e.g. song, band, movie)"
            className="rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-sm text-[var(--text)] outline-none focus:border-[var(--accent)]"
          />
        </div>
      </section>

      {error && (
        <p className="mt-4 rounded-lg border border-[var(--red)] bg-[var(--red)]/10 px-4 py-3 text-sm text-[var(--red)]">
          {error}
        </p>
      )}

      {loading && (
        <p className="mt-6 text-sm text-[var(--muted)]">
          Searching {sources.join(", ")} and scoring authenticity…
        </p>
      )}

      {comparison && <CompareView result={comparison} />}

      {brief && (
        <section className="mt-6">
          <div className="mb-3 flex items-center justify-between gap-3">
            <span className="text-sm text-[var(--muted)]">
              {brief.item_count} items · ranked by trust × engagement ·{" "}
              {new Date(brief.generated_at).toLocaleDateString()}
            </span>
            {brief.items.length > 0 && (
              <button
                onClick={() => downloadBrief(brief)}
                className="rounded-lg border border-[var(--border)] px-3 py-1 text-xs text-[var(--text)] hover:border-[var(--accent)]"
              >
                ⬇ Export HTML
              </button>
            )}
          </div>
          {trend && (
            <div className="mb-5 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
              <h2 className="mb-2 text-sm font-semibold">
                Reputation trend{" "}
                <span className="font-normal text-[var(--muted)]">
                  — what last30days can&apos;t show you
                </span>
              </h2>
              <TrendChart series={trend} />
            </div>
          )}
          {brief.warnings.map((w) => (
            <p
              key={w}
              className="mb-3 rounded-lg border border-[var(--yellow)] bg-[var(--yellow)]/10 px-4 py-2 text-sm text-[var(--yellow)]"
            >
              ⚠️ {w}
            </p>
          ))}
          {brief.items.length === 0 && (
            <p className="text-sm text-[var(--muted)]">No items found.</p>
          )}
          <ol className="space-y-3">
            {brief.items.map((it, i) => (
              <ItemCard key={it.item_id || i} item={it} rank={i + 1} />
            ))}
          </ol>
        </section>
      )}
    </main>
  );
}

function ItemCard({ item, rank }: { item: BriefItem; rank: number }) {
  const color = TRUST_COLOR[item.trust_label];
  const head = item.title || item.text.slice(0, 80);
  return (
    <li className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
      <div className="mb-1 flex items-start justify-between gap-3">
        <h3 className="font-semibold leading-snug">
          {rank}. {head}
        </h3>
      </div>
      <div className="mb-2 flex flex-wrap items-center gap-2 text-xs text-[var(--muted)]">
        <span className="rounded bg-[var(--bg)] px-2 py-0.5 font-mono">
          {item.source}
        </span>
        {item.rating != null && <span>{item.rating}★</span>}
        {item.published_at && (
          <span>{new Date(item.published_at).toLocaleDateString()}</span>
        )}
        <span style={{ color }}>
          ● {item.trust_label} {item.trust.toFixed(2)}
        </span>
      </div>
      <div className="mb-2 h-1.5 w-full overflow-hidden rounded-full bg-[var(--bg)]">
        <div
          className="h-full"
          style={{ width: `${Math.round(item.trust * 100)}%`, background: color }}
        />
      </div>
      {item.text && item.text !== head && (
        <p className="border-l-2 border-[var(--border)] pl-3 text-sm">
          {item.text.slice(0, 320)}
        </p>
      )}
      {item.flags.length > 0 && (
        <p className="mt-2 text-xs text-[var(--yellow)]">
          flags: {item.flags.map((f) => f.name).join(", ")}
        </p>
      )}
      {item.url && (
        <a
          href={item.url}
          target="_blank"
          rel="noreferrer"
          className="mt-2 inline-block text-sm text-[var(--accent)]"
        >
          {item.source} link →
        </a>
      )}
    </li>
  );
}
