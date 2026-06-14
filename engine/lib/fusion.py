"""Rank items by authenticity-weighted engagement + recency.

Two ideas combined:
  1. weighted_score = engagement * authenticity, then a second trust GATE, so a
     500-upvote astroturf burst loses to a 50-upvote genuine thread (the thesis).
  2. engagement is normalized PER SOURCE (log-scaled vs that source's top item),
     so YouTube's millions of views don't crush a 50-helpful App Store review in
     a mixed run. "Top of YouTube" and "top of reviews" compete on equal footing
     - the scale-free principle behind RRF, adapted to our per-item trust model.
"""

from __future__ import annotations

import math
from collections import defaultdict

from .schema import Item

_RECENCY_HALFLIFE_DAYS = 14.0


def _recency_boost(item: Item) -> float:
    age = item.age_days()
    if age is None:
        return 1.0
    return 0.5 ** (max(0.0, age) / _RECENCY_HALFLIFE_DAYS)


def _per_source_norm_engagement(items: list[Item]) -> dict[int, float]:
    """Map id(item) -> log-engagement normalized to [0,1] within its own source.

    Top item in a source = 1.0; a source where every item has equal engagement
    (e.g. Reddit RSS, all 0) collapses to 0, leaving recency + trust to order it.
    """
    by_source: dict[str, list[Item]] = defaultdict(list)
    for it in items:
        by_source[it.source].append(it)
    norm: dict[int, float] = {}
    for group in by_source.values():
        logs = {id(it): math.log1p(max(0.0, it.weighted_score)) for it in group}
        hi = max(logs.values())
        for it in group:
            norm[id(it)] = (logs[id(it)] / hi) if hi > 0 else 0.0
    return norm


def rank(items: list[Item], *, limit: int = 25, min_per_source: int = 2) -> list[Item]:
    norm = _per_source_norm_engagement(items)

    def key(item: Item) -> float:
        # Additive blend on a common 0..1 scale: trust-gated normalized
        # engagement is primary, recency next, trust as a floor/tiebreaker.
        # Recency stays in its own term so zero-engagement sources (Reddit RSS)
        # are still ordered by freshness instead of flattening to a constant.
        eng = norm[id(item)] * item.authenticity.score
        return 0.60 * eng + 0.25 * _recency_boost(item) + 0.15 * item.authenticity.score

    scored = sorted(items, key=key, reverse=True)
    if len(scored) <= limit:
        return scored

    # Diversity floor: guarantee each source up to min_per_source slots before
    # filling the rest by score. Without this, a zero-engagement source (Reddit
    # RSS) gets shut out of a mixed run by review/video items that carry real
    # engagement numbers. Reserved items are still the best of their source.
    chosen: list[Item] = []
    chosen_ids: set[int] = set()
    per_source: dict[str, int] = defaultdict(int)
    for it in scored:
        if len(chosen) >= limit:
            break
        if per_source[it.source] < min_per_source:
            chosen.append(it)
            chosen_ids.add(id(it))
            per_source[it.source] += 1
    for it in scored:
        if len(chosen) >= limit:
            break
        if id(it) not in chosen_ids:
            chosen.append(it)
            chosen_ids.add(id(it))
    chosen.sort(key=key, reverse=True)
    return chosen


def corpus_trust(items: list[Item]) -> float:
    """Mean authenticity across the pool — surfaced as a brief-level warning."""
    if not items:
        return 1.0
    return sum(i.authenticity.score for i in items) / len(items)
