import re
import yaml
from pathlib import Path

INDEX_MD = Path("index.md")
OUTPUT_YAML = Path("papers.yaml")

# Regex helpers
doi_re = re.compile(r"(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)")
year_re = re.compile(r"\b(19|20)\d{2}\b")
img_re = re.compile(
    r"(https://coreybradshaw\.files\.wordpress\.com/[^\s\"'>]+)",
    re.IGNORECASE
)

text = INDEX_MD.read_text(encoding="utf-8")

# Split into paper blocks by blank lines
blocks = [b.strip() for b in text.split("\n\n") if b.strip()]

papers = []

for block in blocks:
    doi_match = doi_re.search(block)
    if not doi_match:
        continue

    doi = doi_match.group(1)

    # Image (optional)
    img_match = img_re.search(block)
    image = img_match.group(1) if img_match else None

    # Year
    year_match = year_re.search(block)
    year = int(year_match.group(0)) if year_match else None

    # Collapse whitespace for title extraction
    clean = re.sub(r"\s+", " ", block)

    # Attempt to extract title:
    # assume title is sentence after year, before DOI
    title = None
    if year:
        after_year = clean.split(str(year), 1)[1]
        before_doi = after_year.split(doi, 1)[0]
        title = before_doi.strip(" .")
    else:
        title = None

    # Authors = everything before year
    if year:
        authors = clean.split(str(year), 1)[0].strip(" .,-")
    else:
        authors = None

    papers.append({
        "doi": doi,
        "year": year,
        "authors": authors,
        "title": title,
        "image": image
    })

print(f"✅ Parsed {len(papers)} papers from index.md")

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

print("✅ papers.yaml written successfully")
