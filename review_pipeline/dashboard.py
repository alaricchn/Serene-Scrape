"""
dashboard.py
------------
Aggregate the analysed reviews and write the outputs:

  * output/reviews.csv   -> clean, chronological table (open in Excel / VSCode)
  * output/reviews.json  -> same data as JSON
  * output/dashboard.html -> a single self-contained page with:
        - summary cards
        - a "positive vs negative reviews over time" trend chart
        - "what people complain about" (themes in negative reviews)
        - "what people praise" (themes in positive reviews)
        - a searchable / filterable table of every review

The HTML embeds the data inline, so it opens by double-clicking. Charts are
drawn with Chart.js (loaded from a CDN); the table works with or without it.
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

SENTIMENTS = ["negative", "neutral", "positive"]


def _summary(reviews) -> dict:
    counts = Counter(r.sentiment for r in reviews)
    sources = Counter(r.source for r in reviews)
    dates = [r.date_iso for r in reviews if r.date_iso]
    return {
        "total": len(reviews),
        "negative": counts.get("negative", 0),
        "neutral": counts.get("neutral", 0),
        "positive": counts.get("positive", 0),
        "sources": dict(sources),
        "date_min": min(dates) if dates else "",
        "date_max": max(dates) if dates else "",
    }


def _timeline(reviews) -> dict:
    """Counts per quarter, split by sentiment, in chronological order."""
    buckets: dict[str, Counter] = defaultdict(Counter)
    for r in reviews:
        buckets[r.quarter][r.sentiment] += 1
    quarters = sorted(buckets)
    return {
        "labels": quarters,
        "negative": [buckets[q]["negative"] for q in quarters],
        "neutral": [buckets[q]["neutral"] for q in quarters],
        "positive": [buckets[q]["positive"] for q in quarters],
    }


def _theme_counts(reviews, sentiment: str) -> list[list]:
    counter: Counter = Counter()
    for r in reviews:
        if r.sentiment == sentiment:
            counter.update(r.themes)
    return [[theme, n] for theme, n in counter.most_common()]


def build_outputs(reviews, output_dir: str | Path) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = [r.to_dict() for r in reviews]

    # ---- reviews.json ----
    (output_dir / "reviews.json").write_text(
        json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # ---- reviews.csv ----
    csv_fields = [
        "date_iso", "date_display", "source", "rating", "rating_basis",
        "sentiment", "vader_compound", "themes", "title", "job_title",
        "location", "employment", "pros", "cons", "body", "advice",
    ]
    with (output_dir / "reviews.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=csv_fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            row = dict(row)
            row["themes"] = "; ".join(row.get("themes", []))
            writer.writerow(row)

    # ---- dashboard.html ----
    payload = {
        "summary": _summary(reviews),
        "timeline": _timeline(reviews),
        "themes_negative": _theme_counts(reviews, "negative"),
        "themes_positive": _theme_counts(reviews, "positive"),
        "reviews": [
            {
                "date_iso": r.date_iso,
                "date_display": r.date_display,
                "source": r.source,
                "rating": r.rating,
                "sentiment": r.sentiment,
                "themes": r.themes,
                "title": r.title,
                "job_title": r.job_title,
                "location": r.location,
                "snippet": (r.body or r.cons or r.pros or r.title)[:320],
            }
            for r in reviews
        ],
    }

    html = _HTML_TEMPLATE.replace(
        "/*__DATA__*/", json.dumps(payload, ensure_ascii=False)
    )
    out = output_dir / "dashboard.html"
    out.write_text(html, encoding="utf-8")
    return out


# --------------------------------------------------------------------------- #
# Self-contained HTML / CSS / JS template.
# `/*__DATA__*/` is replaced with the JSON payload above.
# --------------------------------------------------------------------------- #
_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Serene Health — Review Analysis</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
  :root{
    --bg:#0f172a; --panel:#1e293b; --panel2:#243349; --text:#e2e8f0;
    --muted:#94a3b8; --line:#334155;
    --neg:#ef4444; --neu:#94a3b8; --pos:#22c55e; --accent:#38bdf8;
  }
  *{box-sizing:border-box}
  body{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
       background:var(--bg);color:var(--text);line-height:1.5}
  header{padding:28px 32px 8px}
  h1{margin:0 0 4px;font-size:24px}
  .sub{color:var(--muted);font-size:14px}
  .wrap{padding:16px 32px 48px;max-width:1180px;margin:0 auto}
  .cards{display:flex;gap:14px;flex-wrap:wrap;margin:18px 0}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:12px;
        padding:14px 18px;min-width:130px;flex:1}
  .card .n{font-size:26px;font-weight:700}
  .card .l{color:var(--muted);font-size:13px}
  .card.neg .n{color:var(--neg)} .card.pos .n{color:var(--pos)}
  .card.neu .n{color:var(--neu)}
  .grid{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-top:6px}
  @media(max-width:860px){.grid{grid-template-columns:1fr}}
  .panel{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px}
  .panel h2{margin:0 0 12px;font-size:15px;font-weight:600}
  .panel.full{grid-column:1/-1}
  canvas{width:100%!important}
  .controls{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:22px 0 10px}
  select,input[type=search]{background:var(--panel2);color:var(--text);
      border:1px solid var(--line);border-radius:8px;padding:8px 10px;font-size:13px}
  input[type=search]{flex:1;min-width:180px}
  table{width:100%;border-collapse:collapse;font-size:13px}
  th,td{text-align:left;padding:9px 10px;border-bottom:1px solid var(--line);vertical-align:top}
  th{color:var(--muted);font-weight:600;position:sticky;top:0;background:var(--panel);cursor:pointer}
  tbody tr:hover{background:var(--panel2)}
  .pill{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;font-weight:600}
  .pill.negative{background:rgba(239,68,68,.15);color:#fca5a5}
  .pill.positive{background:rgba(34,197,94,.15);color:#86efac}
  .pill.neutral{background:rgba(148,163,184,.15);color:#cbd5e1}
  .tag{display:inline-block;background:var(--panel2);border:1px solid var(--line);
       border-radius:6px;padding:1px 6px;margin:1px 2px 1px 0;font-size:11px;color:var(--muted)}
  .src{font-size:11px;color:var(--muted)}
  .snippet{color:var(--muted);max-width:520px}
  .count{color:var(--muted);font-size:13px;margin:6px 2px}
  .note{color:var(--muted);font-size:12px;margin-top:8px}
</style>
</head>
<body>
<header>
  <h1>Serene Health — Employee Review Analysis</h1>
  <div class="sub" id="subtitle"></div>
</header>

<div class="wrap">
  <div class="cards" id="cards"></div>

  <div class="grid">
    <div class="panel full">
      <h2>Positive vs. negative reviews over time</h2>
      <canvas id="timeline" height="120"></canvas>
    </div>
    <div class="panel">
      <h2>What people complain about (negative reviews)</h2>
      <canvas id="themesNeg" height="220"></canvas>
    </div>
    <div class="panel">
      <h2>What people praise (positive reviews)</h2>
      <canvas id="themesPos" height="220"></canvas>
    </div>
  </div>

  <div class="controls">
    <select id="fSent">
      <option value="">All sentiment</option>
      <option value="negative">Negative</option>
      <option value="neutral">Neutral</option>
      <option value="positive">Positive</option>
    </select>
    <select id="fSrc">
      <option value="">All sources</option>
      <option value="Indeed">Indeed</option>
      <option value="Glassdoor">Glassdoor</option>
    </select>
    <select id="fTheme"><option value="">All themes</option></select>
    <input type="search" id="fSearch" placeholder="Search title / text…">
  </div>
  <div class="count" id="rowCount"></div>

  <div class="panel full">
    <table id="tbl">
      <thead><tr>
        <th data-k="date_iso">Date</th>
        <th data-k="source">Source</th>
        <th data-k="rating">Rating</th>
        <th data-k="sentiment">Sentiment</th>
        <th data-k="title">Title &amp; details</th>
        <th>Themes</th>
      </tr></thead>
      <tbody></tbody>
    </table>
    <div class="note">Tip: click a column header to sort. Charts need an internet
      connection (Chart.js CDN); the table works offline.</div>
  </div>
</div>

<script>
const DATA = /*__DATA__*/;
const COL = {neg:'#ef4444', neu:'#94a3b8', pos:'#22c55e'};

/* ---------- header + cards ---------- */
const s = DATA.summary;
document.getElementById('subtitle').textContent =
  `${s.total} reviews · ${s.date_min} → ${s.date_max} · ` +
  Object.entries(s.sources).map(([k,v])=>`${v} ${k}`).join(' · ');
document.getElementById('cards').innerHTML = `
  <div class="card"><div class="n">${s.total}</div><div class="l">Total reviews</div></div>
  <div class="card neg"><div class="n">${s.negative}</div><div class="l">Negative</div></div>
  <div class="card neu"><div class="n">${s.neutral}</div><div class="l">Neutral</div></div>
  <div class="card pos"><div class="n">${s.positive}</div><div class="l">Positive</div></div>`;

/* ---------- charts ---------- */
function makeCharts(){
  if(typeof Chart === 'undefined') return;        // offline: skip charts
  const t = DATA.timeline;
  new Chart(document.getElementById('timeline'), {
    type:'bar',
    data:{labels:t.labels, datasets:[
      {label:'Negative', data:t.negative, backgroundColor:COL.neg, stack:'s'},
      {label:'Neutral',  data:t.neutral,  backgroundColor:COL.neu, stack:'s'},
      {label:'Positive', data:t.positive, backgroundColor:COL.pos, stack:'s'},
    ]},
    options:{responsive:true,
      scales:{x:{stacked:true,ticks:{color:'#94a3b8'},grid:{color:'#33415544'}},
              y:{stacked:true,ticks:{color:'#94a3b8',precision:0},grid:{color:'#33415544'}}},
      plugins:{legend:{labels:{color:'#e2e8f0'}}}}
  });

  const hbar = (id, pairs, color) => new Chart(document.getElementById(id), {
    type:'bar',
    data:{labels:pairs.map(p=>p[0]), datasets:[{data:pairs.map(p=>p[1]),
          backgroundColor:color}]},
    options:{indexAxis:'y', responsive:true,
      scales:{x:{ticks:{color:'#94a3b8',precision:0},grid:{color:'#33415544'}},
              y:{ticks:{color:'#cbd5e1'},grid:{display:false}}},
      plugins:{legend:{display:false}}}
  });
  hbar('themesNeg', DATA.themes_negative.slice(0,10), COL.neg);
  hbar('themesPos', DATA.themes_positive.slice(0,10), COL.pos);
}
makeCharts();

/* ---------- table + filters ---------- */
const tbody = document.querySelector('#tbl tbody');
const fSent=document.getElementById('fSent'), fSrc=document.getElementById('fSrc'),
      fTheme=document.getElementById('fTheme'), fSearch=document.getElementById('fSearch'),
      rowCount=document.getElementById('rowCount');

const allThemes=[...new Set(DATA.reviews.flatMap(r=>r.themes))].sort();
fTheme.innerHTML='<option value="">All themes</option>'+
  allThemes.map(t=>`<option>${t}</option>`).join('');

let sortKey='date_iso', sortDir=-1;
document.querySelectorAll('#tbl th[data-k]').forEach(th=>{
  th.onclick=()=>{const k=th.dataset.k; sortDir=(k===sortKey)?-sortDir:1; sortKey=k; render();};
});

function render(){
  const sent=fSent.value, src=fSrc.value, th=fTheme.value, q=fSearch.value.toLowerCase();
  let rows=DATA.reviews.filter(r=>
    (!sent||r.sentiment===sent) && (!src||r.source===src) &&
    (!th||r.themes.includes(th)) &&
    (!q||(r.title+' '+r.snippet).toLowerCase().includes(q)));
  rows.sort((a,b)=>{
    let x=a[sortKey], y=b[sortKey];
    if(x==null)x=''; if(y==null)y='';
    return (x>y?1:x<y?-1:0)*sortDir;
  });
  rowCount.textContent=`${rows.length} of ${DATA.reviews.length} reviews`;
  tbody.innerHTML=rows.map(r=>`
    <tr>
      <td>${r.date_display||r.date_iso}</td>
      <td class="src">${r.source}</td>
      <td>${r.rating!=null?r.rating.toFixed(1)+'★':'—'}</td>
      <td><span class="pill ${r.sentiment}">${r.sentiment}</span></td>
      <td><strong>${esc(r.title)||'(untitled)'}</strong>
          <div class="src">${esc(r.job_title)}${r.location?' · '+esc(r.location):''}</div>
          <div class="snippet">${esc(r.snippet)}</div></td>
      <td>${r.themes.map(t=>`<span class="tag">${t}</span>`).join('')}</td>
    </tr>`).join('');
}
function esc(x){return (x||'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}
[fSent,fSrc,fTheme].forEach(e=>e.onchange=render);
fSearch.oninput=render;
render();
</script>
</body>
</html>
"""
