import re
import yaml
import requests
from pathlib import Path

INDEX_MD = Path("index.md")
OUTPUT_YAML = Path("papers.yaml")

def initials(given):
    """
    Convert a given-name string into initials.
    'Corey J A' -> 'CJA'
    'Jean-Michel' -> 'JM'
    'Mary Ann' -> 'MA'
    """
    if not given:
        return ""
    parts = given.replace("-", " ").split()
    return "".join(p[0].upper() for p in parts if p)

# --- regex patterns ---
hr_split = re.compile(r"<hr\s*/?>", re.IGNORECASE)
img_re = re.compile(
    r'<img[^>]+src=["\']([^"\']+)["\']',
    re.IGNORECASE
)
doi_re = re.compile(
    r'https?://doi\.org/(10\.\d{4,9}/[-._;()/:A-Za-z0-9\[\]]+)',
    re.IGNORECASE
)

# --- Crossref query ---
def crossref_metadata(doi):
    url = f"https://api.crossref.org/works/{doi}"
    r = requests.get(url, timeout=15)

    if not r.ok:
        raise RuntimeError(
            f"❌ Crossref lookup failed for DOI: {doi} "
            f"(HTTP {r.status_code})"
        )

    msg = r.json().get("message")
    if not msg:
        raise RuntimeError(
            f"❌ Crossref response missing 'message' for DOI: {doi}"
        )

    # Title
    title = msg.get("title", [""])[0]

    # Year (prefer print, then online)
    year = None
    if "published-print" in msg:
        year = msg["published-print"]["date-parts"][0][0]
    elif "published-online" in msg:
        year = msg["published-online"]["date-parts"][0][0]

    # Authors
    authors = []
for a in msg.get("author", []):
    family = a.get("family", "")
    given = a.get("given", "")
    author = f"{family}, {initials(given)}".strip(", ")
    if author:
        authors.append(author)
        
    # Journal
    journal = msg.get("container-title", [""])[0]

    return {
        "title": title,
        "year": year,
        "authors": "; ".join(authors),
        "journal": journal,
    }

# --- parse index.md into blocks ---
blocks = hr_split.split(INDEX_MD.read_text(encoding="utf-8"))

papers = []

for block in blocks:
    img_match = img_re.search(block)
    doi_match = doi_re.search(block)

    if not doi_match:
        continue

    doi = doi_match.group(1)
    image = img_match.group(1) if img_match else None

    print(f"Processing DOI: {doi}")

    meta = crossref_metadata(doi)

    papers.append({
        "doi": doi,
        "year": meta["year"],
        "authors": meta["authors"],
        "title": meta["title"],
        "journal": meta["journal"],
        "image": image
    })

# --- write canonical YAML ---
with OUTPUT_YAML.open("w", encoding="utf-8") as f:
    yaml.safe_dump(
        papers,
        f,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        indent=2,
        width=120,
    )

print(f"✅ Rebuilt papers.yaml with {len(papers)} papers")
