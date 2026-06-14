from datetime import datetime, timezone

from lib import compare
from lib.schema import Authenticity, Brief, Item


def _it(rating, trust, text="a sufficiently long review body about the product"):
    return Item(source="appstore", item_id=f"{rating}-{trust}-{text[:5]}", title="", text=text,
                rating=rating, engagement=5.0, authenticity=Authenticity(score=trust),
                published_at=datetime(2026, 6, 1, tzinfo=timezone.utc))


def _brief(topic, items):
    return Brief(topic=topic, items=items)


def test_summarize_metrics():
    s = compare.summarize(_brief("A", [_it(5, 1.0), _it(1, 0.9), _it(5, 0.2)]))
    assert s["item_count"] == 3
    assert s["avg_rating"] == round((5 + 1 + 5) / 3, 2)
    assert s["suspicious"] == 1  # trust 0.2 -> suspicious
    assert s["top_praise"]["rating"] == 5
    assert s["top_complaint"]["rating"] == 1


def test_verdict_flags_higher_rating_but_lower_trust():
    # B rates higher but on astroturf; A is more authentic.
    a = compare.summarize(_brief("Notion", [_it(4, 1.0), _it(5, 0.95)]))
    b = compare.summarize(_brief("Obsidian", [_it(5, 0.2), _it(5, 0.25)]))
    result = compare.compare([a, b])
    assert "Obsidian rates higher" in result["verdict"]
    assert "Notion" in result["verdict"] and "more authentic" in result["verdict"]


def test_single_leader_when_best_at_both():
    a = compare.summarize(_brief("A", [_it(5, 1.0), _it(5, 0.95)]))
    b = compare.summarize(_brief("B", [_it(3, 0.9), _it(2, 0.8)]))
    result = compare.compare([a, b])
    assert "leads on both" in result["verdict"]


def test_tie_does_not_manufacture_authenticity_winner():
    # Both fully trusted -> must NOT claim one is "more authentic".
    a = compare.summarize(_brief("Notion", [_it(3, 1.0), _it(4, 1.0)]))
    b = compare.summarize(_brief("Obsidian", [_it(5, 1.0), _it(4, 1.0)]))
    result = compare.compare([a, b])
    assert "more authentic" not in result["verdict"]
    assert "comparable" in result["verdict"]
    assert "Obsidian rates highest" in result["verdict"]


def test_markdown_table_has_all_entities():
    a = compare.summarize(_brief("A", [_it(5, 1.0)]))
    b = compare.summarize(_brief("B", [_it(4, 0.9)]))
    md = compare.to_markdown(compare.compare([a, b]))
    assert "Winnow comparison: A vs B" in md
    assert "| Avg trust |" in md
    assert "## A" in md and "## B" in md
