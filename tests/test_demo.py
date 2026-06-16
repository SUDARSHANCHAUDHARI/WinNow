from lib import demo, store


def test_demo_brief_fires_detectors():
    brief = demo.build_brief(["appstore", "reddit", "youtube", "x", "pantip"])
    assert brief.topic == demo.DEMO_TOPIC
    assert brief.items
    flags = {f.name for i in brief.items for f in i.authenticity.signals}
    # the seed is engineered to exercise the full detector set
    for expected in ("review-burst", "near-duplicate", "generated-handle",
                     "rating-text-mismatch", "new-account", "low-karma"):
        assert expected in flags, f"{expected} did not fire"
    # polarization warning present
    assert any("polarized" in w for w in brief.warnings)


def test_demo_genuine_outranks_astroturf():
    brief = demo.build_brief(["appstore"])
    top = brief.items[0]
    assert top.authenticity.label == "trusted"
    # at least one suspicious astroturf item exists and ranks low
    labels = [i.authenticity.label for i in brief.items]
    assert "suspicious" in labels


def test_seed_store_creates_declining_trust(tmp_path):
    db = str(tmp_path / "demo.db")
    n = demo.seed_store(db, weeks=4)
    assert n == 4
    conn = store.connect(db)
    series = store.trust_timeseries(conn, demo.DEMO_TOPIC)
    assert len(series) == 4
    # creeping astroturf -> trust trends down, suspicious count up
    assert series[0]["avg_trust"] > series[-1]["avg_trust"]
    assert series[-1]["suspicious"] > series[0]["suspicious"]
