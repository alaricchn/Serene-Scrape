"""Review analysis pipeline for Indeed / Glassdoor review PDFs."""

from .pdf_parse import parse_pdfs, parse_sources, Review
from .sentiment import add_sentiment
from .overrides import apply_overrides
from .themes import add_themes
from .dashboard import (
    build_outputs, build_html, to_csv, to_json, compute_payload,
)


def analyze(reviews) -> list:
    """Run the analysis stages (sentiment -> overrides -> themes) in place."""
    add_sentiment(reviews)
    apply_overrides(reviews)
    add_themes(reviews)
    return reviews


__all__ = [
    "parse_pdfs", "parse_sources", "Review", "analyze",
    "add_sentiment", "apply_overrides", "add_themes",
    "build_outputs", "build_html", "to_csv", "to_json", "compute_payload",
]
