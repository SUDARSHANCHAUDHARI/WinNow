"""Pantip adapter — search-API parsing + RSS fallback (offline)."""

from lib.adapters import pantip


def test_search_api_parses_results(monkeypatch):
    payload = {"data": [
        {"topic_id": 4242, "title": "รีวิว Acme Notes", "detail": "ใช้ดีมาก",
         "author": "somchai", "timestamp": 1781200000, "comments_count": 12},
        {"id": "x", "title": ""},  # malformed -> skipped
    ]}
    monkeypatch.setattr(pantip.http, "get_json", lambda *a, **k: payload)
    items = pantip._search_api("Acme Notes", "tok", 10)
    assert len(items) == 1
    it = items[0]
    assert it.source == "pantip"
    assert it.item_id == "4242"
    assert it.url.endswith("/topic/4242")
    assert it.engagement == 12.0
    assert it.metadata["via"] == "search-api"


def test_search_api_failure_returns_empty(monkeypatch):
    monkeypatch.setattr(pantip.http, "get_json",
                        lambda *a, **k: (_ for _ in ()).throw(pantip.http.HTTPError("401")))
    assert pantip._search_api("x", "tok", 5) == []


def test_fetch_uses_rss_when_no_token(monkeypatch):
    monkeypatch.setattr(pantip.env, "get", lambda cfg, key: None)  # no PANTIP_AUTH
    called = {"api": False}
    monkeypatch.setattr(pantip, "_search_api",
                        lambda *a, **k: called.__setitem__("api", True) or [])
    monkeypatch.setattr(pantip.http, "get", lambda *a, **k: "<rss></rss>")
    pantip.fetch("Acme Notes")
    assert called["api"] is False  # token absent -> API path skipped
