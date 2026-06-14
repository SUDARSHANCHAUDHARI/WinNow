"""App Store customer reviews via the public iTunes RSS feed.

This is a source last30days does not cover at all. Zero auth, zero key.
Topic may be a numeric track id, a bundle-id-ish name, or a free-text app
name (resolved via the public iTunes Search API).

Feed: https://itunes.apple.com/{country}/rss/customerreviews/id={id}/sortBy=mostRecent/json
"""

from __future__ import annotations

from datetime import datetime

from .. import http
from ..schema import Item

_SEARCH = "https://itunes.apple.com/search?term={q}&entity=software&limit=1&country={country}"
_REVIEWS = "https://itunes.apple.com/{country}/rss/customerreviews/page={page}/id={id}/sortBy=mostRecent/json"


def resolve_app_id(topic: str, country: str = "us") -> tuple[str, str] | None:
    """Return (track_id, app_name) for a free-text query, or None."""
    if topic.strip().isdigit():
        return topic.strip(), topic.strip()
    url = _SEARCH.format(q=http.urllib.parse.quote(topic), country=country)
    data = http.get_json(url)
    results = data.get("results") or []
    if not results:
        return None
    top = results[0]
    return str(top["trackId"]), top.get("trackName", topic)


def _parse_date(label: str) -> datetime | None:
    # e.g. 2026-06-10T08:33:00-07:00
    try:
        return datetime.fromisoformat(label)
    except ValueError:
        return None


def fetch(topic: str, *, lookback_days: int = 30, limit: int = 50, country: str = "us") -> list[Item]:
    resolved = resolve_app_id(topic, country)
    if not resolved:
        return []
    app_id, app_name = resolved

    items: list[Item] = []
    for page in range(1, 4):  # iTunes serves ~50 reviews/page, up to 10 pages
        if len(items) >= limit:
            break
        url = _REVIEWS.format(country=country, id=app_id, page=page)
        try:
            data = http.get_json(url)
        except (http.HTTPError, ValueError):
            break
        entries = (data.get("feed") or {}).get("entry") or []
        # First entry is app metadata when present; reviews carry im:rating.
        for entry in entries:
            if "im:rating" not in entry:
                continue
            rating = _safe_float(entry["im:rating"]["label"])
            published = _parse_date(entry.get("updated", {}).get("label", ""))
            items.append(
                Item(
                    source="appstore",
                    item_id=entry.get("id", {}).get("label", ""),
                    title=entry.get("title", {}).get("label", ""),
                    text=entry.get("content", {}).get("label", ""),
                    url=entry.get("author", {}).get("uri", {}).get("label", ""),
                    author=entry.get("author", {}).get("name", {}).get("label", ""),
                    published_at=published,
                    rating=rating,
                    engagement=float(_safe_float(entry.get("im:voteSum", {}).get("label", "0")) or 0.0),
                    metadata={"app_id": app_id, "app_name": app_name,
                              "version": entry.get("im:version", {}).get("label", "")},
                )
            )
    return items[:limit]


def _safe_float(val: str) -> float | None:
    try:
        return float(val)
    except (TypeError, ValueError):
        return None
