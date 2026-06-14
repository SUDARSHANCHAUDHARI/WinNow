"""YouTube via keyless search-page scrape (ytInitialData).

No API key, no yt-dlp. Sorted by upload date (sp=CAI%3D) and forced to English
locale so view counts and relative dates parse. Real engagement = view count.
Relative dates ("3 weeks ago") are converted to an approximate published_at so
the central 30-day window filter can drop stale results.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone

from .. import http, relevance
from ..schema import Item

# sp=CAI%3D -> sort by upload date (most recent first)
_SEARCH = "https://www.youtube.com/results?search_query={q}&sp=CAI%3D&hl=en&gl=US"
_INITIAL = re.compile(r"var ytInitialData = (\{.*?\});</script>", re.DOTALL)
_REL = re.compile(r"(\d+)\s+(hour|day|week|month|year)s?\s+ago")
_UNIT_DAYS = {"hour": 1 / 24, "day": 1, "week": 7, "month": 30, "year": 365}


def _approx_published(text: str) -> datetime | None:
    m = _REL.search(text or "")
    if not m:
        return None
    days = int(m.group(1)) * _UNIT_DAYS[m.group(2)]
    return datetime.now(timezone.utc) - timedelta(days=days)


def _views(text: str) -> float:
    digits = re.sub(r"[^\d]", "", text or "")
    return float(digits) if digits else 0.0


def _iter_video_renderers(node):
    if isinstance(node, dict):
        if "videoRenderer" in node:
            yield node["videoRenderer"]
        for v in node.values():
            yield from _iter_video_renderers(v)
    elif isinstance(node, list):
        for v in node:
            yield from _iter_video_renderers(v)


def fetch(topic: str, *, lookback_days: int = 30, limit: int = 50) -> list[Item]:
    url = _SEARCH.format(q=http.urllib.parse.quote(topic))
    try:
        html = http.get(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh)"})
    except http.HTTPError:
        return []
    m = _INITIAL.search(html)
    if not m:
        return []
    try:
        data = json.loads(m.group(1))
    except ValueError:
        return []

    items: list[Item] = []
    seen: set[str] = set()
    for v in _iter_video_renderers(data):
        vid = v.get("videoId", "")
        if not vid or vid in seen:
            continue
        seen.add(vid)
        title = "".join(r.get("text", "") for r in v.get("title", {}).get("runs", []))
        channel = "".join(r.get("text", "") for r in v.get("ownerText", {}).get("runs", []))
        if not relevance.matches(topic, title, channel):
            continue
        items.append(
            Item(
                source="youtube",
                item_id=vid,
                title=title,
                text=title,
                url=f"https://www.youtube.com/watch?v={vid}",
                author=channel,
                published_at=_approx_published(v.get("publishedTimeText", {}).get("simpleText", "")),
                engagement=_views(v.get("viewCountText", {}).get("simpleText", "")),
                metadata={"channel": channel},
            )
        )
        if len(items) >= limit:
            break
    return items
