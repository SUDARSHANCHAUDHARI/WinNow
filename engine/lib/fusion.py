"""Rank items by authenticity-weighted engagement + recency.

Unlike last30days (pure RRF over engagement), the headline ordering signal
here is weighted_score = engagement * authenticity. A 500-upvote astroturf
burst loses to a 50-upvote genuine thread.
"""

from __future__ import annotations

import math

from .schema import Item

_RECENCY_HALFLIFE_DAYS = 14.0


def _recency_boost(item: Item) -> float:
    age = item.age_days()
    if age is None:
        return 1.0
    return 0.5 ** (max(0.0, age) / _RECENCY_HALFLIFE_DAYS)


def rank(items: list[Item], *, limit: int = 25) -> list[Item]:
    def key(item: Item) -> float:
        # weighted_score already discounts engagement by trust once (linear).
        # The trust GATE multiplies by authenticity a second time so suspicious
        # content is suppressed super-linearly: 500 upvotes at 0.2 trust ranks
        # below 50 upvotes at 1.0 trust. This is the Winnow thesis in one line.
        eng = math.log1p(max(0.0, item.weighted_score)) * item.authenticity.score
        return eng * _recency_boost(item) + item.authenticity.score * 0.25

    return sorted(items, key=key, reverse=True)[:limit]


def corpus_trust(items: list[Item]) -> float:
    """Mean authenticity across the pool — surfaced as a brief-level warning."""
    if not items:
        return 1.0
    return sum(i.authenticity.score for i in items) / len(items)
