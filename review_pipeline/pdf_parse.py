"""
pdf_parse.py
------------
Turn the raw Indeed / Glassdoor review PDFs into clean, structured records.

Two source layouts are handled:

  * Indeed     -> each review starts with a DATE. Full month names are used,
                  in two styles: "February 12, 2026" and "26 May 2026".
                  Optional "Pros / Cons" lists and a "Ratings by topics" block
                  (which contains a per-topic star rating, e.g. Management 1.0).

  * Glassdoor  -> each review starts with an OVERALL STAR rating ("1.0") then a
                  short-month date ("Jan 7, 2026"), then job title, employment
                  status, location, "Recommend CEO approval Business outlook",
                  Pros / Cons / Advice, ending in "Helpful Share".

The parser normalises whitespace, splits the text into individual reviews,
pulls out the fields we care about, strips page navigation noise, and
de-duplicates reviews that appear more than once (the PDFs repeat some).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path

from pypdf import PdfReader

MONTHS = (
    "January|February|March|April|May|June|July|August|September|October|"
    "November|December"
)

# A review in an Indeed PDF begins with one of these date shapes.
INDEED_DATE_A = rf"(?:{MONTHS}) \d{{1,2}}, \d{{4}}"      # February 12, 2026
INDEED_DATE_B = rf"\d{{1,2}} (?:{MONTHS}) \d{{4}}"        # 26 May 2026
INDEED_DATE = re.compile(rf"\b({INDEED_DATE_A}|{INDEED_DATE_B})\b")

# A US "City, ST" location: 1-3 capitalised words then a two-letter state.
# Tight on purpose so it can't swallow a whole title sentence.
LOCATION = re.compile(r"\b([A-Z][A-Za-z.'-]+(?: [A-Z][A-Za-z.'-]+){0,2}), ([A-Z]{2})\b")

# Common job-title phrases. The first one found marks where the job title starts
# (everything before it is the review's headline). Order longest-first so e.g.
# "Lead Care Manager" wins over "Care Manager".
ROLE = re.compile(
    r"(Lead Care Manager|Lead Case Manager|Community Support Lead Case Manager|"
    r"Enhanced Care Management[- ]Lead Care Coordinator|Lead care[- ]?manager|"
    r"Lead case manager|Care Manager|Case Manager|Care Coordinator|Care coordinator|"
    r"Patient [Cc]oordinat\w+|Behavioral [Cc]oordinator|Clinical care coordinator|"
    r"Outreach Specialist|Licensed Mental Health \w+|Mental health \w+|"
    r"Associate Marriage[^A-Z]{0,4}Family Therap\w*|Associate Mental Health \w+|"
    r"Psychiatric Mental Health Nurse Practitioner|Nurse Practitioner|Therapist|"
    r"Clinician I*|Counselor|Accountant|Healthcare representative|Representative|"
    r"Receptionist|Data Entry|Team Member|Community Supports?|"
    r"Director of [A-Za-z]+(?: and [A-Za-z]+){0,2}|"
    r"Human r\w+|Behavioral coordinator|Mental health provider|Mental health therapist|"
    r"Anonymous employee|Anonymous|LCM|Lcm|ECM|Ecm)"
)

# A review in a Glassdoor PDF begins with "<rating> <short-month date>".
GLASSDOOR_ANCHOR = re.compile(
    r"\b([1-5]\.\d) "
    r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{1,2}, \d{4})\b"
)

# Phrases that mark the start of Indeed page-navigation / summary junk. When we
# see one of these inside a review body we cut the body off there.
INDEED_NOISE_MARKERS = [
    "Overall rating",
    "Jobs at ",
    "Rate your recent company",
    "What people are saying",
    "Ratings by topics",          # handled separately, but also ends the body
    " page 1 of ",
    " page 2 of ",
]


@dataclass
class Review:
    source: str                       # "Indeed" or "Glassdoor"
    date_iso: str                     # "2026-02-12"
    date_display: str                 # "Feb 12, 2026"
    year: int
    quarter: str                      # "2026-Q1"
    title: str
    job_title: str
    location: str
    employment: str                   # e.g. "Former employee, less than 1 year"
    body: str
    pros: str
    cons: str
    advice: str
    rating: float | None              # overall star rating if available (1-5)
    rating_basis: str                 # how the rating was derived
    full_text: str                    # everything, used for analysis
    # Filled in later by the sentiment / theme stages:
    sentiment: str = ""
    vader_compound: float = 0.0
    themes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# --------------------------------------------------------------------------- #
# Low-level helpers
# --------------------------------------------------------------------------- #
def _read_pdf_text(path: Path) -> str:
    """Extract every page's text and normalise whitespace to single spaces."""
    reader = PdfReader(str(path))
    raw = " ".join((page.extract_text() or "") for page in reader.pages)
    raw = raw.replace(" ", " ")            # non-breaking spaces
    raw = raw.replace("ﬁ", "fi")           # "ﬁ" ligature seen in "Beneﬁts"
    raw = re.sub(r"\s+", " ", raw)
    return raw.strip()


