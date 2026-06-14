"""Reddit OAuth enrichment + account-age authenticity — all mocked, no network."""

from datetime import datetime, timezone

from lib import authenticity, env
from lib.adapters import reddit, reddit_oauth
from lib.schema import Item


# --- env / placeholder gating -------------------------------------------------

def test_placeholder_keys_treated_as_unset():
    cfg = {"REDDIT_CLIENT_ID": "your_client_id_here", "REDDIT_CLIENT_SECRET": "xxx"}
    assert env.reddit_creds(cfg) is None


def test_real_keys_resolve():
    cfg = {"REDDIT_CLIENT_ID": "abc123", "REDDIT_CLIENT_SECRET": "s3cret"}
    creds = env.reddit_creds(cfg)
    assert creds is not None
    assert creds[0] == "abc123" and creds[1] == "s3cret"


# --- OAuth fetch maps API shape ----------------------------------------------

_SEARCH_PAYLOAD = {
    "data": {"children": [
        {"data": {"name": "t3_x1", "id": "x1", "title": "Notion sync is great now",
                  "selftext": "works across devices", "subreddit": "Notion",
                  "permalink": "/r/Notion/comments/x1/s/", "author": "real_user",
                  "score": 120, "num_comments": 18,
                  "created_utc": datetime(2026, 6, 10, tzinfo=timezone.utc).timestamp()}},
    ]}
}


def test_oauth_fetch_builds_items(monkeypatch):
    monkeypatch.setattr(reddit_oauth, "app_token", lambda *a, **k: "tok")
    monkeypatch.setattr(reddit_oauth.http, "get_json",
                        lambda url, **k: _SEARCH_PAYLOAD if "search" in url
                        else {"data": {"created_utc": datetime(2015, 1, 1, tzinfo=timezone.utc).timestamp(),
                                       "total_karma": 9000}})
    items = reddit_oauth.fetch("Notion", ("id", "sec", "ua"), limit=5)
    assert len(items) == 1
    it = items[0]
    assert it.engagement == 138.0  # score + comments
    assert it.metadata["account_age_days"] > 3000
    assert it.metadata["total_karma"] == 9000


def test_oauth_no_token_returns_empty(monkeypatch):
    monkeypatch.setattr(reddit_oauth, "app_token", lambda *a, **k: None)
    assert reddit_oauth.fetch("Notion", ("id", "sec", "ua")) == []


def test_rss_fallback_when_no_creds(monkeypatch):
    # No creds -> adapter must not call OAuth, must hit RSS path.
    monkeypatch.setattr(reddit.env, "reddit_creds", lambda cfg: None)
    called = {"oauth": False}
    monkeypatch.setattr(reddit.reddit_oauth, "fetch",
                        lambda *a, **k: called.__setitem__("oauth", True) or [])
    monkeypatch.setattr(reddit.http, "get", lambda *a, **k: "<feed></feed>")
    reddit.fetch("Notion")
    assert called["oauth"] is False


# --- account-age detector -----------------------------------------------------

def _item(meta):
    return Item(source="reddit", item_id="x", title="t",
                text="a genuinely substantial review body about the product here",
                author="someone", metadata=meta)


def test_new_account_penalized():
    it = _item({"account_age_days": 5, "total_karma": 9000})
    authenticity.score_corpus([it])
    assert any(s.name == "new-account" for s in it.authenticity.signals)
    assert it.authenticity.score <= 0.7


def test_low_karma_penalized():
    it = _item({"account_age_days": 2000, "total_karma": 3})
    authenticity.score_corpus([it])
    assert any(s.name == "low-karma" for s in it.authenticity.signals)


def test_established_account_clean():
    it = _item({"account_age_days": 3000, "total_karma": 50000})
    authenticity.score_corpus([it])
    assert it.authenticity.score == 1.0


def test_missing_account_metadata_is_noop():
    it = _item({})
    authenticity.score_corpus([it])
    assert not any(s.name in ("new-account", "low-karma") for s in it.authenticity.signals)
