"""YouTube adapter — ytInitialData parsing + relative-date conversion (offline)."""

import json
from datetime import datetime, timezone

from lib.adapters import youtube


def _page(videos):
    data = {"contents": [{"videoRenderer": v} for v in videos]}
    return f"<html>var ytInitialData = {json.dumps(data)};</script></html>"


def test_parses_videos_and_views(monkeypatch):
    page = _page([
        {"videoId": "abc", "title": {"runs": [{"text": "Notion review 2026"}]},
         "ownerText": {"runs": [{"text": "TechChannel"}]},
         "viewCountText": {"simpleText": "12,345 views"},
         "publishedTimeText": {"simpleText": "2 weeks ago"}},
        {"videoId": "xyz", "title": {"runs": [{"text": "unrelated cooking video"}]},
         "ownerText": {"runs": [{"text": "FoodTV"}]},
         "viewCountText": {"simpleText": "9 views"},
         "publishedTimeText": {"simpleText": "1 day ago"}},
    ])
    monkeypatch.setattr(youtube.http, "get", lambda *a, **k: page)
    items = youtube.fetch("Notion", limit=10)
    # relevance gate drops the cooking video (no "notion")
    assert len(items) == 1
    it = items[0]
    assert it.source == "youtube"
    assert it.engagement == 12345.0
    assert it.url == "https://www.youtube.com/watch?v=abc"
    assert it.metadata["channel"] == "TechChannel"
    # "2 weeks ago" -> ~14 days old
    age = (datetime.now(timezone.utc) - it.published_at).days
    assert 12 <= age <= 16


def test_relative_date_units():
    assert youtube._approx_published("3 hours ago") is not None
    assert youtube._approx_published("no date here") is None
    yr = youtube._approx_published("1 year ago")
    assert (datetime.now(timezone.utc) - yr).days > 300


def test_http_failure_returns_empty(monkeypatch):
    monkeypatch.setattr(youtube.http, "get",
                        lambda *a, **k: (_ for _ in ()).throw(youtube.http.HTTPError("x")))
    assert youtube.fetch("Notion") == []
