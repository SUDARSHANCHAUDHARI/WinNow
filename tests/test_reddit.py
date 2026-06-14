"""Reddit adapter — Atom feed parsing (fixture) + failure degradation."""

from pathlib import Path

from lib.adapters import reddit

_FIXTURE = (Path(__file__).parent / "fixtures" / "reddit_search.rss").read_text()


def test_parses_atom_entries(monkeypatch):
    monkeypatch.setattr(reddit.http, "get", lambda *a, **k: _FIXTURE)
    items = reddit.fetch("Notion", limit=10)
    assert len(items) == 2

    first = items[0]
    assert first.source == "reddit"
    assert first.title == "Sync finally works on iOS"
    assert first.author == "/u/note_taker_99"
    assert first.metadata["subreddit"] == "r/Notion"
    assert "sync is finally reliable" in first.text
    assert first.url.endswith("/sync_finally_works/")
    assert first.published_at is not None and first.published_at.year == 2026
    assert first.engagement == 0.0  # RSS has no score, honestly

    assert items[1].metadata["subreddit"] == "r/productivity"


def test_http_failure_returns_empty(monkeypatch):
    def boom(*a, **k):
        raise reddit.http.HTTPError("403")
    monkeypatch.setattr(reddit.http, "get", boom)
    assert reddit.fetch("anything") == []


def test_registered():
    from lib.adapters import REGISTRY
    assert REGISTRY["reddit"] is reddit
