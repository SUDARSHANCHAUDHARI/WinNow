"""Render a Brief to markdown. The model (skill host) synthesizes prose on top;
this is the structured evidence block + a CLI-readable summary."""

from __future__ import annotations

from .schema import Brief

_LABEL_EMOJI = {"trusted": "✅", "mixed": "⚠️", "suspicious": "🚩"}


def to_markdown(brief: Brief) -> str:
    lines: list[str] = []
    lines.append(f"# Winnow: {brief.topic}")
    lines.append(f"_synced {brief.generated_at:%Y-%m-%d} · {len(brief.items)} items, "
                 f"authenticity-weighted_")
    lines.append("")
    for w in brief.warnings:
        lines.append(f"> ⚠️ {w}")
    if brief.warnings:
        lines.append("")

    for i, item in enumerate(brief.items, 1):
        emoji = _LABEL_EMOJI.get(item.authenticity.label, "")
        rating = f" · {item.rating:.0f}★" if item.rating else ""
        date = f" · {item.published_at:%Y-%m-%d}" if item.published_at else ""
        head = item.title or (item.text[:70] + "…" if len(item.text) > 70 else item.text)
        lines.append(f"### {i}. {head}")
        lines.append(f"`{item.source}`{rating}{date} · trust {item.authenticity.score:.2f} "
                     f"{emoji} {item.authenticity.label}")
        if item.text and item.text != head:
            lines.append(f"> {item.text[:300]}")
        if item.authenticity.signals:
            flags = ", ".join(s.name for s in item.authenticity.signals)
            lines.append(f"  _flags: {flags}_")
        if item.url:
            lines.append(f"  [{item.source} link]({item.url})")
        lines.append("")
    return "\n".join(lines)
