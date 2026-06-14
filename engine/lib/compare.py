"""Head-to-head comparison of two topics, weighted by authenticity.

The differentiating angle: not just "which app is rated higher" but "whose
rating is REAL." Two apps at 4.6 are not equal if one's reviews are 90%
trusted and the other's are a burst of new-account 5-stars. Only Winnow,
which scores authenticity per item, can surface that.
"""

from __future__ import annotations

from .schema import Brief, Item


def _avg(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _best(items: list[Item], predicate) -> Item | None:
    """Highest-trust item matching predicate (a real, representative review)."""
    pool = [i for i in items if predicate(i)]
    if not pool:
        return None
    return max(pool, key=lambda i: (i.authenticity.score, i.engagement))


def summarize(brief: Brief) -> dict:
    items = brief.items
    ratings = [i.rating for i in items if i.rating is not None]
    trusts = [i.authenticity.score for i in items]
    suspicious = sum(1 for i in items if i.authenticity.label == "suspicious")
    praise = _best(items, lambda i: (i.rating or 0) >= 4 or (i.rating is None and i.authenticity.score >= 0.7))
    complaint = _best(items, lambda i: i.rating is not None and i.rating <= 2)

    def snippet(it: Item | None) -> dict | None:
        if it is None:
            return None
        return {"text": (it.title or it.text)[:160], "rating": it.rating,
                "trust": round(it.authenticity.score, 2), "source": it.source, "url": it.url}

    return {
        "topic": brief.topic,
        "item_count": len(items),
        "avg_rating": round(_avg(ratings), 2) if _avg(ratings) is not None else None,
        "avg_trust": round(_avg(trusts), 2) if _avg(trusts) is not None else None,
        "suspicious": suspicious,
        "suspicious_share": round(suspicious / len(items), 2) if items else 0.0,
        "top_praise": snippet(praise),
        "top_complaint": snippet(complaint),
    }


def compare(summaries: list[dict]) -> dict:
    """Pick a verdict line across N summarized entities."""
    rated = [s for s in summaries if s["avg_rating"] is not None]
    verdict = None
    _TRUST_EPS = 0.03  # below this spread, treat trust scores as a tie
    if len(rated) >= 2:
        best_rating = max(rated, key=lambda s: s["avg_rating"])
        most_trusted = max(summaries, key=lambda s: s["avg_trust"] or 0)
        trusts = [s["avg_trust"] or 0 for s in summaries]
        trust_spread = max(trusts) - min(trusts)
        if trust_spread < _TRUST_EPS:
            # Authenticity is effectively equal - don't manufacture a winner.
            verdict = (
                f"{best_rating['topic']} rates highest ({best_rating['avg_rating']}); "
                f"review authenticity is comparable across the field "
                f"(trust ~{best_rating['avg_trust']})."
            )
        elif best_rating["topic"] == most_trusted["topic"]:
            verdict = (
                f"{best_rating['topic']} leads on both rating ({best_rating['avg_rating']}) "
                f"and authenticity (trust {best_rating['avg_trust']})."
            )
        else:
            # The headline Winnow insight: higher rating, but less-authentic reviews.
            verdict = (
                f"{best_rating['topic']} rates higher ({best_rating['avg_rating']}), "
                f"but {most_trusted['topic']}'s reviews are more authentic "
                f"(trust {most_trusted['avg_trust']} vs {best_rating['avg_trust']})."
            )
    return {"entities": summaries, "verdict": verdict}


def to_markdown(result: dict) -> str:
    ents = result["entities"]
    lines = ["# Winnow comparison: " + " vs ".join(e["topic"] for e in ents), ""]
    if result["verdict"]:
        lines += ["**Verdict:** " + result["verdict"], ""]
    lines.append("| Metric | " + " | ".join(e["topic"] for e in ents) + " |")
    lines.append("|---|" + "---|" * len(ents))
    lines.append("| Items | " + " | ".join(str(e["item_count"]) for e in ents) + " |")
    lines.append("| Avg rating | " + " | ".join(str(e["avg_rating"] or "-") for e in ents) + " |")
    lines.append("| Avg trust | " + " | ".join(str(e["avg_trust"] or "-") for e in ents) + " |")
    lines.append("| Suspicious | " + " | ".join(f"{e['suspicious']} ({e['suspicious_share']:.0%})" for e in ents) + " |")
    lines.append("")
    for e in ents:
        lines.append(f"## {e['topic']}")
        if e["top_praise"]:
            p = e["top_praise"]
            lines.append(f"- Praise ({p['rating']}★, trust {p['trust']}): \"{p['text']}\"")
        if e["top_complaint"]:
            c = e["top_complaint"]
            lines.append(f"- Complaint ({c['rating']}★, trust {c['trust']}): \"{c['text']}\"")
        lines.append("")
    return "\n".join(lines)
