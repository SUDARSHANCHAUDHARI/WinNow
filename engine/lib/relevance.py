"""Lightweight relevance gate for keyword-search sources (Reddit, Pantip).

Review sources are fetched by app id, so every item is on-topic by construction.
Keyword feeds are not: a recency-sorted Reddit search returns a firehose where
most items barely match. Without a gate, the brief fills with spam. This is the
minimal grounding check - the item must mention the topic's primary entity
(its longest significant token) - mirroring last30days' entity-grounding idea
without an LLM call.
"""

from __future__ import annotations

import re

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOP = frozenset({
    "the", "a", "an", "and", "or", "of", "to", "for", "in", "on", "is", "are",
    "what", "how", "why", "best", "new", "vs", "versus", "review", "reviews",
    "app", "apps", "bug", "bugs", "issue", "issues", "update", "with", "about",
})


def tokens(topic: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(topic.lower()) if t not in _STOP and len(t) >= 3]


def primary_entity(topic: str) -> str:
    """The longest significant token - the thing the item must mention."""
    toks = tokens(topic)
    return max(toks, key=len) if toks else ""


def matches(topic: str, *texts: str) -> bool:
    """True if the primary entity appears in any of the given text surfaces.

    Falls back to True when the topic has no significant token (e.g. a pure
    stopword query) so we never silently drop everything.
    """
    primary = primary_entity(topic)
    if not primary:
        return True
    haystack = " ".join(t for t in texts if t).lower()
    return primary in haystack


def passes_context(
    text: str,
    include: list[str] | None = None,
    exclude: list[str] | None = None,
) -> bool:
    """Disambiguation gate for ambiguous brands ("Notion" app vs band).

    A reasoning host (or the user) supplies context: `exclude` drops items
    carrying off-sense terms (song, lyrics, album); `include` requires at least
    one in-sense term (app, workspace, software). Both empty = no-op, so this
    never changes behavior unless context is explicitly provided.
    """
    t = text.lower()
    if exclude and any(term.lower() in t for term in exclude if term):
        return False
    if include and not any(term.lower() in t for term in include if term):
        return False
    return True
