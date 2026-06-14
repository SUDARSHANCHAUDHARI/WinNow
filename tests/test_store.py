from datetime import datetime, timezone

from lib import store
from lib.schema import Authenticity, Brief, Item


def _brief(topic, trust_scores, when):
    items = [
        Item(source="appstore", item_id=f"{topic}-{i}", title=f"r{i}", text="body",
             rating=4.0, engagement=3.0,
             authenticity=Authenticity(score=t),
             published_at=datetime(2026, 6, 1, tzinfo=timezone.utc))
        for i, t in enumerate(trust_scores)
    ]
    return Brief(topic=topic, items=items, generated_at=when)


def test_save_and_timeseries_roundtrip():
    conn = store.connect(":memory:")
    store.save_run(conn, "Notion", ["appstore"],
                   _brief("Notion", [1.0, 0.8], datetime(2026, 6, 1, tzinfo=timezone.utc)))
    store.save_run(conn, "Notion", ["appstore"],
                   _brief("Notion", [0.3, 0.2], datetime(2026, 6, 8, tzinfo=timezone.utc)))

    series = store.trust_timeseries(conn, "Notion")
    assert len(series) == 2
    assert series[0]["avg_trust"] == 0.9
    assert series[1]["avg_trust"] == 0.25
    assert series[1]["suspicious"] == 2  # both <0.45 -> suspicious label
    assert series[0]["avg_rating"] == 4.0
    # ordered by timestamp
    assert series[0]["ts"] < series[1]["ts"]


def test_topic_isolation():
    conn = store.connect(":memory:")
    store.save_run(conn, "Notion", ["appstore"], _brief("Notion", [1.0], datetime(2026, 6, 1, tzinfo=timezone.utc)))
    store.save_run(conn, "Obsidian", ["appstore"], _brief("Obsidian", [0.5], datetime(2026, 6, 1, tzinfo=timezone.utc)))
    assert len(store.trust_timeseries(conn, "Notion")) == 1
    assert len(store.trust_timeseries(conn, "Obsidian")) == 1


def test_empty_run_safe():
    conn = store.connect(":memory:")
    rid = store.save_run(conn, "Empty", ["reddit"],
                         Brief(topic="Empty", items=[], generated_at=datetime(2026, 6, 1, tzinfo=timezone.utc)))
    assert rid >= 1
    series = store.trust_timeseries(conn, "Empty")
    assert series[0]["item_count"] == 0
    assert series[0]["avg_rating"] is None