def _is_glassdoor(text: str) -> bool:
    return "Recommend CEO approval Business outlook" in text


def _parse_date(token: str) -> datetime:
    for fmt in ("%B %d, %Y", "%d %B %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(token.strip(), fmt)
        except ValueError:
            continue
    raise ValueError(f"Unrecognised date: {token!r}")


def _section(text: str, label: str, stops: list[str]) -> str:
    """
    Return the text of a "<label> ... " section, stopping at whichever of the
    `stops` markers (or end of string) comes first. Empty string if not found.
    """
    m = re.search(rf"\b{re.escape(label)}\b", text)
    if not m:
        return ""
    start = m.end()
    end = len(text)
    for stop in stops:
        s = re.search(rf"\b{re.escape(stop)}\b", text[start:])
        if s:
            end = min(end, start + s.start())
    return text[start:end].strip(" .,-")


def _truncate_at_noise(body: str) -> str:
    """Cut an Indeed body off at the first navigation / summary marker."""
    cut = len(body)
    for marker in INDEED_NOISE_MARKERS:
        idx = body.find(marker)
        if idx != -1:
            cut = min(cut, idx)
    return body[:cut].strip()


# --------------------------------------------------------------------------- #
# Indeed
# --------------------------------------------------------------------------- #
def _parse_indeed(text: str) -> list[Review]:
    reviews: list[Review] = []
    anchors = list(INDEED_DATE.finditer(text))
    for i, m in enumerate(anchors):
        date_token = m.group(1)
        try:
            dt = _parse_date(date_token)
        except ValueError:
            continue
        chunk_start = m.end()
        chunk_end = anchors[i + 1].start() if i + 1 < len(anchors) else len(text)
        chunk = text[chunk_start:chunk_end].strip()

        # Pull out Pros / Cons (they sit before "Ratings by topics").
        pros = _section(chunk, "Pros", ["Cons", "Ratings by topics", "Advice to Management"])
        cons = _section(chunk, "Cons", ["Ratings by topics", "Advice to Management", "Pros"])

        # Topic star ratings -> average them for an overall rating.
        rating, basis = _indeed_topic_rating(chunk)

        # The "body" is everything before Pros / Cons / Ratings, minus nav junk.
        body = chunk
        for marker in ("Pros", "Cons", "Ratings by topics"):
            idx = body.find(marker)
            if idx != -1:
                body = body[:idx]
        body = _truncate_at_noise(body)

        # First few tokens of the body are: title, job title, (location).
        title, job_title, location, body = _split_indeed_head(body)

        full_text = " ".join(x for x in (title, body, pros, cons) if x)
        if not full_text.strip():
            continue

        reviews.append(
            Review(
                source="Indeed",
                date_iso=dt.strftime("%Y-%m-%d"),
                date_display=dt.strftime("%b %d, %Y"),
                year=dt.year,
                quarter=f"{dt.year}-Q{(dt.month - 1) // 3 + 1}",
                title=title,
                job_title=job_title,
                location=location,
                employment="",
                body=body,
                pros=pros,
                cons=cons,
                advice="",
                rating=rating,
                rating_basis=basis,
                full_text=full_text,
            )
        )
    return reviews


def _indeed_topic_rating(chunk: str) -> tuple[float | None, str]:
    """Average the star numbers in a 'Ratings by topics' block, if present."""
    m = re.search(r"Ratings by topics(.*)", chunk)
    if not m:
        return None, "none"
    block = m.group(1)
    # Each topic looks like "1.0 Work/Life Balance 1.0 out of 5 stars for ..."
    stars = re.findall(r"\b([1-5]\.\d) out of 5 stars\b", block)
    if not stars:
        return None, "none"
    vals = [float(s) for s in stars]
    return round(sum(vals) / len(vals), 2), "indeed_topics"


def _extract_role(head: str) -> tuple[str, str]:
    """Split a "<Title> <Job Title>" head at the first job-title phrase."""
    m = ROLE.search(head)
    if m:
        return head[: m.start()].strip(" .,-"), head[m.start():].strip()
    return head.strip(" .,-"), ""


def _split_indeed_head(body: str) -> tuple[str, str, str, str]:
    """
    Separate the leading title / job title / location from the review prose.
    Indeed lists them right after the date with no punctuation. We anchor on a
    "City, ST" location when present; the job title is the role phrase that sits
    just before it, and the headline is whatever comes first.
    """
    location = ""
    role = ROLE.search(body[:160])
    if role:
        # Headline is before the job-title phrase; an optional "City, ST" sits
        # right after it; the prose body is whatever follows.
        title = body[: role.start()].strip(" .,-")
        job_title = role.group(0).strip()
        rest = body[role.end():].lstrip()
        loc = LOCATION.match(rest)
        if loc:
            location = loc.group(0).strip()
            rest = rest[loc.end():].lstrip()
        return title, job_title, location, rest.strip()

    # No recognised role: fall back to a "City, ST" split, else a short head.
    loc = LOCATION.search(body[:160])
    if loc:
        title = body[: loc.start()].strip(" .,-")
        location = loc.group(0).strip()
        return title, "", location, body[loc.end():].strip()
    return body[:80].strip(" .,-"), "", "", body[80:].strip()


# --------------------------------------------------------------------------- #
# Glassdoor
# --------------------------------------------------------------------------- #
def _parse_glassdoor(text: str) -> list[Review]:
    reviews: list[Review] = []
    anchors = list(GLASSDOOR_ANCHOR.finditer(text))
    for i, m in enumerate(anchors):
        rating = float(m.group(1))
        dt = _parse_date(m.group(2))
        chunk_start = m.end()
        chunk_end = anchors[i + 1].start() if i + 1 < len(anchors) else len(text)
        chunk = text[chunk_start:chunk_end].strip()

        # Header = everything up to "Recommend CEO approval Business outlook".
        head, _, rest = chunk.partition("Recommend CEO approval Business outlook")
        title, job_title, employment, location = _split_glassdoor_head(head)

        pros = _section(rest, "Pros", ["Cons", "Advice to Management", "Helpful"])
        cons = _section(rest, "Cons", ["Advice to Management", "Helpful", "Show more"])
        advice = _section(rest, "Advice to Management", ["Helpful", "Show more"])

        full_text = " ".join(x for x in (title, pros, cons, advice) if x)
        reviews.append(
            Review(
                source="Glassdoor",
                date_iso=dt.strftime("%Y-%m-%d"),
                date_display=dt.strftime("%b %d, %Y"),
                year=dt.year,
                quarter=f"{dt.year}-Q{(dt.month - 1) // 3 + 1}",
                title=title,
                job_title=job_title,
                location=location,
                employment=employment,
                body="",
                pros=pros,
                cons=cons,
                advice=advice,
                rating=rating,
                rating_basis="glassdoor_overall",
                full_text=full_text,
            )
        )
    return reviews


def _split_glassdoor_head(head: str) -> tuple[str, str, str, str]:
    """
    Header looks like:
      "<Title> <Job Title> <Former/Current employee[, tenure]> <Location?>"
    We anchor on the "Former/Current employee" phrase.
    """
    head = head.strip()
    emp = re.search(r"(Former|Current) employee(?:, [^A-Z]*?(?:year|months?))?", head)
    location = ""
    employment = ""
    if emp:
        title_job = head[: emp.start()].strip()
        employment = emp.group(0).strip()
        tail = head[emp.end():].strip()
        loc = LOCATION.search(tail)
        if loc:
            location = loc.group(0).strip()
        elif tail:
            location = tail.split(" Pros")[0].strip()[:40]
    else:
        title_job = head

    title, job_title = _extract_role(title_job)
    return title.strip(), job_title.strip(), employment, location


# --------------------------------------------------------------------------- #
# De-duplication & public entry point
# --------------------------------------------------------------------------- #
def _dedup_key(r: Review) -> tuple:
    snippet = (r.body or r.cons or r.pros or r.title).lower()
    snippet = re.sub(r"[^a-z0-9 ]", "", snippet)[:60]
    return (r.date_iso, r.title.lower()[:40], snippet)


def parse_pdfs(data_dir: str | Path) -> list[Review]:
    """Parse every PDF in `data_dir` and return de-duplicated, sorted reviews."""
    data_dir = Path(data_dir)
    pdfs = sorted(data_dir.glob("*.pdf"))
    if not pdfs:
        raise FileNotFoundError(f"No PDF files found in {data_dir}")

    all_reviews: list[Review] = []
    for pdf in pdfs:
        text = _read_pdf_text(pdf)
        parser = _parse_glassdoor if _is_glassdoor(text) else _parse_indeed
        all_reviews.extend(parser(text))

    # De-duplicate (PDFs repeat reviews, and some overlap across files).
    seen: dict[tuple, Review] = {}
    for r in all_reviews:
        seen.setdefault(_dedup_key(r), r)

    reviews = sorted(seen.values(), key=lambda r: r.date_iso)
    return reviews
