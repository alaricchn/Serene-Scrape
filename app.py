"""
app.py — Streamlit host for the original review dashboard.

This deploys the *exact* standalone dashboard (the dark UI with summary cards,
the Chart.js trend chart, the complaint/praise theme bars, and the searchable,
sortable review table) on Streamlit Community Cloud.

It does that by embedding the self-contained HTML that the pipeline already
produces (`build_html`) inside the page, and hiding Streamlit's own chrome so
the result looks and behaves like opening `output/dashboard.html` in a browser.

Data comes from uploaded PDFs (sidebar) or the bundled sample set in ./data, so
there are no local-only assumptions and nothing is written to disk.

Run locally:  streamlit run app.py
Deploy:       Streamlit Community Cloud, main file = app.py
"""

from __future__ import annotations

import io
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from review_pipeline import parse_sources, analyze, build_html, to_csv, to_json

HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / "data"

st.set_page_config(
    page_title="Review Analysis",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Strip Streamlit's chrome and padding so the embedded dashboard fills the page
# edge-to-edge on the same dark background it uses internally.
st.markdown(
    """
    <style>
      header[data-testid="stHeader"], footer {display:none;}
      #MainMenu {visibility:hidden;}
      .block-container {padding:0 !important; max-width:100% !important;}
      [data-testid="stAppViewContainer"], [data-testid="stMain"] {background:#0f172a;}
      [data-testid="stSidebar"] {background:#1e293b;}
      iframe {border:none; display:block;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner="Analysing reviews…")
def run_pipeline(named_pdfs: tuple[tuple[str, bytes], ...]) -> dict:
    """Parse + analyse the given PDFs; return the dashboard HTML and exports."""
    reviews = parse_sources([io.BytesIO(data) for _name, data in named_pdfs])
    analyze(reviews)
    return {
        "html": build_html(reviews),
        "csv": to_csv(reviews),
        "json": to_json(reviews),
        "count": len(reviews),
    }


def bundled_pdfs() -> tuple[tuple[str, bytes], ...]:
    return tuple((p.name, p.read_bytes()) for p in sorted(DATA_DIR.glob("*.pdf")))


# --------------------------------------------------------------------------- #
# Sidebar: data input + downloads (kept out of the main view so the dashboard
# below looks exactly like the original standalone page).
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.header("Data")
    uploads = st.file_uploader(
        "Upload review PDFs", type="pdf", accept_multiple_files=True,
        help="Indeed or Glassdoor review PDFs.",
    )
    st.caption("No upload? The bundled sample reviews are shown by default.")

if uploads:
    named_pdfs = tuple((f.name, f.getvalue()) for f in uploads)
elif DATA_DIR.exists() and any(DATA_DIR.glob("*.pdf")):
    named_pdfs = bundled_pdfs()
else:
    st.warning("Upload one or more review PDFs from the sidebar to begin.")
    st.stop()

try:
    result = run_pipeline(named_pdfs)
except Exception as exc:  # surface problems instead of rendering a blank page
    st.error(f"Could not analyse the PDFs: {exc}")
    st.stop()

with st.sidebar:
    st.divider()
    st.subheader("Download")
    st.download_button("⬇️ CSV", result["csv"].encode("utf-8-sig"),
                       "reviews.csv", "text/csv", use_container_width=True)
    st.download_button("⬇️ JSON", result["json"].encode("utf-8"),
                       "reviews.json", "application/json", use_container_width=True)
    st.download_button("⬇️ HTML dashboard", result["html"].encode("utf-8"),
                       "dashboard.html", "text/html", use_container_width=True)

# --------------------------------------------------------------------------- #
# The original dashboard, embedded verbatim. Height scales with the number of
# reviews so the long table is fully visible (it scrolls if it overflows).
# --------------------------------------------------------------------------- #
height = 1180 + result["count"] * 120
components.html(result["html"], height=height, scrolling=True)
