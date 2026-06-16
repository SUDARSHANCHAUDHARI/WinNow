"""Pantip (Thailand's Reddit) — the regional gap last30days skips.

Two paths:
- Search API (preferred): real keyword search via Pantip's getresult endpoint.
  Needs the frontend's `ptauthorize: Basic <token>` (set PANTIP_AUTH in .env).
  Gated + defensive: returns [] on any failure so we fall back cleanly.
- RSS (keyless default): forum feeds, HTTP 200 with no token; topic matched
  against titles/descriptions since RSS has no native query.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from .. import env, http, relevance
from ..schema import Item

_FEEDS = [
    "https://pantip.com/forum/tech/feed",
    "https://pantip.com/forum/news/feed",
]
_ITEM_RE = re.compile(r"<item>(.*?)</item>", re.DOTALL)
_SEARCH_API = "https://pantip.com/api/search-service/search/getresult?keyword={q}&page=1&rooms="


def _search_api(topic: str, token: str, limit: int) -> list[Item]:
    """Real keyword search. Defensive: any shape mismatch / error -> []."""
    url = _SEARCH_API.format(q=http.urllib.parse.quote(topic))
    try:
        data = http.get_json(url, headers={"ptauthorize": f"Basic {token}"})
    except (http.HTTPError, ValueError):
        return []
    rows = data.get("data") if isinstance(data.get("data"), list) else data.get("results") or []
    items: list[Item] = []
    for r in rows if isinstance(rows, list) else []:
        if not isinstance(r, dict):
            continue
        tid = str(r.get("topic_id") or r.get("id") or "")
        title = r.get("title") or ""
        if not tid or not title:
            continue
        ts = r.get("timestamp") or r.get("created_time")
        pub = None
        if isinstance(ts, (int, float)):
            pub = datetime.fromtimestamp(ts, tz=timezone.utc)
        items.append(Item(
            source="pantip", item_id=tid, title=title,
            text=r.get("detail") or r.get("desc") or title,
            url=f"https://pantip.com/topic/{tid}", author=r.get("author") or "",
            published_at=pub,
            engagement=float(r.get("comments_count") or r.get("comment") or 0),
            metadata={"via": "search-api"}))
        if len(items) >= limit:
            break
    return items


def _tag(block: str, tag: str) -> str:
    m = re.search(rf"<{tag}>(.*?)</{tag}>", block, re.DOTALL)
    if not m:
        return ""
    val = m.group(1).strip()
    val = re.sub(r"^<!\[CDATA\[(.*?)\]\]>$", r"\1", val, flags=re.DOTALL)
    return val.strip()


def fetch(topic: str, *, lookback_days: int = 30, limit: int = 50) -> list[Item]:
    token = env.get(env.load(), "PANTIP_AUTH")
    if token:
        api_items = _search_api(topic, token, limit)
        if api_items:
            return api_items

    items: list[Item] = []
    for feed in _FEEDS:
        try:
            xml = http.get(feed)
        except http.HTTPError:
            continue
        for block in _ITEM_RE.findall(xml):
            title = _tag(block, "title")
            desc = _tag(block, "description")
            if not relevance.matches(topic, title, desc):
                continue
            link = _tag(block, "link")
            pub = None
            raw_date = _tag(block, "pubDate")
            if raw_date:
                try:
                    pub = parsedate_to_datetime(raw_date)
                except (TypeError, ValueError):
                    pub = None
            items.append(
                Item(
                    source="pantip",
                    item_id=link,
                    title=title,
                    text=desc,
                    url=link,
                    author=_tag(block, "dc:creator"),
                    published_at=pub,
                    metadata={"feed": feed},
                )
            )
            if len(items) >= limit:
                return items
    return items
