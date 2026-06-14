#!/usr/bin/env python3
"""Emit a topic's stored trust/rating timeseries as JSON (for the dashboard).

Reads the SQLite store written by `winnow --store`. Returns an empty series
(not an error) when the store or topic has no history yet.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib import store


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="winnow-trends")
    p.add_argument("topic")
    p.add_argument("--store-path")
    args = p.parse_args(argv)

    db = Path(args.store_path) if args.store_path else store.default_db_path()
    if not db.exists():
        print(json.dumps({"topic": args.topic, "series": []}))
        return 0

    conn = store.connect(db)
    series = store.trust_timeseries(conn, args.topic)
    conn.close()
    print(json.dumps({"topic": args.topic, "series": series}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
