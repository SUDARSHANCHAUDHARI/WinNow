"""Source adapters. Each turns one platform into a list[Item]."""

from __future__ import annotations

from . import appstore, pantip, playstore, reddit, x, youtube

# Registry: source name -> module exposing fetch(topic, *, lookback_days, limit).
REGISTRY = {
    "appstore": appstore,
    "playstore": playstore,
    "pantip": pantip,
    "reddit": reddit,
    "youtube": youtube,
    "x": x,
}
