# Winnow Architecture

## Thesis

last30days proved the concept: aggregate what real people say across walled
gardens and synthesize it. Its structural weakness is that **engagement is the
ranking signal with no authenticity check** — and upvotes/likes/reviews are the
most gamed metrics online. Winnow makes **authenticity the spine**: every
item is trust-scored, and ranking gates on that score. The three product angles
("app reputation", "SEA/regional", "authenticity-first") are not three products
— they are *source adapters + one scoring layer* on one engine.

## Shape

```
                 ┌──────────────────────────────┐
                 │  AUTHENTICITY ENGINE (spine)  │  authenticity.py
                 │  burst · duplicate · thin ·   │  ← the differentiator
                 │  anon/generated-handle        │
                 └───────────────┬──────────────┘
   adapters/                     │ fusion.py (trust-gated rank)
   ┌──────────────┐              │
   │ appstore  ✅ │   gather()   ▼          surfaces
   │ playstore ✅ │ ──────────► Brief ───►  • CLI (winnow.py)  ✅
   │ pantip    ✅ │  (threaded)  │          • Agent Skill (SKILL.md) — next
   │ reddit    ◻︎ │              │          • Web dashboard         — next
   │ x / yt    ◻︎ │           render.py
   └──────────────┘            (markdown)
```

## Data flow (one run)

1. **CLI** ([`engine/winnow.py`](engine/winnow.py)) parses topic + `--sources`.
2. **gather()** fans out adapters across a `ThreadPoolExecutor`; one dead source
   is logged to stderr and never kills the run (failure isolation, like
   last30days' `errors_by_source`).
3. **authenticity.score_corpus()** runs corpus-level detectors, mutating each
   `Item.authenticity` in place.
4. **fusion.rank()** orders by `log1p(engagement·trust)·trust·recency` — the
   trust gate is the second `·trust`.
5. **render.to_markdown()** emits the structured evidence block. In skill mode
   the host model synthesizes prose on top; in CLI mode this *is* the output.

## Adapter contract

Any module exposing `fetch(topic, *, lookback_days=30, limit=50) -> list[Item]`,
registered in [`engine/lib/adapters/__init__.py`](engine/lib/adapters/__init__.py).
Adapters do **retrieval + normalization only** — never authenticity scoring, so
trust logic stays in one place and is consistent across sources. This is the
extension point: a new source = one file + one registry line.

## Key types ([`engine/lib/schema.py`](engine/lib/schema.py))

- `Item` — one piece of content. `weighted_score = engagement · authenticity.score`.
- `Authenticity` — `score` + transparent `signals[]`; `.label` ∈ {trusted, mixed, suspicious}.
- `Brief` — topic + ranked items + corpus-level warnings.

## Deliberate choices (and what we took from last30days)

- **Took:** zero runtime deps, stdlib-only HTTP, threaded fan-out, failure
  isolation per source, structured-evidence-then-LLM-synthesis split.
- **Rejected:** pushing planning/format determinism onto the host model (their
  1,700-line SKILL.md + 8 LAWs). Our engine decides; the skill wrapper is thin.
- **Rejected:** scraping undocumented frontend partials as a primary path. RSS
  and official RPCs first; defensive parsers return `[]` on shape drift.

## Roadmap

| Phase | Scope |
|---|---|
| ✅ 0 | Engine + App Store/Play Store/Pantip adapters + authenticity v0 + CLI + tests |
| 1 | Reddit (official API) + account-age/karma detector; `--store` SQLite persistence |
| 2 | Thin `SKILL.md` wrapper; multi-host packaging (plugin.json, npx skills) |
| 3 | Web dashboard: trend tracking over stored runs, shareable HTML briefs |
| 4 | App-name→id resolution UX, competitor diff (`my app vs theirs`), X/YouTube |

## Open risks

- **Play Store batchexecute** payload/parse is brittle by nature; live-probe
  reachability is confirmed but full-field extraction needs a fixture-backed
  test before it's load-bearing.
- **Authenticity v0 is heuristic.** Burst/duplicate are robust; account-level
  signals (the strongest) require per-source enrichment not yet built.
- **Pantip** RSS has no native query — current matching is title/desc contains.
  The token-authed search API is the upgrade path.
