# Winnow — Status

_Last updated 2026-06-16 · v0.2 (four phases + POC demo, watchlist, extra detectors)_

## What Winnow is

A focused alternative to [last30days-skill](https://github.com/mvanhorn/last30days-skill):
same "what are real people saying in the last 30 days" concept, but it ranks by
**authenticity** (not raw engagement) and covers the sources last30days skips
(App Store + Play Store reviews, Pantip/Thailand). One Python engine, two
surfaces (agent skill + web dashboard).

## Build state — plan complete (Phases 1–4)

| Phase | Tasks | Status |
|-------|-------|--------|
| 1 Engine depth & trust | T1 Play Store hardening · T2 Reddit feed · T3 account-age trust · T4 SQLite store · T5 name→id | ✅ |
| 2 Distribution | T6 self-contained skill · T7 `.skill` build + install docs · T8 CI | ✅ (T8 **deferred — gated**) |
| 3 Web dashboard | T9 scaffold · T10 engine API · T11 brief view · T12 trend chart · T13 HTML export | ✅ |
| 4 Differentiators | T14 competitor diff · T15 YouTube + X adapters | ✅ |

### v0.2 additions
- **POC demo mode** — `winnow --demo` runs on built-in seed data (no network/keys);
  the seed exercises every detector. Dashboard has a **Try the demo** button
  (`/api/demo`) that seeds the store and shows brief + trend in one click.
- **Watchlist + alerts** — `engine/watchlist.py` compares the last two stored runs
  per topic and alerts on trust drop / rating drop / astroturf spike.
- **Extra authenticity detectors** — `rating-text-mismatch` (5★ + negative text)
  and a corpus `rating-polarization` warning (1/5-star manipulation signature).
- **Pantip search API** — real keyword search, gated on `PANTIP_AUTH`, RSS fallback.

68 engine tests passing. Web typecheck + lint clean.

## Architecture (see ARCHITECTURE.md)

```
adapters (6) ─► authenticity.score_corpus ─► fusion.rank (trust-gated)
   │                                              │
   │                          ┌───────────────────┼──────────────┐
appstore playstore            ▼                   ▼              ▼
pantip reddit            --store SQLite     render md/html/json  compare
youtube x                      │                   │              │
                               └──► winnow-web (Next.js dashboard)
```

- **Engine**: `engine/winnow.py` (CLI) + `engine/lib/*` (zero runtime deps, Python 3.9+).
- **Authenticity spine** (`authenticity.py`): burst, near-duplicate, thin-text,
  anon/generated-handle, new-account, low-karma (last two via Reddit OAuth).
- **Skill**: `skills/winnow/SKILL.md` (thin), engine symlinked in; `build-skill.sh` bundles.
- **Web**: `winnow-web/` — brief view, trust bars, reputation-trend chart, HTML export.

## Sources

| Source | Path | Auth |
|--------|------|------|
| App Store reviews | iTunes RSS | none |
| Play Store reviews | batchexecute RPC | none |
| Reddit | search.rss (keyless) → OAuth enrich | optional `.env` |
| Pantip (Thailand) | RSS (keyless) → search API | optional `PANTIP_AUTH` |
| YouTube | ytInitialData scrape | none |
| X / Twitter | GraphQL search | requires `AUTH_TOKEN`+`CT0` cookies |

## Run it

```bash
python3 engine/winnow.py "Notion" --sources appstore,reddit --limit 25
python3 engine/winnow.py "Notion" --vs "Obsidian" --sources appstore   # competitor diff
python3 engine/winnow.py "Slack" --sources appstore --store            # persist for trends
python3 engine/winnow.py --demo                                        # POC seed data, no keys
python3 engine/winnow.py --seed-store && python3 engine/watchlist.py   # seed + reputation alerts
cd winnow-web && pnpm dev                                              # dashboard :3000 (Try the demo)
python3 -m pytest -q                                                    # 68 tests
bash build-skill.sh                                                     # dist/winnow.skill
```

## Open threads

- **CI** (T8): pytest-on-push workflow. Blocked by hook + global rule; needs an
  explicit "add CI" instruction.
- ~~**Brand disambiguation**~~: DONE - `--context-include` / `--context-exclude`
  filter keyword sources (reddit/youtube/x/pantip); the host model supplies the
  terms (SKILL.md). Review sources are unambiguous and never filtered.
- ~~**Cross-source engagement normalization**~~: DONE - `fusion.rank` now scores
  engagement per-source (log-normalized vs each source's top item), so YouTube's
  millions no longer crush a 50-helpful review, PLUS a per-source diversity floor
  (`min_per_source=2`) so a zero-engagement source (Reddit RSS) is not shut out of
  a mixed run. Mixed appstore+reddit run went from 7:1 to 6:2.
- ~~**Dashboard feature parity**~~: DONE - the web UI now exposes competitor diff
  (`/api/compare` + CompareView, "Compare vs…" input) and disambiguation
  ("Exclude terms…" input), matching the engine/CLI.
- **X query-id rotation**: the GraphQL query id is hard-coded with an env override
  (`X_SEARCH_QUERY_ID`); will need updating when X changes it.
- ~~**git repo**~~: DONE - shipped to https://github.com/SUDARSHANCHAUDHARI/WinNow
  (private), `main` is the source of truth.

## Bugs caught by live-run discipline

burst false-positive on recency slices · stale-date leak (2018 items in a 30-day
tool) · Reddit spam results (sort=new firehose) · manufactured-tie verdict in
compare · brace typo in a test fixture. None would have surfaced from unit tests
alone.
