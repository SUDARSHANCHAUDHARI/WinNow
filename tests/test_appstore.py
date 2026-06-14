"""App Store adapter — parsing test against a captured RSS shape (offline, no network)."""

import json
from unittest import mock

from lib.adapters import appstore

_SAMPLE = {
    "feed": {
        "entry": [
            {  # app metadata entry (no im:rating) — must be skipped
                "im:name": {"label": "Sample App"},
                "id": {"label": "meta"},
            },
            {
                "id": {"label": "review-1"},
                "title": {"label": "Sync is broken"},
                "content": {"label": "After the update my notes stopped syncing across devices."},
                "im:rating": {"label": "1"},
                "im:version": {"label": "9.2.0"},
                "im:voteSum": {"label": "12"},
                "updated": {"label": "2026-06-10T08:33:00-07:00"},
                "author": {"name": {"label": "daily_user_x"},
                           "uri": {"label": "https://itunes.apple.com/us/reviews/id123"}},
            },
        ]
    }
}


def test_parses_reviews_skips_metadata_entry():
    with mock.patch.object(appstore.http, "get_json", return_value=_SAMPLE), \
         mock.patch.object(appstore, "resolve_app_id", return_value=("123", "Sample App")):
        items = appstore.fetch("Sample App", limit=10)
    # 3 pages requested but same payload; dedupe-free MVP -> at least the 1 review parsed
    assert items
    first = items[0]
    assert first.source == "appstore"
    assert first.rating == 1.0
    assert "syncing" in first.text
    assert first.metadata["version"] == "9.2.0"
    assert first.engagement == 12.0


def test_resolve_app_id_passthrough_for_numeric():
    with mock.patch.object(appstore.http, "get_json") as gj:
        assert appstore.resolve_app_id("310633997") == ("310633997", "310633997")
        gj.assert_not_called()
