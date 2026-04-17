from pathlib import Path
import time
import yaml
import requests

PAPERS_FILE = Path("papers.yaml")
TEMPLATE_FILE = Path("index.template.html")
OUTPUT_FILE = Path("index.html")
PLACEHOLDER = "<!-- GENERATED CONTENT -->"


# -------------------------------
# Load data
# -------------------------------
with PAPERS_FILE.open(encoding="utf-8") as f:
    papers = yaml.safe_load(f)

if not isinstance(papers, list):
    raise RuntimeError("papers.yaml must contain a list")


# -------------------------------
# APIs
# -------------------------------
def fetch_altmetric(doi):
    try:
        r = requests.get(f"https://api.altmetric.com/v1/doi/{doi}", timeout=10)
        if r.ok:
            return r.json().get("score", 0)
    except Exception:
        pass
    return 0


def fetch_citations(doi):
    try:
        r = requests.get(f"https://api.crossref.org/works/{doi}", timeout=10)
        if r.ok:
            return r.json()["message"].get("is-referenced-by-count", 0)
    except Exception:
        pass
    return 0


# -------------------------------
# Fetch metrics
# -------------------------------
for p in papers:
    doi = p.get("doi")
    if not doi:
        p["altmetric"] = 0
        p["citations"] = 0
        continue

    p["altmetric"] = fetch_altmetric(doi)
    p["citations"] = fetch_citations(doi)
    time.sleep(1)


papers.sort(key=lambda p: p.get("altmetric", 0), reverse=True)


# -------------------------------
# Render HTML
# -------------------------------
items = []

for p in papers:
    doi = p.get("doi", "")
    title = p.get("title", "")
    authors = p.get("authors", "")
    journal = p.get("journal", "")
    year = p.get("year") or "n.d."
    image = p.get("image")
    alt = p.get("altmetric", 0)
    cites = p.get("citations", 0)

    icon = f'<img src="{image}" class="paper-icon" alt="Journal icon">' if image else ""

    items.append(
    f'<li class="paper">'
    f'  <div class="paper-row">'
    f'    <div class="citation">'
    f'      {authors} {year}. '
    f'      <a href="https://doi.org/{doi}">{title}</a>. '
    f'      <span class="journal"><em>{journal}</em></span>. '
    f'      doi:{doi}'
    f'    </div>'
    f'    <div class="paper-icon-container">{icon}</div>'
    f'  </div>'
    f'  <div class="metrics-row">'
    f'    <span class="altmetric-embed" '
    f'          data-badge-type="donut" '
    f'          data-doi="{doi}"></span>'
    f'    <span class="metrics">citations: {cites}</span>'
    f'  </div>'
    f'</li>'
    f'<hr>'
)

html = TEMPLATE_FILE.read_text(encoding="utf-8")

if "<!-- GENERATED CONTENT -->" not in html:
    raise RuntimeError("Missing <!-- GENERATED CONTENT --> in index.template.html")

html = html.replace("<!-- GENERATED CONTENT -->", "\n\n".join(items))
OUTPUT_FILE.write_text(html, encoding="utf-8")

print(f"✅ index.html regenerated with {len(items)} papers")
