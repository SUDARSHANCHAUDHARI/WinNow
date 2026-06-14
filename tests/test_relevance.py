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
