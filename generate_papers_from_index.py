import re
import yaml
from pathlib import Path

INDEX = Path("index.md")
OUTPUT = Path("papers.yaml")

papers = []

doi_re = re.compile(r"(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)")
year_re = re.compile(r"\b(19|20)\d{2}\b")

for line in INDEX.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line:
        continue

    doi_match = doi_re.search(line)
    if not doi_match:
        continue

    doi = doi_match.group(1)
    year_match = year_re.search(line)
    year = int(year_match.group(0)) if year_match else None

    # crude but safe splits
    parts = line.split(". ", 2)
    authors = parts[0] if len(parts) > 0 else "Unknown"
    title = parts[1] if len(parts) > 1 else "Untitled"

    papers.append({
        "doi": doi,
        "year": year,
        "authors": authors,
        "title": title,
    })

with OUTPUT.open("w", encoding="utf-8") as f:
    yaml.safe_dump(
        papers,
        f,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        indent=2,
        width=120,
    )

print(f"✅ Wrote {len(papers)} papers to papers.yaml")
