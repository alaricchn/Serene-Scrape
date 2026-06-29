"""
themes.py
---------
Bucket each review into recurring workplace THEMES by keyword matching.

A theme is flagged when any of its keywords/phrases appears in the review text.
A single review can carry several themes (e.g. "micromanagement" + "pay").
Downstream we count how often each theme shows up inside negative reviews
(what people complain about) versus positive reviews (what people praise).

Keep this list readable and easy to extend: add a theme, add its keywords,
done. Keywords are matched case-insensitively on word boundaries.
"""

from __future__ import annotations

import re

# theme name -> list of trigger words / phrases
THEME_KEYWORDS: dict[str, list[str]] = {
    "Management & Leadership": [
        "management", "manager", "managers", "leadership", "supervisor",
        "supervisors", "ceo", "coo", "hr", "human resources", "director",
        "upper management", "site manager", "leaders",
    ],
    "Micromanagement & Surveillance": [
        "micromanag", "micro-manag", "micro manag", "cameras", "watched",
        "monitored", "surveillance", "tracking", "every move", "watching",
        "documented", "double documentation", "metrics", "quota", "kpi",
    ],
    "Pay & Benefits": [
        "pay", "paid", "salary", "wage", "wages", "underpaid", "compensation",
        "compensate", "benefits", "pto", "401k", "insurance", "bonus",
        "bonuses", "raise", "mileage", "low pay", "mid pay",
    ],
    "Workload & Burnout": [
        "workload", "overworked", "burnout", "burned out", "burnt out",
        "case load", "caseload", "overtime", "long hours", "stress",
        "stressful", "exhausting", "exhausted", "overloaded", "high needs",
        "unrealistic expectations", "boundaries", "drained",
    ],
    "Culture & Toxicity": [
        "toxic", "cliquey", "hostile", "drama", "gaslit", "gaslight",
        "gaslighting", "bully", "bullies", "bullying", "favoritism",
        "nepotism", "office politics", "politics", "retaliat", "negativity",
        "condescending", "passive-aggressive", "passive aggressive",
        "disrespect", "belittl", "unprofessional",
    ],
    "Career Growth & Advancement": [
        "growth", "advancement", "promotion", "promote", "career",
        "opportunities", "move up", "no room", "stepping stone", "dead end",
    ],
    "Training & Onboarding": [
        "training", "trained", "onboarding", "no training", "poor training",
        "learn the job", "no support", "lack of support",
    ],
    "Communication & Organization": [
        "communication", "disorganized", "unorganized", "disorganised",
        "chaotic", "chaos", "organization", "inconsistent", "last-minute",
        "last minute", "unclear", "no structure", "poor planning",
        "miscommunication", "accountability",
    ],
    "Turnover & Retention": [
        "turnover", "turn over", "quit", "quitting", "retention",
        "high turnover", "people leave", "don't stay", "no one stays",
        "left and right",
    ],
    "Coworkers & Team": [
        "coworker", "co-worker", "colleagues", "teammates", "the team",
        "team members", "great people", "second family", "friendships",
        "supportive team", "great team",
    ],
    "Meaningful / Patient Work": [
        "members", "patients", "clients", "helping people", "rewarding",
        "mission", "community", "make a difference", "underserved",
        "patient care", "help others", "fulfilling",
    ],
    "Flexibility & Schedule": [
        "flexible", "flexibility", "remote", "work from home", "hybrid",
        "schedule", "4/10", "telehealth", "no flexibility",
    ],
    "Work Conditions & Safety": [
        "fleas", "flea", "infestation", "unsafe", "covid", "ac does not",
        "restroom", "working conditions", "dress code", "safety",
    ],
}

# Pre-compile a single regex per theme for speed.
_COMPILED: dict[str, re.Pattern] = {
    theme: re.compile(
        "|".join(re.escape(k) for k in sorted(keywords, key=len, reverse=True)),
        re.IGNORECASE,
    )
    for theme, keywords in THEME_KEYWORDS.items()
}


def detect_themes(text: str) -> list[str]:
    """Return the list of themes whose keywords appear in `text`."""
    text = text or ""
    return [theme for theme, pat in _COMPILED.items() if pat.search(text)]


def add_themes(reviews) -> None:
    """Annotate each review in-place with .themes."""
    for r in reviews:
        r.themes = detect_themes(r.full_text)
