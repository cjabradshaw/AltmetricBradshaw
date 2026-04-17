import re
import yaml
from pathlib import Path

INDEX_MD = Path("index.md")
PAPERS_YAML = Path("papers.yaml")
OUTPUT_YAML = Path("papers_with_icons.yaml")

# --- regex patterns ---
# WordPress images
wp_img = re.compile(
    r"(https://coreybradshaw\.files\.wordpress\.com/[^\s\)\"']+)",
    re.IGNORECASE
)

# DOI pattern (robust)
doi_re = re.compile(
    r"(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)"
)

# --- Step 1: Extract DOI → image mapping from index.md ---
doi_to_image = {}

current_image = None

for line in INDEX_MD.read_text(encoding="utf-8").splitlines():
    img_match = wp_img.search(line)
    if img_match:
        current_image = img_match.group(1)
        continue

    doi_match = doi_re.search(line)
    if doi_match and current_image:
        doi = doi_match.group(1)
        doi_to_image[doi] = current_image
        current_image = None

print(f"✅ Found {len(doi_to_image)} WordPress icon URLs")

# --- Step 2: Load papers.yaml ---
with PAPERS_YAML.open(encoding="utf-8") as f:
    papers = yaml.safe_load(f)

if not isinstance(papers, list):
    raise RuntimeError("papers.yaml must contain a list")

# --- Step 3: Merge icons into papers ---
for p in papers:
    doi = p.get("doi")
    if doi in doi_to_image:
        p["image"] = doi_to_image[doi]

# --- Step 4: Write merged dataset ---
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

print(f"✅ Wrote updated dataset to {OUTPUT_YAML.name}")
