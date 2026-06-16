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
                 ┌──────────────────────────────────────┐
                 │  AUTHENTICITY ENGINE (spine)          │  authenticity.py
                 │  burst · duplicate · thin · anon ·    │  ← the differentiator
                 │  new-account · low-karma ·            │  (8 signals)
                 │  rating-text-mismatch · polarization  │
                 └───────────────┬──────────────────────┘
   adapters/                     │ fusion.py (trust gate · per-source
   ┌──────────────┐              │            normalization · diversity floor)
   │ appstore  ✅ │   gather()   ▼          surfaces
   │ playstore ✅ │ ──────────► Brief ───►  • CLI (winnow.py)        ✅
   │ pantip    ✅ │  (threaded)  │          • Agent Skill (SKILL.md) ✅
   │ reddit    ✅ │              │          • Web dashboard          ✅
   │ youtube   ✅ │       render md/html/json + compare
   │ x         ✅ │       --store SQLite ──► trends.py / watchlist.py (alerts)
   └──────────────┘       --demo: built-in seed data (no network/keys)
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

## Roadmap (all phases built)

| Phase | Scope | Status |
|---|---|---|
| 0/1 | Adapters, authenticity spine + account-age/karma, `--store` SQLite, name→id | ✅ |
| 2 | Thin `SKILL.md` wrapper, self-contained `.skill` build, plugin manifests | ✅ |
| 3 | Web dashboard: brief view, reputation-trend chart, HTML export | ✅ |
| 4 | Competitor diff, YouTube + X adapters, brand disambiguation | ✅ |
| v0.2 | Watchlist alerts, demo/POC mode, rating-text-mismatch + polarization detectors, Pantip search | ✅ |

Gated paths (X / Reddit-OAuth / Pantip-search) are validated end-to-end on
placeholder payloads; live credentials only feed real production data. Current
open items are tracked in [STATUS.md](STATUS.md).

## Open risks

- **Play Store batchexecute** parse is brittle by nature; fixture-backed now, but
  a Google template change can still break field extraction (degrades to `[]`).
- **X GraphQL** needs browser cookies and a query id that X rotates
  (`X_SEARCH_QUERY_ID` override); inherently fragile.
- **Brand disambiguation** is context-term based (host/user supplied), not a
  knowledge base — a tight exclude list is on the caller.
- **Pantip** RSS has no native query — matching is title/desc contains; the
  token-authed search API is the upgrade path.
