# Serene Health — Review Analysis

Turns raw **Indeed** and **Glassdoor** review PDFs into a clean, chronological
dataset and a simple visual dashboard:

- a **trend chart** of positive vs. negative reviews over time, and
- the **recurring themes** people praise vs. complain about.

Everything runs locally with one command. No data leaves your machine.

---

## Quick start

1. Install Python 3.10+ (you already have 3.13).
2. Open this folder in VSCode and open a terminal here.
3. Install the two dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

4. Run the pipeline:

   ```powershell
   python main.py
   ```

5. Open **`output/dashboard.html`** in your browser (double-click it, or run
   `python main.py --open` to open it automatically).

That's it. To analyse new reviews later, drop more PDFs into the `data/`
folder and re-run `python main.py`.

---

## What it does (5 steps)

| Step | File | What happens |
|------|------|--------------|
| 1. Read PDFs | `review_pipeline/pdf_parse.py` | Extracts text from every PDF in `data/`. Auto-detects Indeed vs. Glassdoor layout. |
| 2. Clean | `review_pipeline/pdf_parse.py` | Normalises spacing, pulls out date / title / job / location / Pros / Cons / rating, strips page-navigation junk, removes duplicate reviews, sorts by date. |
| 3. Sentiment | `review_pipeline/sentiment.py` | Labels each review **positive / negative / neutral** — using the star rating when present, otherwise VADER text sentiment. |
| 4. Themes | `review_pipeline/themes.py` | Flags recurring topics (management, pay, micromanagement, culture, workload, turnover, …) by keyword, so we can bucket complaints and praise. |
| 5. Output | `review_pipeline/dashboard.py` | Writes the CSV, JSON, and the HTML dashboard. |

## Outputs (in `output/`)

- **`dashboard.html`** — the simple UI: summary cards, the over-time trend
  chart, complaint/praise theme charts, and a searchable, sortable table of
  every review. (Charts use the Chart.js CDN, so they need internet; the table
  works offline.)
- **`reviews.csv`** — clean, chronological table. Opens in Excel or VSCode.
- **`reviews.json`** — the same structured data as JSON.

## Customising

- **Add / rename themes:** edit `THEME_KEYWORDS` in
  `review_pipeline/themes.py`.
- **Change sentiment cut-offs:** edit the constants at the top of
  `review_pipeline/sentiment.py`.
- **Different folders:** `python main.py --data <folder> --output <folder>`.

## Notes

- The VADER sentiment lexicon is bundled in `vendor/vader_lexicon.txt`, so no
  download step is required.
- Title / job-title / location are split heuristically from the PDF text (the
  PDFs run these fields together with no separators), so a few rows may look
  slightly off — the date, rating, sentiment, themes, and review text are the
  reliable analytical fields.
