import json
from datetime import datetime, timezone

from lib import render_json
from lib.schema import Authenticity, AuthenticitySignal, Brief, Item


def test_brief_serializes_round_trip():
    item = Item(
        source="reddit", item_id="t3_x", title="Sync broke", text="details here",
        url="https://reddit.com/x", author="u/dev",
        published_at=datetime(2026, 6, 10, tzinfo=timezone.utc),
        engagement=42.0, rating=None,
        authenticity=Authenticity(score=0.55, signals=[AuthenticitySignal("new-account", -0.30, "5d old")]),
        metadata={"subreddit": "r/Notion", "account_age_days": 5, "irrelevant": "drop"},
    )
    brief = Brief(topic="Notion", items=[item],
                  generated_at=datetime(2026, 6, 14, tzinfo=timezone.utc),
                  warnings=["low trust"])
    payload = json.loads(render_json.to_json(brief))

    assert payload["topic"] == "Notion"
    assert payload["item_count"] == 1
    assert payload["warnings"] == ["low trust"]
    it = payload["items"][0]
    assert it["source"] == "reddit"
    assert it["trust"] == 0.55
    assert it["trust_label"] == "mixed"
    assert it["flags"][0]["name"] == "new-account"
    assert it["metadata"]["account_age_days"] == 5
    assert "irrelevant" not in it["metadata"]  # only whitelisted keys
