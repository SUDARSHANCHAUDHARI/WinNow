from datetime import datetime, timezone

from lib import authenticity
from lib.schema import Item


def _item(item_id, text, author="real_person_42x", day=10, eng=100.0):
    return Item(
        source="appstore", item_id=item_id, title="", text=text, author=author,
        published_at=datetime(2026, 6, day, tzinfo=timezone.utc), engagement=eng,
    )


def test_rating_text_mismatch_high_star_negative_text():
    it = _item("m", "this app keeps crashing, freezes, totally useless and broken now", day=5)
    it.rating = 5.0
    authenticity.score_corpus([it, _item("o", "some other unrelated review body here", day=9)])
    assert any(s.name == "rating-text-mismatch" for s in it.authenticity.signals)


def test_rating_text_mismatch_skips_when_no_rating():
    it = _item("m", "crashing broken useless terrible garbage", day=5)  # no rating (social post)
    authenticity.score_corpus([it])
    assert not any(s.name == "rating-text-mismatch" for s in it.authenticity.signals)


def test_rating_polarization():
    mid = [_item(f"m{i}", "ok decent fine", day=i % 20 + 1) for i in range(4)]
    for m in mid:
        m.rating = 3.0
    extremes = [_item(f"e{i}", "text", day=i % 20 + 1) for i in range(12)]
    for i, e in enumerate(extremes):
        e.rating = 5.0 if i % 2 == 0 else 1.0
    assert authenticity.rating_polarization(mid + extremes) >= 0.7
    assert authenticity.rating_polarization(mid[:3]) is None  # too few


def test_clean_item_stays_trusted():
    items = [_item(str(i), f"genuinely useful review number {i} about the app sync feature")
             for i in range(6)]
    # spread across days so no burst
    for offset, it in enumerate(items):
        it.published_at = datetime(2026, 6, 1 + offset, tzinfo=timezone.utc)
    authenticity.score_corpus(items)
    assert all(i.authenticity.score >= 0.9 for i in items)
    assert all(i.authenticity.label == "trusted" for i in items)


def test_review_burst_penalized():
    # A genuine spike: 6 items on day 10 against a multi-day baseline (days 2, 5).
    items = [_item(str(i), f"distinct text body alpha bravo charlie {i} delta echo") for i in range(8)]
    for it in items[:6]:
        it.published_at = datetime(2026, 6, 10, tzinfo=timezone.utc)
    items[6].published_at = datetime(2026, 6, 2, tzinfo=timezone.utc)
    items[7].published_at = datetime(2026, 6, 5, tzinfo=timezone.utc)
    authenticity.score_corpus(items)
    bursty = [i for i in items if i.published_at.day == 10]
    assert all(any(s.name == "review-burst" for s in i.authenticity.signals) for i in bursty)
    assert all(i.authenticity.score < 0.8 for i in bursty)


def test_no_burst_on_recency_slice():
    # Newest-first fetch puts everything on ~one day; must NOT flag as a push.
    items = [_item(str(i), f"unique review text number {i} about feature {i}") for i in range(8)]
    for it in items:
        it.published_at = datetime(2026, 6, 12, tzinfo=timezone.utc)
    authenticity.score_corpus(items)
    assert not any(
        any(s.name == "review-burst" for s in i.authenticity.signals) for i in items
    )


def test_near_duplicate_penalized():
    shared = "best app ever amazing fantastic love it five stars highly recommend to everyone"
    items = [_item("a", shared, day=1), _item("b", shared, day=8), _item("c", shared, day=15)]
    authenticity.score_corpus(items)
    flagged = [i for i in items if any(s.name == "near-duplicate" for s in i.authenticity.signals)]
    assert len(flagged) >= 2


def test_thin_text_and_anon():
    items = [_item("x", "great", author=""), _item("y", "ok fine good", author="user_99")]
    authenticity.score_corpus(items)
    assert any(s.name == "thin-text" for s in items[0].authenticity.signals)
    assert any(s.name == "anon-author" for s in items[0].authenticity.signals)
    assert any(s.name == "generated-handle" for s in items[1].authenticity.signals)


def test_weighted_score_discounts_engagement():
    it = _item("z", "great", author="", eng=1000.0)
    authenticity.score_corpus([it, _item("z2", "another thing entirely here", day=20)])
    assert it.weighted_score < it.engagement  # authenticity < 1 dragged it down
