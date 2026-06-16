# Winnow

**Last-30-days research weighted by authenticity, not raw engagement.**

A focused answer to [last30days-skill](https://github.com/mvanhorn/last30days-skill): same "what are real people saying" concept, but it fixes the loophole that engagement *is* the score with no check that the engagement is real, and it covers the sources last30days can't — **app-store reviews** and **regional walled gardens** (Pantip/Thailand).

```bash
python3 engine/winnow.py "Notion" --sources appstore --limit 10
python3 engine/winnow.py com.whatsapp --sources playstore
python3 engine/winnow.py "ChatGPT" --sources appstore,pantip
```

## Install

**Claude Code (plugin):**
```
/plugin marketplace add <your-org>/winnow
/plugin install winnow
```
The plugin install fetches the whole repo, so the skill resolves the engine via
the repo-checkout fallback - nothing else to do.

**Agent Skills hosts (Codex, Cursor, Gemini CLI, …):**
```
npx skills add <your-org>/winnow -g
```

**claude.ai (web) or any manual upload:** build a self-contained bundle and
upload `dist/winnow.skill` via Settings → Capabilities → Skills:
```
bash build-skill.sh
```

**Manual (developer):**
```
git clone <repo> && cd winnow
ln -s "$(pwd)/skills/winnow" ~/.claude/skills/winnow   # engine resolves via the in-repo symlink
```

Reddit (RSS), App Store, Play Store, and Pantip work with zero configuration.
Add a free Reddit OAuth app to `.env` (see `.env.example`) to unlock real upvote
scores plus account-age authenticity signals.

### Web dashboard (optional)
```
cd winnow-web && pnpm install && pnpm dev   # http://localhost:3000
```

## Why it's different

| last30days | Winnow |
|---|---|
| Engagement = score, no bot/astroturf filter | **Authenticity score on every item**; ranking gates on trust |
| Reddit/X/YouTube/TikTok/… | Adds **App Store + Play Store reviews** and **Pantip (Thailand)** |
| Undocumented `/svc/shreddit/` scraping | Official-API/RSS-first; degrades to `[]`, never crashes |
| 1,700-line behavioral SKILL.md | Determinism lives in the engine; the skill wrapper stays thin |

## The spine: authenticity

Every `Item` carries a `0..1` trust score plus the signals that produced it
([`engine/lib/authenticity.py`](engine/lib/authenticity.py)). Detectors:

- **review-burst** — a spike of items on one day/version = coordinated push
- **near-duplicate** — templated/copy-pasted text = astroturf
- **thin-text** — "great app!!!" carries little signal
- **anon / generated-handle** — missing or auto-looking author
- **new-account** / **low-karma** — Reddit OAuth enrichment (dormant until keyed)

Ranking ([`engine/lib/fusion.py`](engine/lib/fusion.py)) applies a **trust gate**
(500 upvotes at 0.2 trust rank below 50 at 1.0 trust), **per-source engagement
normalization** (so a million-view video does not crush a 50-helpful review),
and a **diversity floor** so no source is shut out of a mixed run.

```bash
python3 engine/winnow.py "Notion" --vs "Obsidian" --sources appstore   # competitor diff
python3 engine/winnow.py "Notion" --sources reddit,youtube \
  --context-exclude "song,band,movie"                                  # disambiguation
```

## Status

All four planned phases are built. 6 source adapters (App Store, Play Store,
Pantip, Reddit, YouTube, X), the authenticity spine, SQLite persistence, and
competitor diff. Two surfaces: the agent skill and a Next.js dashboard (brief
view, trust bars, reputation-trend chart, HTML export, competitor diff). See
[STATUS.md](STATUS.md) for the full scorecard.

Reddit OAuth enrichment and the X adapter are code-complete but dormant until you
add credentials (see `.env.example`).

```bash
python3 -m pytest -q     # 69 tests
```

## Sources validated (live probes, 2026-06)

- App Store customer reviews RSS — HTTP 200, zero auth ✅
- Play Store `batchexecute` UsvDTd RPC — HTTP 200 ✅
- Pantip RSS — HTTP 200 keyless ✅

MIT. Requires Python 3.9+ (zero runtime dependencies).
