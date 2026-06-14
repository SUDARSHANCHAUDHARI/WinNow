"""Play Store parser — fixture-backed (real batchexecute shape, anonymized) + drift guards."""

from pathlib import Path

from lib.adapters import playstore

_FIXTURE = Path(__file__).parent / "fixtures" / "playstore_batchexecute.txt"


def test_extract_reviews_from_real_shape():
    raw = _FIXTURE.read_text()
    reviews = playstore._extract_reviews(raw)
    assert len(reviews) == 2

    first = reviews[0]
    assert first["id"] == "rev-id-1"
    assert first["author"] == "Alice Tester"
    assert first["rating"] == 5
    assert "sync works great" in first["text"]
    assert first["helpful"] == 4
    assert first["version"] == "2.26.20.72"
    assert first["date"] is not None
    assert first["date"].year == 2026

    second = reviews[1]
    assert second["rating"] == 1
    assert second["author"] == "user_4821"
    assert "crashing" in second["text"]


def test_fetch_maps_fixture_to_items(monkeypatch):
    monkeypatch.setattr(playstore.http, "post", lambda *a, **k: _FIXTURE.read_text())
    items = playstore.fetch("com.whatsapp", limit=10)
    assert len(items) == 2
    assert items[0].source == "playstore"
    assert items[0].rating == 5.0
    assert items[0].engagement == 4.0  # helpful-count
    assert items[0].metadata["version"] == "2.26.20.72"
    assert items[0].url.endswith("id=com.whatsapp")


def test_garbage_response_returns_empty():
    # Shape drift / HTML error page must degrade to [], never crash (loophole #2 fix).
    assert playstore._extract_reviews("<html>blocked</html>") == []
    assert playstore._extract_reviews(")]}'\n\n[[\"wrb.fr\"]]") == []
    assert playstore._extract_reviews("") == []


def test_http_failure_returns_empty(monkeypatch):
    def boom(*a, **k):
        raise playstore.http.HTTPError("429")
    monkeypatch.setattr(playstore, "resolve_package_id", lambda *a, **k: "com.whatsapp")
    monkeypatch.setattr(playstore.http, "post", boom)
    assert playstore.fetch("com.whatsapp") == []


def test_resolve_passthrough_for_package_id(monkeypatch):
    # Already a package id -> no network search.
    monkeypatch.setattr(playstore.http, "get", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no net")))
    assert playstore.resolve_package_id("com.whatsapp") == "com.whatsapp"
    assert playstore.resolve_package_id("com.tencent.mm") == "com.tencent.mm"


def test_resolve_name_to_id_from_search_html(monkeypatch):
    html = '<a href="/store/apps/details?id=com.whatsapp">WhatsApp</a> ... id=com.whatsapp.w4b'
    monkeypatch.setattr(playstore.http, "get", lambda *a, **k: html)
    assert playstore.resolve_package_id("WhatsApp") == "com.whatsapp"


def test_resolve_returns_none_when_no_match(monkeypatch):
    monkeypatch.setattr(playstore.http, "get", lambda *a, **k: "<html>nothing</html>")
    assert playstore.resolve_package_id("zzz nonexistent app") is None
