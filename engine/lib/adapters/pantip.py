"""Pantip (Thailand's Reddit) via public RSS — the regional gap last30days skips.

Probed live: the search API needs Pantip's known frontend ptauthorize token;
the RSS feeds serve HTTP 200 keyless. We start with RSS (robust) and keep the
search-API path behind a token env for later. Topic is matched against feed
titles/descriptions (RSS has no native query).
"""

from __future__ import annotations

import re
from datetime import datetime
from email.utils import parsedate_to_datetime

from .. import http, relevance
from ..schema import Item

_FEEDS = [
    "https://pantip.com/forum/tech/feed",
    "https://pantip.com/forum/news/feed",
]
_ITEM_RE = re.compile(r"<item>(.*?)</item>", re.DOTALL)


def _tag(block: str, tag: str) -> str:
    m = re.search(rf"<{tag}>(.*?)</{tag}>", block, re.DOTALL)
    if not m:
        return ""
    val = m.group(1).strip()
    val = re.sub(r"^<!\[CDATA\[(.*?)\]\]>$", r"\1", val, flags=re.DOTALL)
    return val.strip()


def fetch(topic: str, *, lookback_days: int = 30, limit: int = 50) -> list[Item]:
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
