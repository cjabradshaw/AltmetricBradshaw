"""
Build index.html from papers.yaml with:
- Clean academic formatting
- Clickable paper titles
- Altmetric donuts
- Crossref citation counts
- Sorting by Altmetric score (descending)
"""

import yaml
import requests
import time
from pathlib import Path

# -----------------------
# Files
# -----------------------
PAPERS_FILE = Path("papers.yaml")
INDEX_FILE = Path("index.html")

# -----------------------
# Load papers
# -----------------------
with PAPERS_FILE.open(encoding="utf-8") as f:
    papers = yaml.safe_load(f)

if not isinstance(papers, list):
    raise RuntimeError("papers.yaml must contain a list")

# -----------------------
# API helpers
# -----------------------
def altmetric_score(doi):
    """Fetch Altmetric score for a DOI."""
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


def citation_count(doi):
    """Fetch Crossref citation count for a DOI."""
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


# -----------------------
# Fetch metrics
# -----------------------
for p in papers:
    doi = p.get("doi")
    if not doi:
        p["altmetric"] = 0
        p["citations"] = 0
        continue

    print(f"Fetching metrics for {doi}")

    p["altmetric"] = altmetric_score(doi)
    p["citations"] = citation_count(doi)

    # Be polite to APIs
    time.sleep(1)


# -----------------------
# Sort by Altmetric score
# -----------------------
papers.sort(key=lambda x: x.get("altmetric", 0), reverse=True)


# -----------------------
# Generate HTML list items
# -----------------------
items = []

for p in papers:
    year = p.get("year")
    year_display = year if year is not None else "n.d."

    authors = p.get("authors", "").strip()
    title = p.get("title", "").strip()
    doi = p.get("doi", "").strip()

    alt = p.get("altmetric", 0)
    cites = p.get("citations", 0)

    item_html = f"""
<li class="paper"
    data-altmetric="{alt}"
    data-citations="{cites}"
    data-year="{year_display}">
  <div class="citation">
    <strong>{authors}</strong> ({year_display}).<br>
    <a href="https://doi.org/{doi}" target="_blank" rel="noopener noreferrer">
      {title}
    </a>
  </div>
  <div class="badges">
    <span class="altmetric-embed"
          data-badge-type="donut"
          data-doi="{doi}">
    </span>
    <span class="metrics">
      Altmetric: {alt} &bull; Citations: {cites}
    </span>
  </div>
</li>
"""
    items.append(item_html.strip())


# -----------------------
# Inject into index.html
# -----------------------
html = INDEX_FILE.read_text(encoding="utf-8")

if "<!-- GENERATED CONTENT -->" not in html:
    raise RuntimeError(
        "index.html must contain <!-- GENERATED CONTENT --> placeholder"
    )

html = html.replace(
    "<!-- GENERATED CONTENT -->",
    "\n".join(items)
)

INDEX_FILE.write_text(html, encoding="utf-8")

print(f"✅ index.html regenerated successfully ({len(items)} papers)")

