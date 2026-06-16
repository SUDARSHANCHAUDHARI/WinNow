#!/usr/bin/env python3
"""Winnow CLI — last-30-days research weighted by authenticity, not raw engagement.

Usage:
    python3 engine/winnow.py "Notion" --sources appstore
    python3 engine/winnow.py com.whatsapp --sources playstore
    python3 engine/winnow.py "ChatGPT" --sources appstore,pantip --limit 20
"""

from __future__ import annotations

import argparse
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib import authenticity, fusion, relevance, render, render_html, render_json
from lib.adapters import REGISTRY
from lib.schema import Brief, Item

# Keyword-search sources are brand-ambiguous ("Notion" app vs band); review
# sources are fetched by app id so they are unambiguous and never context-filtered.
KEYWORD_SOURCES = {"reddit", "youtube", "x", "pantip"}


def gather(topic: str, sources: list[str], *, lookback_days: int, limit: int) -> list[Item]:
    items: list[Item] = []
    with ThreadPoolExecutor(max_workers=max(1, len(sources))) as ex:
        futures = {
            ex.submit(REGISTRY[s].fetch, topic, lookback_days=lookback_days, limit=limit): s
            for s in sources if s in REGISTRY
        }
        for fut in as_completed(futures):
            src = futures[fut]
            try:
                items.extend(fut.result())
            except Exception as exc:  # one dead source never kills the run
                print(f"[{src}] failed: {exc}", file=sys.stderr)
    return items


def _within_window(items: list[Item], lookback_days: int) -> list[Item]:
    """Drop items older than the lookback window. Items with no date are kept
    (we cannot prove they are stale). This is the 'last-30-days' guarantee -
    Reddit's RSS in particular mixes in subreddit pages dated years ago."""
    kept = []
    for it in items:
        age = it.age_days()
        if age is None or age <= lookback_days:
            kept.append(it)
    return kept


def _disambiguate(items: list[Item], include: list[str], exclude: list[str]) -> list[Item]:
    """Apply context filtering to keyword-source items only."""
    if not include and not exclude:
        return items
    kept = []
    for it in items:
        if it.source not in KEYWORD_SOURCES:
            kept.append(it)
            continue
        ctx = " ".join([it.title, it.text,
                        str(it.metadata.get("subreddit", "")),
                        str(it.metadata.get("channel", ""))])
        if relevance.passes_context(ctx, include, exclude):
            kept.append(it)
    return kept


def build_brief(topic: str, sources: list[str], *, lookback_days: int, limit: int,
                context_include: list[str] | None = None,
                context_exclude: list[str] | None = None) -> Brief:
    raw = gather(topic, sources, lookback_days=lookback_days, limit=limit * 3)
    raw = _within_window(raw, lookback_days)
    raw = _disambiguate(raw, context_include or [], context_exclude or [])
    authenticity.score_corpus(raw)
    ranked = fusion.rank(raw, limit=limit)
    brief = Brief(topic=topic, items=ranked)
    pol = authenticity.rating_polarization(raw)
    if pol is not None and pol >= 0.7:
        brief.warnings.append(
            f"Ratings are {pol:.0%} polarized (1/5-star extremes) - a manipulation signature."
        )
    trust = fusion.corpus_trust(raw)
    if trust < 0.6 and raw:
        brief.warnings.append(
            f"Low corpus trust ({trust:.0%}) — heavy burst/duplicate signals; "
            f"treat engagement numbers with suspicion."
        )
    if not raw:
        brief.warnings.append("No items retrieved. Check the topic/app id or source availability.")
    return brief


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="winnow")
    p.add_argument("topic", nargs="?", help="app name, package id, or free-text topic")
    p.add_argument("--demo", action="store_true",
                   help="run on built-in seed data (no network/keys) for a POC demo")
    p.add_argument("--seed-store", action="store_true",
                   help="write backdated demo runs into the store (for the dashboard trend), then exit")
    p.add_argument("--sources", default="appstore",
                   help=f"comma list: {', '.join(REGISTRY)}")
    p.add_argument("--limit", type=int, default=25)
    p.add_argument("--lookback-days", type=int, default=30)
    p.add_argument("--emit", choices=["md", "html", "json"], default="md")
    p.add_argument("--out", help="write to this path instead of stdout")
    p.add_argument("--store", action="store_true",
                   help="persist this run to the SQLite store for trend tracking")
    p.add_argument("--store-path", help="override the SQLite db path")
    p.add_argument("--vs", action="append", default=[],
                   help="compare against another entity (repeatable): --vs Obsidian")
    p.add_argument("--context-include",
                   help="disambiguation: keyword-source items must mention one of these (comma list)")
    p.add_argument("--context-exclude",
                   help="disambiguation: drop keyword-source items mentioning any of these (comma list)")
    args = p.parse_args(argv)

    from lib import store as _store

    if args.seed_store:
        from lib import demo
        db = args.store_path or _store.default_db_path()
        n = demo.seed_store(str(db), weeks=4)
        print(f"seeded {n} demo runs for '{demo.DEMO_TOPIC}' -> {db}", file=sys.stderr)
        return 0

    sources = [s.strip() for s in args.sources.split(",") if s.strip()]
    unknown = [s for s in sources if s not in REGISTRY]
    if unknown:
        print(f"unknown sources: {unknown}. available: {list(REGISTRY)}", file=sys.stderr)
        return 2

    def _csv(v: str | None) -> list[str]:
        return [t.strip() for t in v.split(",") if t.strip()] if v else []
    ctx_in, ctx_ex = _csv(args.context_include), _csv(args.context_exclude)

    if args.demo:
        from lib import demo
        demo_sources = sources if args.sources != "appstore" else ["appstore", "reddit", "youtube", "x", "pantip"]
        brief = demo.build_brief(demo_sources)
        output = (render_html.to_html(brief) if args.emit == "html"
                  else render_json.to_json(brief) if args.emit == "json"
                  else render.to_markdown(brief))
        if args.out:
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.out).write_text(output, encoding="utf-8")
            print(args.out)
        else:
            print(output)
        return 0

    if not args.topic:
        print("error: topic is required (or use --demo / --seed-store)", file=sys.stderr)
        return 2

    if args.vs:
        from lib import compare
        entities = [args.topic, *args.vs]
        summaries = []
        for ent in entities:
            b = build_brief(ent, sources, lookback_days=args.lookback_days, limit=args.limit,
                            context_include=ctx_in, context_exclude=ctx_ex)
            summaries.append(compare.summarize(b))
        result = compare.compare(summaries)
        if args.emit == "json":
            import json
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(compare.to_markdown(result))
        return 0

    brief = build_brief(args.topic, sources, lookback_days=args.lookback_days, limit=args.limit,
                        context_include=ctx_in, context_exclude=ctx_ex)

    if args.store:
        from lib import store
        db = args.store_path or store.default_db_path()
        conn = store.connect(db)
        run_id = store.save_run(conn, args.topic, sources, brief)
        conn.close()
        print(f"stored run #{run_id} -> {db}", file=sys.stderr)

    if args.emit == "html":
        output = render_html.to_html(brief)
    elif args.emit == "json":
        output = render_json.to_json(brief)
    else:
        output = render.to_markdown(brief)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(output, encoding="utf-8")
        print(args.out)
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
