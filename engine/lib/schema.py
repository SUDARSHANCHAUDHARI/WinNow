"""Core data shapes for the Winnow pipeline.

One Item per piece of content from any source. The distinguishing field vs
last30days is `authenticity`: every item carries a 0..1 trust score plus the
signals that produced it, so the fusion layer can weight by *who is real*, not
just by raw upvotes/likes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class AuthenticitySignal:
    """One reason an item's authenticity was adjusted, for transparency."""

    name: str          # e.g. "review-burst", "near-duplicate", "new-account"
    delta: float       # negative = suspicious, positive = trust-building
    detail: str = ""


@dataclass
class Authenticity:
    """Trust verdict for a single item. score in [0,1]; 1.0 == fully trusted."""

    score: float = 1.0
    signals: list[AuthenticitySignal] = field(default_factory=list)

    def penalize(self, name: str, delta: float, detail: str = "") -> None:
        self.signals.append(AuthenticitySignal(name, -abs(delta), detail))
        self.score = max(0.0, min(1.0, self.score - abs(delta)))

    @property
    def label(self) -> str:
        if self.score >= 0.75:
            return "trusted"
        if self.score >= 0.45:
            return "mixed"
        return "suspicious"


@dataclass
class Item:
    """A single result from any source."""

    source: str                     # "appstore", "playstore", "pantip", "reddit"
    item_id: str
    title: str
    text: str
    url: str = ""
    author: str = ""
    published_at: Optional[datetime] = None
    engagement: float = 0.0         # raw, source-native (upvotes/helpful-count/rating count)
    rating: Optional[float] = None  # 1..5 for review sources
    authenticity: Authenticity = field(default_factory=Authenticity)
    metadata: dict = field(default_factory=dict)

    @property
    def weighted_score(self) -> float:
        """Engagement discounted by authenticity. The core Winnow signal."""
        return self.engagement * self.authenticity.score

    def age_days(self, now: Optional[datetime] = None) -> Optional[float]:
        if self.published_at is None:
            return None
        now = now or datetime.now(timezone.utc)
        pub = self.published_at
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)
        return (now - pub).total_seconds() / 86400.0


@dataclass
class Brief:
    """Final synthesized output."""

    topic: str
    items: list[Item]
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    warnings: list[str] = field(default_factory=list)
