"""Serialize a Brief to JSON for the web dashboard / API consumers."""

from __future__ import annotations

import json

from .schema import Brief, Item

_META_KEYS = ("subreddit", "version", "app_name", "app_id", "score", "num_comments",
              "account_age_days", "total_karma")


def _item_dict(item: Item) -> dict:
    return {
        "source": item.source,
        "item_id": item.item_id,
        "title": item.title,
        "text": item.text,
        "url": item.url,
        "author": item.author,
        "published_at": item.published_at.isoformat() if item.published_at else None,
        "engagement": item.engagement,
        "rating": item.rating,
        "trust": round(item.authenticity.score, 3),
        "trust_label": item.authenticity.label,
        "weighted_score": round(item.weighted_score, 3),
        "flags": [
            {"name": s.name, "delta": s.delta, "detail": s.detail}
            for s in item.authenticity.signals
        ],
        "metadata": {k: item.metadata[k] for k in _META_KEYS if k in item.metadata},
    }


def brief_to_dict(brief: Brief) -> dict:
    return {
        "topic": brief.topic,
        "generated_at": brief.generated_at.isoformat(),
        "warnings": brief.warnings,
        "item_count": len(brief.items),
        "items": [_item_dict(i) for i in brief.items],
    }


def to_json(brief: Brief) -> str:
    return json.dumps(brief_to_dict(brief), ensure_ascii=False, indent=2)
