import re
import yaml
from pathlib import Path

INDEX_MD = Path("index.md")
OUTPUT_YAML = Path("papers.yaml")

# Regex patterns
doi_link_re = re.compile(
    r"\[([^\]]+)\]\(https?://doi\.org/(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)\)"
)
year_re = re.compile(r"\b(19|20)\d{2}\b")

papers = []

for raw_line in INDEX_MD.read_text(encoding="utf-8").splitlines():
    line = raw_line.strip()
    if not line:
        continue

    # Look for DOI hyperlink
    match = doi_link_re.search(line)
    if not match:
        continue

    title = match.group(1).strip()
    doi = match.group(2).strip()

    # Everything before the title link is citation text
    citation_prefix = line[: match.start()]

    # Extract year (first plausible year before DOI)
    year_match = year_re.search(citation_prefix)
    year = int(year_match.group(0)) if year_match else None

    # Authors = text before the year
    if year_match:
        authors = citation_prefix[: year_match.start()].strip(" .,-")
    else:
        authors = citation_prefix.strip(" .,-")

    papers.append({
        "doi": doi,
        "year": year,
        "authors": authors,
        "title": title
    })

print(f"✅ Parsed {len(papers)} papers from index.md")

# Write YAML safely
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
