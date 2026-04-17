# AltmetricBradshaw repository instructions

## Build, test, and lint commands

- Install the Python dependencies used by the scheduled build: `python3 -m pip install requests pyyaml`
- Rebuild the published page: `ALTMETRIC_API_KEY=... python3 build_publications.py`
- The scheduled GitHub Actions job in `.github/workflows/update-metrics.yml` runs the same build weekly and on manual dispatch, and now expects the repository secret `ALTMETRIC_API_KEY`.
- There is no dedicated automated test suite, single-test command, or lint command in this repository right now.

## High-level architecture

- `papers.yaml` is the canonical publication dataset. The scheduled build reads from it directly.
- `build_publications.py` is the only script in the normal publishing path. It fetches live Altmetric scores and Crossref citation counts for each DOI, sorts papers by Altmetric score descending, then injects the generated list into `index.template.html` at the `<!-- GENERATED CONTENT -->` placeholder to produce the committed `index.html`.
- `index.html` is a generated artifact that is committed to the repository and updated by the workflow.
- `index.md` and the helper scripts (`rebuild_papers_from_index_and_doi.py`, `generate_papers_from_index.py`, `extract_wordpress_icons_to_papers.py`, `normalize_papers_yaml.py`) are maintenance/migration utilities for rebuilding or normalizing data from older source material. They are not part of the scheduled update workflow.

## Key conventions

- Do not hand-edit generated publication rows in `index.html`; update `papers.yaml`, `index.template.html`, or the build script, then regenerate.
- Keep the `<!-- GENERATED CONTENT -->` marker in `index.template.html` unchanged. `build_publications.py` does a literal replacement on that exact string.
- Every `papers.yaml` entry is expected to include a DOI. Both Altmetric ranking and the embedded badges depend on it.
- Ranking correctness matters more than producing a stale page. The build should fail if Altmetric scores cannot be fetched with `ALTMETRIC_API_KEY`, rather than silently preserving input order.
- Treat `papers_with_icons.yaml` and `papers_fixed.yaml` as derived helper outputs, not as inputs to the scheduled build.
