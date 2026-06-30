# Serene Health — Review Analysis

Turns raw **Indeed** and **Glassdoor** review PDFs into a clean, chronological
dataset and a simple visual dashboard:

- a **trend chart** of positive vs. negative reviews over time, and
- the **recurring themes** people praise vs. complain about.

There are two ways to use it: a **Streamlit web app** (`app.py`) and a
**command-line script** (`main.py`). Both share the same pipeline in
`review_pipeline/`.

---

## Option A — Streamlit app (recommended)

```powershell
pip install -r requirements.txt
streamlit run app.py
```

Your browser opens automatically. Upload review PDFs (or tick **Use bundled
sample data**) and you'll see metrics, the over-time trend chart, the
complaint/praise theme charts, a searchable table, and CSV / JSON / HTML
download buttons.

### Deploy free on Streamlit Community Cloud

1. Push this folder to a GitHub repo.
2. Go to <https://share.streamlit.io>, **New app**, pick the repo.
3. Set **Main file path** to `app.py` and deploy.

No extra configuration is needed: the dependencies are in `requirements.txt`,
the VADER lexicon is bundled in `vendor/`, and the sample PDFs in `data/` give
the app something to show before anyone uploads their own files.

---

## Option B — Command line

```powershell
pip install -r requirements.txt
python main.py            # writes output/reviews.csv, reviews.json, dashboard.html
python main.py --open     # also opens the HTML dashboard in your browser
```

Drop more PDFs into the `data/` folder and re-run to analyse new reviews.

---

## What it does (5 steps)

| Step | File | What happens |
|------|------|--------------|
| 1. Read PDFs | `review_pipeline/pdf_parse.py` | Extracts text from every PDF in `data/`. Auto-detects Indeed vs. Glassdoor layout. |
| 2. Clean | `review_pipeline/pdf_parse.py` | Normalises spacing, pulls out date / title / job / location / Pros / Cons / rating, strips page-navigation junk, removes duplicate reviews, sorts by date. |
| 3. Sentiment | `review_pipeline/sentiment.py` | Labels each review **positive / negative / neutral** — using the star rating when present, otherwise VADER text sentiment. |
| 4. Themes | `review_pipeline/themes.py` | Flags recurring topics (management, pay, micromanagement, culture, workload, turnover, …) by keyword, so we can bucket complaints and praise. |
| 5. Output | `review_pipeline/dashboard.py` | Builds the aggregates and renders them — in the Streamlit app, or as CSV / JSON / HTML files. |

The pipeline is plain Python with no Streamlit dependency, so `app.py` and
`main.py` both import it. `app.py` reads PDFs from uploaded streams **or** the
bundled `data/` folder and builds every download in memory (no disk writes), so
it has no local-only assumptions and runs cleanly on Streamlit Cloud.

## Project layout

```
app.py                     Streamlit entry point (deploy this)
main.py                    CLI entry point -> writes files to output/
requirements.txt           streamlit, pypdf, nltk, pandas, altair
data/                      sample review PDFs (bundled fallback)
vendor/vader_lexicon.txt   VADER lexicon, so sentiment works offline
review_pipeline/
  pdf_parse.py             read + clean + dedupe + sort
  sentiment.py             positive / negative / neutral
  overrides.py             manual sentiment corrections
  themes.py                recurring-theme keyword buckets
  dashboard.py             aggregates + CSV/JSON/HTML builders
```

## CLI outputs (in `output/`)

- **`dashboard.html`** — standalone page (summary cards, trend chart,
  theme charts, searchable table). Charts use the Chart.js CDN; the table works
  offline.
- **`reviews.csv`** — clean, chronological table. Opens in Excel or VSCode.
- **`reviews.json`** — the same structured data as JSON.

(The Streamlit app offers these same three as download buttons.)

## Customising

- **Add / rename themes:** edit `THEME_KEYWORDS` in
  `review_pipeline/themes.py`.
- **Correct a misread sentiment:** add a `(date, title)` line to
  `SENTIMENT_OVERRIDES` in `review_pipeline/overrides.py`.
- **Change sentiment cut-offs:** edit the constants at the top of
  `review_pipeline/sentiment.py`.
- **Different folders (CLI):** `python main.py --data <folder> --output <folder>`.

## Notes

- The VADER sentiment lexicon is bundled in `vendor/vader_lexicon.txt`, so no
  download step is required.
- Title / job-title / location are split heuristically from the PDF text (the
  PDFs run these fields together with no separators), so a few rows may look
  slightly off — the date, rating, sentiment, themes, and review text are the
  reliable analytical fields.
