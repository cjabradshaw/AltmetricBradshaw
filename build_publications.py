import os
import re
from pathlib import Path
import time
import yaml
import requests

PAPERS_FILE = Path("papers.yaml")
TEMPLATE_FILE = Path("index.template.html")
OUTPUT_FILE = Path("index.html")
PLACEHOLDER = "<!-- GENERATED CONTENT -->"
ALTMETRIC_API_KEY = os.environ.get("ALTMETRIC_API_KEY")
DOI_ATTR_RE = re.compile(r'data-doi="([^"]+)"')


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
    r = requests.get(
        f"https://api.altmetric.com/v1/doi/{doi}",
        params={"key": ALTMETRIC_API_KEY},
        timeout=10,
    )

    if r.status_code == 404:
        return 0.0

    if r.status_code == 403:
        raise RuntimeError(
            "Altmetric API rejected ALTMETRIC_API_KEY. "
            "Set a valid API key before rebuilding index.html."
        )

    if not r.ok:
        raise RuntimeError(
            f"Altmetric lookup failed for DOI {doi} (HTTP {r.status_code})"
        )

    data = r.json()

    if "score" not in data:
        raise RuntimeError(f"Altmetric response missing score for DOI {doi}")

    try:
        return float(data["score"])
    except (TypeError, ValueError):
        raise RuntimeError(
            f"Altmetric score for DOI {doi} is not numeric: {data.get('score')!r}"
        )


def fetch_citations(doi):
    try:
        r = requests.get(f"https://api.crossref.org/works/{doi}", timeout=10)
        if r.ok:
            return r.json()["message"].get("is-referenced-by-count", 0)
    except Exception:
        pass
    return 0


def existing_order_lookup():
    if not OUTPUT_FILE.exists():
        return {}

    html = OUTPUT_FILE.read_text(encoding="utf-8")
    ordered_dois = []
    seen = set()

    for doi in DOI_ATTR_RE.findall(html):
        if doi not in seen:
            seen.add(doi)
            ordered_dois.append(doi)

    return {doi: index for index, doi in enumerate(ordered_dois)}


# -------------------------------
# Fetch metrics for all papers
# -------------------------------

for p in papers:
    doi = p.get("doi")
    if not doi:
        raise RuntimeError("Every paper entry must include a DOI")

    p["citations"] = fetch_citations(doi)
    p["altmetric"] = None

existing_order = existing_order_lookup()

if ALTMETRIC_API_KEY:
    print("Using Altmetric API key to refresh ranking order.")

    for p in papers:
        p["altmetric"] = fetch_altmetric(p["doi"])
        time.sleep(1)

    papers = sorted(
        papers,
        key=lambda p: p["altmetric"],
        reverse=True
    )

    for i in range(len(papers) - 1):
        if papers[i]["altmetric"] < papers[i + 1]["altmetric"]:
            raise RuntimeError("Altmetric sort failed")
else:
    print("No ALTMETRIC_API_KEY set; preserving the current published paper order.")

    papers = sorted(
        papers,
        key=lambda p: existing_order.get(p["doi"], len(existing_order))
    )

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
