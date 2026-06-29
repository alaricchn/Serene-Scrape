"""
sentiment.py
------------
Classify each review as positive / negative / neutral.

We use two signals and prefer the strongest available:

  1. The star RATING, when the review has one (Glassdoor overall star, or the
     averaged Indeed "Ratings by topics" stars). A star rating is the
     reviewer's own explicit verdict, so it is the most trustworthy signal.

  2. VADER sentiment of the free text, used when there is no rating. VADER is a
     lexicon + rules model that handles negation, intensifiers and punctuation,
     which suits short, emotional review prose well.

The VADER lexicon is loaded from the bundled `vendor/vader_lexicon.txt` so the
project runs offline with no NLTK download step.
"""

from __future__ import annotations

from pathlib import Path

from nltk.sentiment.vader import SentimentIntensityAnalyzer, VaderConstants

# Star-rating cut-offs (out of 5).
POSITIVE_STAR = 3.5
NEGATIVE_STAR = 2.5

# VADER compound-score cut-offs (range -1 .. +1).
POSITIVE_COMPOUND = 0.25
NEGATIVE_COMPOUND = -0.25

_VENDORED_LEXICON = Path(__file__).resolve().parent.parent / "vendor" / "vader_lexicon.txt"


def _build_analyzer() -> SentimentIntensityAnalyzer:
    """Build a VADER analyzer from the vendored lexicon (no network needed)."""
    if _VENDORED_LEXICON.exists():
        sia = SentimentIntensityAnalyzer.__new__(SentimentIntensityAnalyzer)
        sia.lexicon_file = _VENDORED_LEXICON.read_text(encoding="utf-8")
        sia.lexicon = sia.make_lex_dict()
        sia.constants = VaderConstants()
        return sia
    # Fallback: let NLTK find / download the lexicon itself.
    try:
        return SentimentIntensityAnalyzer()
    except LookupError:
        import nltk
        nltk.download("vader_lexicon")
        return SentimentIntensityAnalyzer()


_ANALYZER = _build_analyzer()


def classify(text: str, rating: float | None) -> tuple[str, float]:
    """Return (label, vader_compound) for one review."""
    compound = _ANALYZER.polarity_scores(text or "")["compound"]

    if rating is not None:
        if rating >= POSITIVE_STAR:
            label = "positive"
        elif rating <= NEGATIVE_STAR:
            label = "negative"
        else:
            label = "neutral"
    else:
        if compound >= POSITIVE_COMPOUND:
            label = "positive"
        elif compound <= NEGATIVE_COMPOUND:
            label = "negative"
        else:
            label = "neutral"

    return label, round(compound, 4)


def add_sentiment(reviews) -> None:
    """Annotate each review in-place with .sentiment and .vader_compound."""
    for r in reviews:
        r.sentiment, r.vader_compound = classify(r.full_text, r.rating)
