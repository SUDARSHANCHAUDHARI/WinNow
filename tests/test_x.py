"""X adapter — cookie gating + defensive timeline parsing (offline)."""

from lib.adapters import x


def test_dormant_without_cookies(monkeypatch):
    monkeypatch.setattr(x.env, "load", lambda: {})
    assert x.fetch("Notion") == []


def test_credentials_gate():
    assert x._credentials({}) is None
    assert x._credentials({"AUTH_TOKEN": "a", "CT0": "c"}) == ("a", "c")
    assert x._credentials({"AUTH_TOKEN": "your_token_here", "CT0": "c"}) is None  # placeholder


_TIMELINE = {
    "data": {"search_by_raw_query": {"search_timeline": {"timeline": {"instructions": [
        {"entries": [
            {"content": {"itemContent": {"tweet_results": {"result": {
                "rest_id": "1789",
                "core": {"user_results": {"result": {"legacy": {"screen_name": "devguy"}}}},
                "legacy": {"full_text": "Notion just shipped offline mode, finally",
                            "favorite_count": 220, "retweet_count": 33,
                            "created_at": "Wed Jun 10 14:33:00 +0000 2026"},
            }}}}},
            {"content": {"itemContent": {"tweet_results": {"result": {
                "rest_id": "1790",
                "core": {"user_results": {"result": {"legacy": {"screen_name": "chef"}}}},
                "legacy": {"full_text": "best pasta recipe ever", "favorite_count": 5,
                            "retweet_count": 0, "created_at": "Wed Jun 10 10:00:00 +0000 2026"},
            }}}}},
        ]},
    ]}}}}}


def test_parse_timeline_extracts_and_filters():
    items = x.parse_timeline(_TIMELINE, "Notion")
    assert len(items) == 1  # pasta tweet filtered by relevance
    it = items[0]
    assert it.source == "x"
    assert it.author == "@devguy"
    assert it.engagement == 253.0  # likes + retweets
    assert it.url == "https://x.com/devguy/status/1789"
    assert it.published_at is not None and it.published_at.year == 2026


def test_fetch_full_path_with_cookies(monkeypatch):
    # End-to-end against a placeholder timeline: creds present -> token ->
    # search -> parse. Exercises the whole fetch() path without the real API.
    monkeypatch.setattr(x.env, "load", lambda: {"AUTH_TOKEN": "a", "CT0": "c"})
    monkeypatch.setattr(x.http, "get_json", lambda url, **k: _TIMELINE)
    items = x.fetch("Notion", limit=10)
    assert len(items) == 1
    assert items[0].source == "x" and items[0].author == "@devguy"
    assert items[0].engagement == 253.0


def test_registered():
    from lib.adapters import REGISTRY
    assert REGISTRY["x"] is x and "youtube" in REGISTRY
