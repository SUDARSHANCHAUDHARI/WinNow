import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "engine"))

import watchlist
from lib import store
from lib.schema import Authenticity, Brief, Item


def _run(conn, topic, trust, rating, suspicious, day):
    items = []
    for i in range(10):
        lbl_trust = 0.2 if i < suspicious else 1.0
        items.append(Item(source="appstore", item_id=f"{topic}{day}{i}", title="t", text="b",
                          rating=rating, engagement=2.0,
                          authenticity=Authenticity(score=lbl_trust),
                          published_at=datetime(2026, 6, 1, tzinfo=timezone.utc)))
    b = Brief(topic=topic, items=items, generated_at=datetime(2026, 6, day, tzinfo=timezone.utc))
    # force the run-level avg_trust the timeseries reads
    b.items[0].authenticity.score = b.items[0].authenticity.score  # no-op clarity
    store.save_run(conn, topic, ["appstore"], b)


def test_astroturf_spike_alert():
    conn = store.connect(":memory:")
    _run(conn, "App", trust=1.0, rating=4.5, suspicious=1, day=1)
    _run(conn, "App", trust=0.6, rating=4.5, suspicious=6, day=8)
    alerts = watchlist.check_topic(conn, "App")
    kinds = {a["kind"] for a in alerts}
    assert "astroturf-spike" in kinds


def test_rating_drop_alert():
    conn = store.connect(":memory:")
    _run(conn, "App", trust=1.0, rating=4.6, suspicious=0, day=1)
    _run(conn, "App", trust=1.0, rating=4.0, suspicious=0, day=8)
    alerts = watchlist.check_topic(conn, "App")
    assert any(a["kind"] == "rating-drop" for a in alerts)


def test_no_alert_when_steady():
    conn = store.connect(":memory:")
    _run(conn, "App", trust=1.0, rating=4.5, suspicious=0, day=1)
    _run(conn, "App", trust=0.98, rating=4.5, suspicious=0, day=8)
    assert watchlist.check_topic(conn, "App") == []


def test_single_run_no_alert():
    conn = store.connect(":memory:")
    _run(conn, "App", trust=1.0, rating=4.5, suspicious=0, day=1)
    assert watchlist.check_topic(conn, "App") == []
