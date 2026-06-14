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

from lib import authenticity, fusion, render, render_html, render_json
from lib.adapters import REGISTRY
from lib.schema import Brief, Item


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


def build_brief(topic: str, sources: list[str], *, lookback_days: int, limit: int) -> Brief:
    raw = gather(topic, sources, lookback_days=lookback_days, limit=limit * 3)
    raw = _within_window(raw, lookback_days)
    authenticity.score_corpus(raw)
    ranked = fusion.rank(raw, limit=limit)
    brief = Brief(topic=topic, items=ranked)
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
    p.add_argument("topic", help="app name, package id, or free-text topic")
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
    args = p.parse_args(argv)

    sources = [s.strip() for s in args.sources.split(",") if s.strip()]
    unknown = [s for s in sources if s not in REGISTRY]
    if unknown:
        print(f"unknown sources: {unknown}. available: {list(REGISTRY)}", file=sys.stderr)
        return 2

    if args.vs:
        from lib import compare
        entities = [args.topic, *args.vs]
        summaries = []
        for ent in entities:
            b = build_brief(ent, sources, lookback_days=args.lookback_days, limit=args.limit)
            summaries.append(compare.summarize(b))
        result = compare.compare(summaries)
        if args.emit == "json":
            import json
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(compare.to_markdown(result))
        return 0

    brief = build_brief(args.topic, sources, lookback_days=args.lookback_days, limit=args.limit)

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
