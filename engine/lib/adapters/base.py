"""Adapter contract.

An adapter is any module exposing:

    fetch(topic: str, *, lookback_days: int = 30, limit: int = 50) -> list[Item]

Adapters do retrieval + light normalization only. They do NOT score
authenticity (that is the engine's job, in authenticity.py) so the trust
logic stays in one place and is consistent across sources.
"""

from __future__ import annotations

from typing import Protocol

from ..schema import Item


class SourceAdapter(Protocol):
    def fetch(self, topic: str, *, lookback_days: int = 30, limit: int = 50) -> list[Item]:
        ...
