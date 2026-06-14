"""Reddit via the official public search feed (search.rss / Atom).

Probed 2026-06: www.reddit.com `.json` returns HTTP 403 (anti-bot block) even
residential, but `search.rss` serves HTTP 200 keyless. We use the official
feed, NOT undocumented `/svc/shreddit/` partials (last30days' loophole #2).

Known boundary: Atom entries carry title/author/link/date but NO engagement
(upvotes/comments). v0 Reddit items therefore rank on recency + authenticity;
real scores and account-age trust signals arrive via optional OAuth enrichment
(see authenticity T3 / reddit_oauth). engagement stays 0.0 here, honestly.
"""

from __future__ import annotations

import html
import re
from datetime import datetime

from .. import http
from .. import env, relevance
from ..schema import Item
from . import reddit_oauth

# sort=relevance (not new) - a recency firehose returns mostly off-topic noise.
_SEARCH = "https://www.reddit.com/search.rss?q={q}&sort=relevance&t=month&limit={limit}"
_ENTRY_RE = re.compile(r"<entry>(.*?)</entry>", re.DOTALL)


def _tag(block: str, tag: str) -> str:
    m = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", block, re.DOTALL)
    if not m:
        return ""
    return html.unescape(m.group(1).strip())


def _attr(block: str, tag: str, attr: str) -> str:
    m = re.search(rf"<{tag}[^>]*\b{attr}=\"(.*?)\"", block, re.DOTALL)
    return html.unescape(m.group(1)) if m else ""


def fetch(topic: str, *, lookback_days: int = 30, limit: int = 50) -> list[Item]:
    # Prefer the official OAuth API when keys are configured: real scores +
    # account-age signals. Falls through to keyless RSS otherwise.
    creds = env.reddit_creds(env.load())
    if creds:
        oauth_items = reddit_oauth.fetch(topic, creds, lookback_days=lookback_days, limit=limit)
        if oauth_items:
            return oauth_items

    url = _SEARCH.format(q=http.urllib.parse.quote(topic), limit=min(limit, 100))
    try:
        xml = http.get(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh) winnow"})
    except http.HTTPError:
        return []

    items: list[Item] = []
    for block in _ENTRY_RE.findall(xml):
        title = _tag(block, "title")
        link = _attr(block, "link", "href") or _tag(block, "id")
        author = _tag(block, "name")           # e.g. /u/username
        subreddit = _attr(block, "category", "label")  # e.g. r/Notion
        content = re.sub(r"<[^>]+>", " ", _tag(block, "content"))
        content = html.unescape(content)  # feed double-encodes (&amp;quot; -> ")
        content = re.sub(r"\s+", " ", content).strip()
        published = None
        raw_date = _tag(block, "published") or _tag(block, "updated")
        if raw_date:
            try:
                published = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
            except ValueError:
                published = None
        # Relevance gate: keyword feeds return noise; require the topic's
        # primary entity to appear in title/content/subreddit.
        if not relevance.matches(topic, title, content, subreddit):
            continue
        items.append(
            Item(
                source="reddit",
                item_id=_tag(block, "id") or link,
                title=title,
                text=content[:500],
                url=link,
                author=author,
                published_at=published,
                engagement=0.0,  # RSS carries no score; see module docstring
                metadata={"subreddit": subreddit},
            )
        )
        if len(items) >= limit:
            break
    return items
