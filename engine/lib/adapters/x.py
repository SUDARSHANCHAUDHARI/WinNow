"""X / Twitter via cookie-gated GraphQL search (optional, like reddit_oauth).

Dormant unless AUTH_TOKEN + CT0 (browser cookies from x.com) are set. X has no
viable keyless search, so this honestly requires the user's own session - we do
not pretend otherwise. All failures degrade to []; the parser is defensive
because X's GraphQL shape shifts. Tweet authenticity still benefits from the
corpus detectors (duplicate/burst), and engagement = likes + retweets.

Note: X rotates its GraphQL query id; override via X_SEARCH_QUERY_ID if the
default stops working. This is the inherent fragility of scraping X - the same
reason last30days vendors a whole client for it.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from .. import env, http, relevance
from ..schema import Item

# Public web app bearer (not a secret; ships in x.com's JS).
_BEARER = ("AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs"
           "%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA")
_DEFAULT_QUERY_ID = "nKAncKPF3fW8Dw4S8I6Vqw"
_ENDPOINT = "https://x.com/i/api/graphql/{qid}/SearchTimeline"


def _credentials(config: dict) -> tuple[str, str] | None:
    auth = env.get(config, "AUTH_TOKEN")
    ct0 = env.get(config, "CT0")
    return (auth, ct0) if auth and ct0 else None


def _iter_tweet_results(node):
    if isinstance(node, dict):
        if "tweet_results" in node and isinstance(node["tweet_results"], dict):
            result = node["tweet_results"].get("result")
            if isinstance(result, dict):
                yield result
        for v in node.values():
            yield from _iter_tweet_results(v)
    elif isinstance(node, list):
        for v in node:
            yield from _iter_tweet_results(v)


def _parse_created(text: str) -> datetime | None:
    # X format: "Wed Jun 10 14:33:00 +0000 2026"
    try:
        return datetime.strptime(text, "%a %b %d %H:%M:%S %z %Y")
    except (ValueError, TypeError):
        return None


def parse_timeline(data: dict, topic: str) -> list[Item]:
    items: list[Item] = []
    seen: set[str] = set()
    for result in _iter_tweet_results(data):
        legacy = result.get("legacy") or {}
        tweet_id = result.get("rest_id") or legacy.get("id_str") or ""
        text = legacy.get("full_text") or legacy.get("text") or ""
        if not tweet_id or tweet_id in seen or not text:
            continue
        seen.add(tweet_id)
        user = (((result.get("core") or {}).get("user_results") or {}).get("result") or {})
        handle = ((user.get("legacy") or {}).get("screen_name")
                  or (user.get("core") or {}).get("screen_name") or "")
        if not relevance.matches(topic, text, handle):
            continue
        likes = legacy.get("favorite_count", 0) or 0
        rts = legacy.get("retweet_count", 0) or 0
        items.append(
            Item(
                source="x",
                item_id=tweet_id,
                title=text[:80],
                text=text,
                url=f"https://x.com/{handle}/status/{tweet_id}" if handle else f"https://x.com/i/status/{tweet_id}",
                author=f"@{handle}" if handle else "",
                published_at=_parse_created(legacy.get("created_at", "")),
                engagement=float(likes + rts),
                metadata={"likes": likes, "retweets": rts},
            )
        )
    return items


def fetch(topic: str, *, lookback_days: int = 30, limit: int = 50) -> list[Item]:
    config = env.load()
    creds = _credentials(config)
    if not creds:
        return []
    auth_token, ct0 = creds
    qid = env.get(config, "X_SEARCH_QUERY_ID") or _DEFAULT_QUERY_ID

    variables = {"rawQuery": topic, "count": min(limit, 40), "product": "Latest"}
    features = {"responsive_web_graphql_timeline_navigation_enabled": True}
    url = (_ENDPOINT.format(qid=qid)
           + "?variables=" + http.urllib.parse.quote(json.dumps(variables))
           + "&features=" + http.urllib.parse.quote(json.dumps(features)))
    headers = {
        "Authorization": f"Bearer {_BEARER}",
        "x-csrf-token": ct0,
        "Cookie": f"auth_token={auth_token}; ct0={ct0}",
        "x-twitter-active-user": "yes",
        "User-Agent": "Mozilla/5.0 (Macintosh)",
    }
    try:
        data = http.get_json(url, headers=headers)
    except (http.HTTPError, ValueError):
        return []
    return parse_timeline(data, topic)[:limit]
