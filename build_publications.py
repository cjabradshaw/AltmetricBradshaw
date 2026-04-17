"""
Build index.html from papers.yaml, rendering:
- journal / outlet icons (from WordPress image URLs)
- clean citation text
- Altmetric donuts
- Crossref citation counts
- sorted by Altmetric score (descending)
"""

from pathlib import Path
import time
import yaml
import requests

# ---------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------
PAPERS_FILE = Path("papers.yaml")
INDEX_FILE = Path("index.html")

PLACEHOLDER = "<!-- GENERATED CONTENT -->"

# ---------------------------------------------------------------------
# Load papers
# ---------------------------------------------------------------------
with PAPERS_FILE.open(encoding="utf-8") as f:
    papers = yaml.safe_load(f)

if not isinstance(papers, list):
    raise RuntimeError("papers.yaml must contain a list of papers")

# ---------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------
def fetch_altmetric(doi):
    try:
        r = requests.get(
            f"https://api.altmetric.com/v1/doi/{doi}",
            timeout=10
        )
        if r.ok:
            return r.json().get("score", 0)
    except Exception:
        pass
    return 0


def fetch_citations(doi):
    try:
        r = requests.get(
            f"https://api.crossref.org/works/{doi}",
            timeout=10
        )
        if r.ok:
            return r.json()["message"].get("is-referenced-by-count", 0)
    except Exception:
        pass
    return 0

# ---------------------------------------------------------------------
# Fetch metrics
# ---------------------------------------------------------------------
for p in papers:
    doi = p.get("doi")
    if not doi:
        p["altmetric"] = 0
        p["citations"] = 0
        continue

    print(f"Fetching metrics for {doi}")

    p["altmetric"] = fetch_altmetric(doi)
    p["citations"] = fetch_citations(doi)

    # be polite
    time.sleep(1)

# ---------------------------------------------------------------------
# Sort by Altmetric score
# ---------------------------------------------------------------------
papers.sort(key=lambda x: x.get("altmetric", 0), reverse=True)

# ---------------------------------------------------------------------
# Generate HTML
# ---------------------------------------------------------------------
items = []

for p in papers:
    doi = p.get("doi", "")
    title = p.get("title", "")
    authors = p.get("authors", "")
    journal = p.get("journal", "")
    year = p.get("year")
    year_display = year if year is not None else "n.d."

    image = p.get("image")
    alt = p.get("altmetric", 0)
    cites = p.get("citations", 0)

    # icon (optional)
    icon_html = (
        f'<img src="{image}" class="paper-icon" alt="Journal icon">' 
        if image else ""
    )

    item_html = f"""
<li class="paper"
    data-altmetric="{alt}"
    data-citations="{cites}"
    data-year="{year_display}">
  <div class="citation">
    {icon_html}
    <strong>{authors}</strong> ({year_display}).<br>
    https://doi.org/{doi}>
      {title}
    </a><br>
    <span class="journal">{journal}</span>
  </div>

  <div class="metrics-row">
    <span class="altmetric-embed"
          data-badge-type="donut"
          data-doi="{doi}">
    </span>
    <span class="metrics">
      Altmetric: {alt} • Citations: {cites}
    </span>
  </div>
</li>
""".strip()

    items.append(item_html)

# ---------------------------------------------------------------------
# Inject into index.html
# ---------------------------------------------------------------------
html = INDEX_FILE.read_text(encoding="utf-8")

if PLACEHOLDER not in html:
    raise RuntimeError(
        "index.html must contain <!-- GENERATED CONTENT -->"
    )

html = html.replace(PLACEHOLDER, "\n\n".join(items))
INDEX_FILE.write_text(html, encoding="utf-8")

print(f"✅ index.html regenerated successfully ({len(items)} papers)")
