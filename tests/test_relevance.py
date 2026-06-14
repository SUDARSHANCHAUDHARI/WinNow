from lib import relevance


def test_primary_entity_is_longest_significant_token():
    assert relevance.primary_entity("Notion bug") == "notion"
    assert relevance.primary_entity("best app for notes") == "notes"
    assert relevance.primary_entity("the a an") == ""  # all stopwords


def test_matches_requires_primary_entity():
    assert relevance.matches("Notion bug", "Notion keeps crashing on iOS")
    assert relevance.matches("Notion", "my workflow", "r/Notion")  # in subreddit surface
    assert not relevance.matches("Notion bug", "DISCOUTHUB official sale 12 month warranty")
    assert not relevance.matches("Notion", "Austin tech meetups and investor relations")


def test_empty_topic_keeps_everything():
    assert relevance.matches("the for", "literally anything")


def test_passes_context_noop_without_terms():
    assert relevance.passes_context("anything at all") is True


def test_passes_context_exclude_drops_off_sense():
    # "Notion" the band vs the app.
    assert not relevance.passes_context(
        "Notion official music video by The Rare Occasions",
        exclude=["music video", "lyrics", "song"],
    )
    assert relevance.passes_context(
        "Notion app review: the new sync feature",
        exclude=["music video", "lyrics", "song"],
    )


def test_passes_context_include_requires_in_sense():
    assert relevance.passes_context("Notion workspace tips", include=["app", "workspace", "software"])
    assert not relevance.passes_context("Notion guitar tab", include=["app", "workspace", "software"])
