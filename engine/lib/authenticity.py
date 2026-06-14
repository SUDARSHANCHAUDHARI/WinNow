"""The Winnow spine: score every item for authenticity.

last30days' loophole is that engagement IS the score, with no check that the
engagement is real. Reviews and upvotes are the most gamed metrics online.
This module runs corpus-level detectors and writes a 0..1 trust score onto
each Item, so fusion can weight by *who is real*.

v0 detectors (no external deps, no ML):
  1. review-burst   — many items from the same day/version = coordinated push
  2. near-duplicate — templated/copy-pasted text = astroturf
  3. thin-text      — 1-3 word "great app!!!" reviews carry little signal
  4. new-or-anon    — missing/auto-generated author handle

Each detector only *penalizes*; an item with no red flags stays at 1.0.
Designed so adding per-source signals later (Reddit karma/account-age) is a
new detector, not a rewrite.
"""

from __future__ import annotations

import re
from collections import Counter

from .schema import Item

_WORD_RE = re.compile(r"[a-z0-9']+")
_BURST_FRACTION = 0.35   # if >35% of items land on one day, that day is bursty
_DUP_SHINGLE = 4         # word-level shingle size for near-dup detection


def _normalize(text: str) -> str:
    return " ".join(_WORD_RE.findall(text.lower()))


def _shingles(text: str, n: int = _DUP_SHINGLE) -> set[str]:
    words = _normalize(text).split()
    if len(words) < n:
        return {" ".join(words)} if words else set()
    return {" ".join(words[i : i + n]) for i in range(len(words) - n + 1)}


def score_corpus(items: list[Item]) -> None:
    """Mutates each item.authenticity in place."""
    if not items:
        return
    _flag_bursts(items)
    _flag_duplicates(items)
    for item in items:
        _flag_thin_text(item)
        _flag_anon(item)
        _flag_account_age(item)


def _flag_bursts(items: list[Item]) -> None:
    dated = [(i, i.published_at.date()) for i in items if i.published_at]
    if len(dated) < 5:
        return
    counts = Counter(day for _, day in dated)
    n = len(dated)
    # Date-burst is only meaningful when there is a multi-day baseline to spike
    # ABOVE. Review feeds are fetched newest-first, so a popular app's slice is
    # naturally all-today; flagging that as a "coordinated push" is a false
    # positive that would fire on every run. Require >=3 distinct days of spread
    # before any single day can be called anomalous.
    if len(counts) < 3:
        return
    for item, day in dated:
        if counts[day] / n >= _BURST_FRACTION and counts[day] >= 3:
            item.authenticity.penalize(
                "review-burst", 0.30,
                f"{counts[day]}/{n} items posted on {day} (coordinated-push signal)",
            )


def _flag_duplicates(items: list[Item]) -> None:
    seen: dict[str, Item] = {}
    for item in items:
        sh = _shingles(item.text)
        if not sh:
            continue
        for other_key, other in list(seen.items()):
            other_sh = _shingles(other.text)
            if not other_sh:
                continue
            overlap = len(sh & other_sh) / min(len(sh), len(other_sh))
            if overlap >= 0.6:
                item.authenticity.penalize(
                    "near-duplicate", 0.35,
                    f"shares {overlap:.0%} phrasing with another review",
                )
                break
        seen[item.item_id or item.text[:40]] = item


def _flag_thin_text(item: Item) -> None:
    words = _normalize(item.text).split()
    if 0 < len(words) <= 3:
        item.authenticity.penalize(
            "thin-text", 0.15, f"only {len(words)} words of substance",
        )


def _flag_anon(item: Item) -> None:
    author = (item.author or "").strip()
    if not author:
        item.authenticity.penalize("anon-author", 0.10, "no author attribution")
        return
    # Auto-generated handles like "User_8f3a2" or pure-digit names.
    if re.fullmatch(r"(user[_\- ]?\d+|\d+|[a-z]{1,3}\d{3,})", author.lower()):
        item.authenticity.penalize(
            "generated-handle", 0.12, f"author '{author}' looks auto-generated",
        )


# Account-level signals from OAuth enrichment (reddit_oauth). The strongest
# astroturf tell: brand-new, low-karma accounts pushing reviews. No-op when
# the metadata is absent (keyless runs), so this is purely additive.
_NEW_ACCOUNT_DAYS = 30
_LOW_KARMA = 50


def _flag_account_age(item: Item) -> None:
    age = item.metadata.get("account_age_days")
    if isinstance(age, (int, float)) and age < _NEW_ACCOUNT_DAYS:
        item.authenticity.penalize(
            "new-account", 0.30, f"author account is {int(age)}d old (<{_NEW_ACCOUNT_DAYS}d)",
        )
    karma = item.metadata.get("total_karma")
    if isinstance(karma, (int, float)) and karma < _LOW_KARMA:
        item.authenticity.penalize(
            "low-karma", 0.15, f"author has {int(karma)} total karma (<{_LOW_KARMA})",
        )
