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


def test_corpus_trust_mean():
    items = [_item("a", 1, 1.0), _item("b", 1, 0.0)]
    assert fusion.corpus_trust(items) == 0.5
    assert fusion.corpus_trust([]) == 1.0
