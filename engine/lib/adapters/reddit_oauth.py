"""Reddit official OAuth API enrichment (optional, key-gated).

Dormant until REDDIT_CLIENT_ID/SECRET are set (see env.reddit_creds). When
active it replaces the keyless RSS path with the official app-only API, which
gives two things RSS cannot:
  1. real engagement - upvote score + comment count
  2. author account-age + karma, the strongest per-item authenticity signals

Author enrichment is one extra call per distinct author, capped to keep the
run cheap. All failures degrade to whatever was gathered; never raise.
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone

from .. import http, relevance
from ..schema import Item

_TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
_SEARCH_URL = "https://oauth.reddit.com/search?q={q}&sort=relevance&t=month&limit={limit}&raw_json=1"
_ABOUT_URL = "https://oauth.reddit.com/user/{user}/about?raw_json=1"
_MAX_AUTHOR_LOOKUPS = 8


def app_token(client_id: str, client_secret: str, user_agent: str) -> str | None:
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    try:
        raw = http.post(
            _TOKEN_URL,
            {"grant_type": "client_credentials"},
            headers={"Authorization": f"Basic {basic}", "User-Agent": user_agent},
        )
        import json
        return json.loads(raw).get("access_token")
    except (http.HTTPError, ValueError):
        return None


def fetch(topic: str, creds: tuple[str, str, str], *, lookback_days: int = 30, limit: int = 50) -> list[Item]:
    client_id, client_secret, ua = creds
    token = app_token(client_id, client_secret, ua)
    if not token:
        return []
    auth = {"Authorization": f"Bearer {token}", "User-Agent": ua}

    url = _SEARCH_URL.format(q=http.urllib.parse.quote(topic), limit=min(limit, 100))
    try:
        data = http.get_json(url, headers=auth)
    except (http.HTTPError, ValueError):
        return []

    items: list[Item] = []
    for child in (data.get("data", {}).get("children") or []):
        d = child.get("data", {})
        title = d.get("title", "")
        selftext = d.get("selftext", "") or ""
        subreddit = f"r/{d.get('subreddit', '')}"
        if not relevance.matches(topic, title, selftext, subreddit):
            continue
        created = d.get("created_utc")
        published = datetime.fromtimestamp(created, tz=timezone.utc) if created else None
        items.append(
            Item(
                source="reddit",
                item_id=d.get("name", d.get("id", "")),
                title=title,
                text=selftext[:500],
                url="https://www.reddit.com" + d.get("permalink", ""),
                author=d.get("author", ""),
                published_at=published,
                engagement=float((d.get("score") or 0) + (d.get("num_comments") or 0)),
                metadata={"subreddit": subreddit, "score": d.get("score"),
                          "num_comments": d.get("num_comments")},
            )
        )
        if len(items) >= limit:
            break

    _enrich_authors(items, auth)
    return items


def _enrich_authors(items: list[Item], auth: dict) -> None:
    """Attach account_age_days + karma to each item's metadata (capped)."""
    seen: dict[str, dict] = {}
    for item in items[:_MAX_AUTHOR_LOOKUPS]:
        author = item.author
        if not author or author in ("[deleted]", "AutoModerator"):
            continue
        if author not in seen:
            try:
                about = http.get_json(_ABOUT_URL.format(user=author), headers=auth)
                a = about.get("data", {})
                created = a.get("created_utc")
                age_days = None
                if created:
                    age_days = (datetime.now(timezone.utc)
                                - datetime.fromtimestamp(created, tz=timezone.utc)).days
                seen[author] = {
                    "account_age_days": age_days,
                    "total_karma": a.get("total_karma"),
                }
            except (http.HTTPError, ValueError):
                seen[author] = {}
        item.metadata.update(seen[author])
