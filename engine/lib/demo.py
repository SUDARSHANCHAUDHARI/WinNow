"""Deterministic demo seed for POC / MVP demos - no network, no credentials.

Builds a corpus for a fictional app ("Acme Notes") engineered so every
authenticity detector visibly fires: a coordinated 5-star burst from new
accounts with near-duplicate text, a rating/text mismatch, thin-text, plus
genuine reviews and social posts. `seed_store` writes several backdated runs
with creeping astroturf so the dashboard trend chart shows trust declining.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from . import authenticity, fusion, store
from .schema import Brief, Item

DEMO_TOPIC = "Acme Notes"


def _days_ago(n: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=n)


def _genuine() -> list[Item]:
    return [
        Item(source="appstore", item_id="g1", title="Solid daily driver",
             text="Been using it for two years. The offline sync finally works well after the last update.",
             rating=5.0, engagement=14, author="Maria K", published_at=_days_ago(3),
             url="https://apps.apple.com/r/g1"),
        Item(source="appstore", item_id="g2", title="Good but pricey",
             text="Genuinely useful for project notes, though the subscription jump annoyed me.",
             rating=4.0, engagement=9, author="devon_p", published_at=_days_ago(6),
             url="https://apps.apple.com/r/g2"),
        Item(source="appstore", item_id="g3", title="Sync bug ruined it",
             text="After 9.2 my notes stopped syncing across devices and support has been silent for a week.",
             rating=1.0, engagement=22, author="frustrated_pm", published_at=_days_ago(4),
             url="https://apps.apple.com/r/g3"),
        Item(source="playstore", item_id="p1", title="",
             text="Widget keeps resetting on Android 15 but the editor itself is great.",
             rating=3.0, engagement=5, author="Sam O", published_at=_days_ago(8),
             url="https://play.google.com/store/apps/details?id=com.acme.notes"),
        Item(source="reddit", item_id="r1", title="Acme Notes vs the alternatives",
             text="Switched from a competitor. The database views are the killer feature for me.",
             engagement=180, author="/u/notetaker", published_at=_days_ago(5),
             metadata={"subreddit": "r/productivity", "account_age_days": 2200, "total_karma": 40000},
             url="https://www.reddit.com/r/productivity/x/r1"),
        Item(source="youtube", item_id="y1", title="Acme Notes review 2026: still worth it?",
             text="Acme Notes review 2026: still worth it?",
             engagement=42000, author="Productive Setups", published_at=_days_ago(11),
             metadata={"channel": "Productive Setups"},
             url="https://www.youtube.com/watch?v=y1"),
        Item(source="x", item_id="x1", title="acme notes shipped real offline mode",
             text="acme notes finally shipped real offline mode and it actually works on the train",
             engagement=320, author="@indiedev", published_at=_days_ago(2),
             metadata={"likes": 290, "retweets": 30}, url="https://x.com/indiedev/status/x1"),
        Item(source="pantip", item_id="pt1", title="รีวิว Acme Notes ใช้ดีไหม",
             text="ลองใช้ Acme Notes มาเดือนนึง ฟีเจอร์จดโน้ตดีมาก แต่ราคาแพงไปนิด",
             engagement=0, author="สมชาย", published_at=_days_ago(7),
             metadata={"feed": "pantip/tech"}, url="https://pantip.com/topic/pt1"),
    ]


def _astroturf(count: int) -> list[Item]:
    """A coordinated 5-star push: same day, near-duplicate text, new low-karma
    accounts. Fires burst + near-duplicate + new-account + generated-handle."""
    blurb = "Best notes app ever amazing love it five stars highly recommend to everyone download now"
    items = []
    for i in range(count):
        items.append(Item(
            source="appstore", item_id=f"a{i}", title="Amazing app!!!",
            text=blurb, rating=5.0, engagement=1, author=f"user_{10000 + i}",
            published_at=_days_ago(1), url=f"https://apps.apple.com/r/a{i}"))
    # one rating/text mismatch planted alongside
    items.append(Item(
        source="appstore", item_id="m1", title="Love it",
        text="great app but it keeps crashing, freezes constantly and is basically unusable now, terrible",
        rating=5.0, engagement=2, author="qz882", published_at=_days_ago(1),
        url="https://apps.apple.com/r/m1"))
    # a brand-new low-karma Reddit account shilling - fires the OAuth-path signals
    items.append(Item(
        source="reddit", item_id="sh1", title="Acme Notes is the GOAT, everyone switch now",
        text="honestly the best app, just download it, trust me you will love it",
        engagement=3, author="/u/acmefan2026", published_at=_days_ago(1),
        metadata={"subreddit": "r/notes", "account_age_days": 4, "total_karma": 6},
        url="https://www.reddit.com/r/notes/x/sh1"))
    return items


def seed_items(astroturf_count: int = 5) -> list[Item]:
    return _genuine() + _astroturf(astroturf_count)


def build_brief(sources: list[str], astroturf_count: int = 5) -> Brief:
    items = [it for it in seed_items(astroturf_count) if it.source in sources]
    authenticity.score_corpus(items)
    ranked = fusion.rank(items, limit=25)
    brief = Brief(topic=DEMO_TOPIC, items=ranked)
    pol = authenticity.rating_polarization(items)
    if pol is not None and pol >= 0.7:
        brief.warnings.append(
            f"Ratings are {pol:.0%} polarized (1/5-star extremes) - a manipulation signature."
        )
    trust = fusion.corpus_trust(items)
    if trust < 0.6 and items:
        brief.warnings.append(f"Low corpus trust ({trust:.0%}) - heavy burst/duplicate signals.")
    return brief


def seed_store(db_path: str, weeks: int = 4) -> int:
    """Write `weeks` backdated runs with creeping astroturf so trust declines
    over time. Returns the number of runs written."""
    conn = store.connect(db_path)
    sources = ["appstore", "reddit", "youtube", "x", "pantip"]
    for w in range(weeks):
        # more astroturf each week -> trust trends down
        brief = build_brief(sources, astroturf_count=2 + w * 3)
        brief.generated_at = _days_ago((weeks - 1 - w) * 7)
        store.save_run(conn, DEMO_TOPIC, sources, brief)
    conn.close()
    return weeks
