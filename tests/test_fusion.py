from datetime import datetime, timezone

from lib import fusion
from lib.schema import Authenticity, Item


def _item(item_id, eng, trust, day=10):
    return Item(
        source="reddit", item_id=item_id, title=item_id, text="x", engagement=eng,
        authenticity=Authenticity(score=trust),
        published_at=datetime(2026, 6, day, tzinfo=timezone.utc),
    )


def test_authentic_low_engagement_beats_astroturf():
    astroturf = _item("fake", eng=500.0, trust=0.2)
    genuine = _item("real", eng=50.0, trust=1.0)
    ranked = fusion.rank([astroturf, genuine])
    assert ranked[0].item_id == "real"


def test_recency_breaks_ties():
    old = _item("old", eng=100.0, trust=1.0, day=1)
    new = _item("new", eng=100.0, trust=1.0, day=14)
    ranked = fusion.rank([old, new])
    assert ranked[0].item_id == "new"


def _src(item_id, source, eng, trust=1.0, day=10):
    return Item(source=source, item_id=item_id, title=item_id, text="x", engagement=eng,
                authenticity=Authenticity(score=trust),
                published_at=datetime(2026, 6, day, tzinfo=timezone.utc))


def test_top_review_beats_higher_engagement_youtube():
    # Cross-source: a top App Store review (10 helpful) must outrank a mid-tier
    # YouTube video (1000 views) even though the video has 100x the raw number,
    # because each is scored relative to its own source.
    yt_high = _src("yt_high", "youtube", 1_000_000)
    yt_low = _src("yt_low", "youtube", 1_000)
    review = _src("review", "appstore", 10)  # top (only) item of its source
    ranked = fusion.rank([yt_high, yt_low, review])
    order = [i.item_id for i in ranked]
    assert order.index("review") < order.index("yt_low")  # not buried by raw scale
    assert "yt_high" in order[:2]  # both source-leaders rank at the top


def test_zero_engagement_source_ordered_by_recency():
    # Reddit RSS: all engagement 0 -> recency must still order them.
    old = _src("old", "reddit", 0.0, day=1)
    new = _src("new", "reddit", 0.0, day=14)
    ranked = fusion.rank([old, new])
    assert ranked[0].item_id == "new"


def test_diversity_floor_keeps_minority_source():
    # 10 high-score appstore items + 3 low-score reddit items, limit 5.
    # The diversity floor must keep >=2 reddit items in the result.
    pool = [_src(f"app{i}", "appstore", 100 - i) for i in range(10)]
    pool += [_src(f"rd{i}", "reddit", 0.0) for i in range(3)]
    ranked = fusion.rank(pool, limit=5, min_per_source=2)
    sources = [i.source for i in ranked]
    assert sources.count("reddit") >= 2
    assert len(ranked) == 5


def test_corpus_trust_mean():
    items = [_item("a", 1, 1.0), _item("b", 1, 0.0)]
    assert fusion.corpus_trust(items) == 0.5
    assert fusion.corpus_trust([]) == 1.0
