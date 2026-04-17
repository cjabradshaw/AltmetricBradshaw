import yaml
from pathlib import Path

INPUT = Path("papers.yaml")
OUTPUT = Path("papers_fixed.yaml")

with INPUT.open("r", encoding="utf-8") as f:
    data = yaml.safe_load(f)

# Basic sanity check
if not isinstance(data, list):
    raise ValueError("papers.yaml must be a list of entries")

# Ensure consistent structure
cleaned = []
for entry in data:
    cleaned.append({
        "doi": str(entry["doi"]),
        "year": int(entry["year"]),
        "authors": str(entry["authors"]),
        "title": str(entry["title"]),
    })

# Write fully-safe YAML
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
