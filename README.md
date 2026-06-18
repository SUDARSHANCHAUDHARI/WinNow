# Winnow

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![Runtime deps](https://img.shields.io/badge/runtime%20deps-0-3fb950)](pyproject.toml)
[![Tests](https://img.shields.io/badge/tests-69%20passing-3fb950)](tests)

**Last-30-days research weighted by authenticity, not raw engagement.**

A focused answer to [last30days-skill](https://github.com/mvanhorn/last30days-skill):
same "what are real people saying" idea, but Winnow fixes the loophole that
engagement *is* the score — with no check that the engagement is real — and it
covers sources last30days skips: **app-store reviews** and **regional walled
gardens** (Pantip/Thailand). Upvotes, likes, and review stars are the most gamed
metrics online; Winnow scores every item for authenticity and ranks by *who is
real*.

```bash
python3 engine/winnow.py "Notion" --sources appstore,reddit --limit 25
python3 engine/winnow.py --demo          # try it with zero setup (seed data, no keys)
```

## Features

- **Authenticity spine** — every result gets a 0–1 trust score from 8 detectors;
  ranking *gates* on trust, so a 500-upvote astroturf burst loses to a 50-upvote
  genuine thread.
- **6 sources** — App Store + Play Store reviews, Reddit, YouTube, X, and Pantip
  (Thailand). Official-API / RSS first; every adapter degrades to `[]` on failure
  rather than crashing.
- **Competitor diff** — `--vs` produces a side-by-side verdict ("higher rating,
  but the reviews are less authentic").
- **Reputation trend tracking** — persist runs to SQLite and chart trust / rating
  / astroturf-share over time. A watchlist alerts on trust drops and review bursts.
- **Brand disambiguation** — `--context-exclude` filters keyword sources so
  "Notion" the app isn't drowned out by "Notion" the band.
- **Two surfaces** — an Agent Skill (`/winnow`) for Claude Code / Codex / Cursor /
  Gemini CLI, and a Next.js dashboard with a one-click demo.
- **Shareable briefs** — emit Markdown, self-contained HTML, or JSON.

## Tech stack

- **Engine** — Python 3.9+, standard library only (**zero runtime dependencies**)
- **Storage** — SQLite (`--store`) for trend tracking
- **Dashboard** — Next.js 16, React 19, TypeScript, Tailwind CSS 4
- **Tests** — pytest (69 tests)

## Install

**Claude Code (plugin):**
```
/plugin marketplace add SUDARSHANCHAUDHARI/WinNow
/plugin install winnow
```

**Agent Skills hosts (Codex, Cursor, Gemini CLI, …):**
```
npx skills add SUDARSHANCHAUDHARI/WinNow -g
```

**claude.ai (web) / manual upload** — build a self-contained bundle and upload
`dist/winnow.skill` via Settings → Capabilities → Skills:
```
bash build-skill.sh
```

**Manual (developer):**
```
git clone https://github.com/SUDARSHANCHAUDHARI/WinNow.git && cd WinNow
ln -s "$(pwd)/skills/winnow" ~/.claude/skills/winnow   # engine resolves via the in-repo symlink
```

App Store, Play Store, Reddit (RSS), Pantip, and YouTube work with **zero
configuration**. Copy `.env.example` to `.env` and add keys to unlock the gated
paths (Reddit OAuth account-age signals, X search, Pantip search).

### Web dashboard (optional)
```
cd winnow-web && pnpm install && pnpm dev   # http://localhost:3000  → "Try the demo"
```

## Why it's different

| last30days | Winnow |
|---|---|
| Engagement = score, no bot/astroturf filter | **Authenticity score on every item**; ranking gates on trust |
| Reddit / X / YouTube / TikTok / … | Adds **App Store + Play Store reviews** and **Pantip (Thailand)** |
| Stateless per run | **Trend tracking + watchlist alerts** over stored runs |
| Undocumented `/svc/shreddit/` scraping | Official-API / RSS first; degrades to `[]`, never crashes |
| 1,700-line behavioral SKILL.md | Determinism lives in the engine; the skill wrapper stays thin |

## The spine: authenticity

Every `Item` carries a `0..1` trust score plus the signals that produced it
([`engine/lib/authenticity.py`](engine/lib/authenticity.py)):

- **review-burst** — a spike of items on one day/version = coordinated push
- **near-duplicate** — templated / copy-pasted text = astroturf
- **thin-text** — "great app!!!" carries little signal
- **anon / generated-handle** — missing or auto-looking author
- **new-account** / **low-karma** — Reddit OAuth enrichment (dormant until keyed)
- **rating-text-mismatch** — a 5★ review whose words read negative (the star was
  set to move the average while the text leaked the truth)
- **rating-polarization** — corpus warning when ratings cluster at the 1/5 extremes

Ranking ([`engine/lib/fusion.py`](engine/lib/fusion.py)) applies a **trust gate**,
**per-source engagement normalization** (so a million-view video doesn't crush a
50-helpful review), and a **diversity floor** so no source is shut out of a mixed run.

```bash
python3 engine/winnow.py "Notion" --vs "Obsidian" --sources appstore   # competitor diff
python3 engine/winnow.py "Notion" --sources reddit,youtube \
  --context-exclude "song,band,movie"                                  # disambiguation
python3 engine/winnow.py --seed-store && python3 engine/watchlist.py   # reputation alerts
python3 -m pytest -q                                                   # 69 tests
```

## Status

All four planned phases plus v0.2 (watchlist, demo mode, extra detectors) are
shipped.

**Live and keyless** — App Store, Play Store, Reddit (RSS), YouTube, and Pantip
(RSS) are validated against the real services and work with zero configuration.

**Keyed paths (stay dormant until you add credentials to `.env`):**
- **Reddit OAuth** (real scores + account-age signals) — built against Reddit's
  documented API; parser-tested, not yet run live.
- **X search** and **Pantip search API** — *experimental*. The parsers are tested
  against recorded payloads, but the live requests have not been verified end to
  end (X needs its full GraphQL feature set + current query id; Pantip's token
  format is unconfirmed). Expect to update these against a live response. Pantip
  works via RSS regardless.

See [STATUS.md](STATUS.md) for the full scorecard and [ARCHITECTURE.md](ARCHITECTURE.md)
for the design.

## License

[MIT](LICENSE) © 2026 Sudarshan Chaudhari (SudarshanTechLabs).
No tracking, no analytics — your research stays on your machine.

## Author

Built by **Sudarshan Chaudhari** — [SudarshanTechLabs](https://github.com/SUDARSHANCHAUDHARI).
