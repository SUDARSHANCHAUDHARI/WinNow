#!/usr/bin/env python3
"""Winnow watchlist: alert when a tracked app's reputation moves.

Reads the SQLite store written by `winnow --store` and, per topic, compares the
two most recent runs. Fires alerts on a meaningful trust drop, rating drop, or
spike in suspicious (astroturf) items - the "monitor my app" use case that a
stateless tool like last30days cannot serve.

Usage:
    python3 engine/watchlist.py                 # check every topic in the store
    python3 engine/watchlist.py --topic "Acme Notes" --emit json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib import store

TRUST_DROP = 0.10      # avg trust fell by >= this
RATING_DROP = 0.30     # avg rating fell by >= this (out of 5)
SUSPICIOUS_RISE = 3    # suspicious-item count rose by >= this


def _topics(conn) -> list[str]:
    return [r["topic"] for r in conn.execute("SELECT DISTINCT topic FROM runs ORDER BY topic")]


def check_topic(conn, topic: str) -> list[dict]:
    series = store.trust_timeseries(conn, topic)
    if len(series) < 2:
        return []
    prev, cur = series[-2], series[-1]
    alerts: list[dict] = []

    trust_delta = (cur["avg_trust"] or 0) - (prev["avg_trust"] or 0)
    if -trust_delta >= TRUST_DROP:
        alerts.append({"topic": topic, "kind": "trust-drop", "severity": "high",
                       "message": f"avg trust fell {prev['avg_trust']} -> {cur['avg_trust']} "
                                  f"({trust_delta:+.2f}) since {prev['ts'][:10]}"})

    if prev["avg_rating"] is not None and cur["avg_rating"] is not None:
        rating_delta = cur["avg_rating"] - prev["avg_rating"]
        if -rating_delta >= RATING_DROP:
            alerts.append({"topic": topic, "kind": "rating-drop", "severity": "medium",
                           "message": f"avg rating fell {prev['avg_rating']} -> {cur['avg_rating']} "
                                      f"({rating_delta:+.2f})"})

    susp_delta = cur["suspicious"] - prev["suspicious"]
    if susp_delta >= SUSPICIOUS_RISE:
        alerts.append({"topic": topic, "kind": "astroturf-spike", "severity": "high",
                       "message": f"suspicious items rose {prev['suspicious']} -> {cur['suspicious']} "
                                  f"(+{susp_delta}) - possible coordinated push"})
    return alerts


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="winnow-watchlist")
    p.add_argument("--topic", help="check a single topic (default: all in the store)")
    p.add_argument("--store-path")
    p.add_argument("--emit", choices=["text", "json"], default="text")
    args = p.parse_args(argv)

    db = Path(args.store_path) if args.store_path else store.default_db_path()
    if not db.exists():
        print(f"no store at {db} - run `winnow ... --store` (or --seed-store) first", file=sys.stderr)
        return 1
    conn = store.connect(db)
    topics = [args.topic] if args.topic else _topics(conn)
    alerts = [a for t in topics for a in check_topic(conn, t)]
    conn.close()

    if args.emit == "json":
        print(json.dumps({"alerts": alerts}, ensure_ascii=False, indent=2))
        return 0
    if not alerts:
        print("✅ no alerts - all tracked topics steady")
        return 0
    icon = {"high": "🚩", "medium": "⚠️"}
    for a in alerts:
        print(f"{icon.get(a['severity'], '•')} [{a['kind']}] {a['topic']}: {a['message']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
