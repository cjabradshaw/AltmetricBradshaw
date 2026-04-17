# AltmetricBradshaw repository instructions

## Build, test, and lint commands

- Install the Python dependencies used by the scheduled build: `python3 -m pip install requests pyyaml`
- Rebuild the published page: `python3 build_publications.py`
- To refresh the Altmetric ranking from the API instead of preserving the current published order, run: `ALTMETRIC_API_KEY=... python3 build_publications.py`
- The scheduled GitHub Actions job in `.github/workflows/update-metrics.yml` runs the same build weekly and on manual dispatch. If `ALTMETRIC_API_KEY` is present, it refreshes ranking scores; otherwise it preserves the existing published order.
- There is no dedicated automated test suite, single-test command, or lint command in this repository right now.

## High-level architecture

- `papers.yaml` is the canonical publication dataset. The scheduled build reads from it directly.
- `build_publications.py` is the only script in the normal publishing path. It always refreshes Crossref citation counts, and it refreshes Altmetric scores only when `ALTMETRIC_API_KEY` is available. With a key, it sorts papers by Altmetric score descending; without a key, it preserves the existing DOI order from the committed `index.html`. It then injects the generated list into `index.template.html` at the `<!-- GENERATED CONTENT -->` placeholder to produce the committed `index.html`.
- `index.html` is a generated artifact that is committed to the repository and updated by the workflow.
- `index.md` and the helper scripts (`rebuild_papers_from_index_and_doi.py`, `generate_papers_from_index.py`, `extract_wordpress_icons_to_papers.py`, `normalize_papers_yaml.py`) are maintenance/migration utilities for rebuilding or normalizing data from older source material. They are not part of the scheduled update workflow.

## Key conventions

- Do not hand-edit generated publication rows in `index.html`; update `papers.yaml`, `index.template.html`, or the build script, then regenerate.
- Keep the `<!-- GENERATED CONTENT -->` marker in `index.template.html` unchanged. `build_publications.py` does a literal replacement on that exact string.
- Every `papers.yaml` entry is expected to include a DOI. Both Altmetric ranking and the embedded badges depend on it.
- Without `ALTMETRIC_API_KEY`, the build intentionally preserves the currently published order from `index.html` instead of reverting to raw `papers.yaml` order.
- Treat `papers_with_icons.yaml` and `papers_fixed.yaml` as derived helper outputs, not as inputs to the scheduled build.
