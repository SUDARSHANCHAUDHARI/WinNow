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
([`engine/lib/authenticity.py`](engine/lib/authenticity.py)). v0 detectors:

- **review-burst** — a spike of items on one day/version = coordinated push
- **near-duplicate** — templated/copy-pasted text = astroturf
- **thin-text** — "great app!!!" carries little signal
- **anon / generated-handle** — missing or auto-looking author

Ranking applies a **trust gate** so 500 upvotes at 0.2 trust rank below 50 at
1.0 trust ([`engine/lib/fusion.py`](engine/lib/fusion.py)). Adding Reddit
account-age/karma later is a new detector, not a rewrite.

## Status

MVP. App Store adapter is live-validated and fully working. Play Store
(batchexecute RPC) and Pantip (RSS) are wired with defensive parsers.
Reddit/X and the web dashboard are next — see [ARCHITECTURE.md](ARCHITECTURE.md).

```bash
python3 -m pytest -q     # 10 tests
```

## Sources validated (live probes, 2026-06)

- App Store customer reviews RSS — HTTP 200, zero auth ✅
- Play Store `batchexecute` UsvDTd RPC — HTTP 200 ✅
- Pantip RSS — HTTP 200 keyless ✅

MIT. Requires Python 3.9+ (zero runtime dependencies).
