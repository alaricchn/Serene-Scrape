"""
overrides.py
------------
Manual sentiment corrections.

Some reviews have no star rating, so they are classified from their text by
VADER. VADER can misread sarcasm ("If you love micromanagement, this is the
place for you") or faint praise ("Great job if you need something quick"), and
land on the wrong label. List those reviews here to force the correct sentiment.

Each entry is keyed by (date_iso, title) so it stays stable across re-runs, and
applied AFTER automatic scoring. To correct another review, copy its date and
title from output/reviews.csv and add a line below.
"""

from __future__ import annotations

# (date_iso, exact title) -> forced sentiment ("negative" / "neutral" / "positive")
SENTIMENT_OVERRIDES: dict[tuple[str, str], str] = {
    ("2023-04-16", "I enjoy being able to show my skills. Leery of the micromanagement"): "negative",
    ("2023-10-11", "This job is not worth the pay or mental health"): "negative",
    ("2024-03-28", "Do not work here"): "negative",
    ("2025-03-23", "Toxic micromanagement"): "negative",
    ("2025-01-23", "Would not recommend to anyone"): "negative",
    ("2025-07-12", "The Worst"): "negative",
}


def apply_overrides(reviews) -> int:
    """Force-set sentiment for any review listed above. Returns count changed."""
    changed = 0
    for r in reviews:
        forced = SENTIMENT_OVERRIDES.get((r.date_iso, r.title))
        if forced and r.sentiment != forced:
            r.sentiment = forced
            changed += 1
    return changed
