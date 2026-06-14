"""SQLite persistence for Winnow runs.

Each run snapshots its ranked items with their trust scores and a timestamp,
so the dashboard can chart how an app's reputation (and the authenticity of
the conversation around it) moves over time - the thing last30days, being
stateless per run, cannot do. stdlib sqlite3 only.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .schema import Brief

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  topic TEXT NOT NULL,
  sources TEXT NOT NULL,
  ts TEXT NOT NULL,
  item_count INTEGER NOT NULL,
  avg_trust REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS items(
  run_id INTEGER NOT NULL,
  source TEXT, item_id TEXT, title TEXT, text TEXT, url TEXT, author TEXT,
  published_at TEXT, engagement REAL, rating REAL,
  trust REAL, trust_label TEXT, flags TEXT,
  FOREIGN KEY(run_id) REFERENCES runs(id)
);
CREATE INDEX IF NOT EXISTS idx_runs_topic ON runs(topic);
"""


def connect(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    if str(path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def save_run(conn: sqlite3.Connection, topic: str, sources: list[str], brief: Brief) -> int:
    items = brief.items
    avg_trust = (sum(i.authenticity.score for i in items) / len(items)) if items else 1.0
    ts = brief.generated_at.astimezone(timezone.utc).isoformat()
    cur = conn.execute(
        "INSERT INTO runs(topic, sources, ts, item_count, avg_trust) VALUES (?,?,?,?,?)",
        (topic, ",".join(sources), ts, len(items), avg_trust),
    )
    run_id = cur.lastrowid
    conn.executemany(
        """INSERT INTO items(run_id, source, item_id, title, text, url, author,
           published_at, engagement, rating, trust, trust_label, flags)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        [
            (run_id, i.source, i.item_id, i.title, i.text, i.url, i.author,
             i.published_at.isoformat() if i.published_at else None,
             i.engagement, i.rating, i.authenticity.score, i.authenticity.label,
             json.dumps([s.name for s in i.authenticity.signals]))
            for i in items
        ],
    )
    conn.commit()
    return run_id


def trust_timeseries(conn: sqlite3.Connection, topic: str) -> list[dict]:
    """One point per stored run: trust + rating + suspicious share over time.

    This is the dashboard's core query - reputation movement, not a snapshot.
    """
    rows = conn.execute(
        "SELECT id, ts, item_count, avg_trust FROM runs WHERE topic=? ORDER BY ts",
        (topic,),
    ).fetchall()
    series = []
    for r in rows:
        agg = conn.execute(
            """SELECT AVG(rating) AS avg_rating,
                      SUM(CASE WHEN trust_label='suspicious' THEN 1 ELSE 0 END) AS suspicious
               FROM items WHERE run_id=?""",
            (r["id"],),
        ).fetchone()
        series.append({
            "run_id": r["id"],
            "ts": r["ts"],
            "item_count": r["item_count"],
            "avg_trust": round(r["avg_trust"], 3),
            "avg_rating": round(agg["avg_rating"], 2) if agg["avg_rating"] is not None else None,
            "suspicious": agg["suspicious"] or 0,
        })
    return series


def default_db_path() -> Path:
    import os
    base = os.environ.get("WINNOW_DB")
    if base:
        return Path(base)
    return Path.home() / "Documents" / "Winnow" / "winnow.db"
