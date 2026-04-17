import yaml
from pathlib import Path

INPUT = Path("papers.yaml")
OUTPUT = Path("papers_fixed.yaml")

# Load YAML (must be at least syntactically valid)
with INPUT.open("r", encoding="utf-8") as f:
    data = yaml.safe_load(f)

if not isinstance(data, list):
    raise ValueError("papers.yaml must contain a list of entries")

cleaned = []

for entry in data:
    year = entry.get("year")

    cleaned.append({
        "doi": str(entry.get("doi")),
        "year": int(year) if year is not None else None,
        "authors": str(entry.get("authors")),
        "title": str(entry.get("title")),
    })

# Write fully normalized YAML
with OUTPUT.open("w", encoding="utf-8") as f:
    yaml.safe_dump(
        cleaned,
        f,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=120,
        indent=2,
    )

print("✅ papers_fixed.yaml written successfully")
