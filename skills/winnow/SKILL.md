---
name: winnow
version: "0.1.0"
description: "Research what real people say about an app or topic in the last 30 days, ranked by authenticity not raw engagement. Covers App Store + Play Store reviews and Pantip (Thailand) — sources other tools skip."
argument-hint: 'winnow Notion | winnow com.whatsapp --sources playstore | winnow ChatGPT for slack'
allowed-tools: Bash, Read
homepage: https://github.com/SUDARSHANCHAUDHARI/winnow
license: MIT
user-invocable: true
---

# Winnow

Winnow runs a headless Python engine that pulls last-30-days content from
review sources and regional platforms, scores every item for **authenticity**
(burst / duplicate / thin-text / anonymous detectors), and ranks by
authenticity-weighted engagement. Your job is to run the engine, read its
structured markdown, and synthesize a short honest brief.

The engine does the retrieval, scoring, and ranking. You do the prose. Do not
re-rank, re-score, or invent data — the trust labels are computed, trust them.

## Run the engine

Resolve `SKILL_DIR` to the directory of this SKILL.md, then locate the engine.
It lives in one of two known spots - bundled inside the skill (standalone
installs) or two levels up (repo checkout). Check both, no open-ended search:

```bash
ENGINE=""
for cand in "$SKILL_DIR/engine/winnow.py" "$SKILL_DIR/../../engine/winnow.py"; do
  [ -f "$cand" ] && ENGINE="$cand" && break
done
python3 "$ENGINE" "<TOPIC>" --sources <sources> --limit 25
```

- **Default sources:** `appstore` for an app name; `appstore,pantip` if the user
  wants regional/Thailand signal; `playstore` when the topic is a package id
  (contains dots, e.g. `com.whatsapp`).
- App names resolve to an App Store id automatically. Package ids go to Play Store.
- One dead source never fails the run; it logs to stderr and continues.

**Disambiguate ambiguous brands.** When the topic is a word that also means
something else (Notion the app vs the band; Apple the company vs the fruit) and
you are using a keyword source (`reddit`, `youtube`, `x`, `pantip`), YOU know
which sense is meant - so pass it through:

```bash
--context-exclude "song,lyrics,album,music video,band,movie,trailer"
--context-include "app,software,workspace,update,feature"
```

These filters apply ONLY to keyword sources (review sources are fetched by app
id and are already unambiguous). Supply a tight exclude list for any topic whose
name collides with an unrelated common sense. Both flags are no-ops if omitted.

## Read the output

The engine prints a markdown brief: a header, optional `⚠️` corpus warnings, then
ranked items. Each item carries:

- a source tag (`appstore` / `playstore` / `pantip`)
- `N★` rating (review sources)
- `trust 0.00–1.00` with a label: ✅ trusted · ⚠️ mixed · 🚩 suspicious
- `flags:` the authenticity signals that fired (e.g. `review-burst, near-duplicate`)

A corpus warning like *"Low corpus trust (48%)"* means the engagement is heavily
gamed — say so plainly in your brief.

## Synthesize the brief

Emit, in this order:

1. **One-line headline** of what real users are actually saying this month.
2. **What's working / what's broken** — 2–4 bullet points, each grounded in a
   cited review. Link every citation as `[source](url)`.
3. **Trust note** — if any high-ranked items are flagged or corpus trust is low,
   call it out: "N of the top items show coordinated-push signals."
4. **The receipts** — pass through the engine's ranked list (or the top 5–8).

Rules, kept short on purpose:
- Never fabricate a review, rating, or number. If the engine returned nothing, say so.
- Every quote comes from the engine output. Every link is a real `[text](url)`.
- Lead with the authenticity story — it is the whole point of this tool.
- No em-dashes in your own prose; use ` - `.

That's it. The engine is the contract; this file is thin by design.
