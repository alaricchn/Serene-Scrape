"""
main.py — run the whole review-analysis pipeline.

    1. Read every PDF in   ./data
    2. Clean + de-duplicate, sort chronologically by date
    3. Score sentiment (positive / negative / neutral)
    4. Flag recurring themes / complaint buckets
    5. Write outputs to    ./output  (reviews.csv, reviews.json, dashboard.html)

Usage (from this folder):
    python main.py
    python main.py --data data --output output --open
"""

from __future__ import annotations

import argparse
import webbrowser
from pathlib import Path

from review_pipeline import (
    parse_pdfs, add_sentiment, apply_overrides, add_themes, build_outputs,
)

HERE = Path(__file__).resolve().parent


def run(data_dir: Path, output_dir: Path, open_browser: bool = False) -> None:
    print(f"Reading PDFs from: {data_dir}")
    reviews = parse_pdfs(data_dir)
    print(f"  parsed {len(reviews)} unique reviews")

    add_sentiment(reviews)
    n_over = apply_overrides(reviews)
    if n_over:
        print(f"  applied {n_over} manual sentiment override(s)")
    add_themes(reviews)

    neg = sum(r.sentiment == "negative" for r in reviews)
    pos = sum(r.sentiment == "positive" for r in reviews)
    neu = sum(r.sentiment == "neutral" for r in reviews)
    print(f"  sentiment -> {neg} negative / {neu} neutral / {pos} positive")

    out = build_outputs(reviews, output_dir)
    print(f"Wrote outputs to: {output_dir}")
    print(f"  open this in your browser: {out}")

    if open_browser:
        webbrowser.open(out.as_uri())


def main() -> None:
    ap = argparse.ArgumentParser(description="Analyse Indeed/Glassdoor review PDFs.")
    ap.add_argument("--data", default=str(HERE / "data"), help="folder of PDFs")
    ap.add_argument("--output", default=str(HERE / "output"), help="output folder")
    ap.add_argument("--open", action="store_true", help="open dashboard when done")
    args = ap.parse_args()
    run(Path(args.data), Path(args.output), args.open)


if __name__ == "__main__":
    main()
