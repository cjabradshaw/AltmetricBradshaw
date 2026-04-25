import csv
import os
import re
from datetime import datetime, timezone
from html import escape, unescape
from pathlib import Path
import time
import yaml
import requests

PAPERS_FILE = Path("papers.yaml")
TEMPLATE_FILE = Path("index.template.html")
OUTPUT_FILE = Path("index.html")
CSV_OUTPUT_FILE = Path("publications.csv")
CONTENT_PLACEHOLDER = "<!-- GENERATED CONTENT -->"
META_PLACEHOLDER = "<!-- GENERATED META -->"
ALTMETRIC_API_KEY = os.environ.get("ALTMETRIC_API_KEY")
BRADSHAW_RE = re.compile(r"\bBradshaw\b", re.IGNORECASE)
MAX_DISPLAY_AUTHORS = 20
MASKED_AUTHORS = {"Cooper, A", "Fordham, DA"}
JOURNAL_ABBREVIATION_OVERRIDES = {
    "American Journal of Health Promotion": "Am J Health Promot",
    "Applied Energy": "Appl Energy",
    "Asia &amp; the Pacific Policy Studies": "Asia Pac Policy Stud",
    "Austral Ecology": "Austral Ecol",
    "Biological Conservation": "Biol Conserv",
    "Biological Reviews": "Biol Rev",
    "Conservation Biology": "Conserv Biol",
    "Conservation Letters": "Conserv Lett",
    "Conservation Science and Practice": "Conserv Sci Pract",
    "Current Biology": "Curr Biol",
    "Diversity and Distributions": "Divers Distrib",
    "Ecological Applications": "Ecol Appl",
    "Ecological Economics": "Ecol Econ",
    "Ecological Management &amp; Restoration": "Ecol Manag Restor",
    "Ecological Monographs": "Ecol Monogr",
    "Ecology and Evolution": "Ecol Evol",
    "Ecology Letters": "Ecol Lett",
    "Environmental Research": "Environ Res",
    "Environmental Research Letters": "Environ Res Lett",
    "Environmental Sciences Europe": "Environ Sci Eur",
    "Evolutionary Applications": "Evol Appl",
    "Fish and Fisheries": "Fish Fish",
    "Frontiers in Conservation Science": "Front Conserv Sci",
    "Frontiers in Ecology and the Environment": "Front Ecol Environ",
    "Frontiers in Public Health": "Front Public Health",
    "Geophysical Research Letters": "Geophys Res Lett",
    "Global and Planetary Change": "Glob Planet Change",
    "Global Change Biology": "Glob Change Biol",
    "Globalization and Health": "Globaliz Health",
    "ICES Journal of Marine Science": "ICES J Mar Sci",
    "Journal of Animal Ecology": "J Anim Ecol",
    "Journal of Applied Ecology": "J Appl Ecol",
    "Journal of Fish Biology": "J Fish Biol",
    "Journal of Mammalogy": "J Mammal",
    "Journal of Plant Ecology": "J Plant Ecol",
    "Marine Ecology Progress Series": "Mar Ecol Prog Ser",
    "Marine Pollution Bulletin": "Mar Pollut Bull",
    "Molecular Ecology": "Mol Ecol",
    "Nature Communications": "Nat Commun",
    "Nature Ecology &amp; Evolution": "Nat Ecol Evol",
    "Nature Genetics": "Nat Genet",
    "Nature Geoscience": "Nat Geosci",
    "Nature Human Behaviour": "Nat Hum Behav",
    "NeoBiota": "NeoBiota",
    "PLOS Computational Biology": "PLoS Comput Biol",
    "PLOS ONE": "PLoS One",
    "PLoS ONE": "PLoS One",
    "Palaeogeography, Palaeoclimatology, Palaeoecology": "Palaeogeogr Palaeoclimatol Palaeoecol",
    "Proceedings of the National Academy of Sciences": "Proc Natl Acad Sci USA",
    "Proceedings of the Royal Society B: Biological Sciences": "Proc R Soc B",
    "Quaternary Geochronology": "Quat Geochronol",
    "Quaternary International": "Quat Int",
    "Quaternary Science Reviews": "Quat Sci Rev",
    "Regional Studies in Marine Science": "Reg Stud Mar Sci",
    "Renewable and Sustainable Energy Reviews": "Renew Sustain Energy Rev",
    "River Research and Applications": "River Res Appl",
    "Royal Society Open Science": "R Soc Open Sci",
    "Science Advances": "Sci Adv",
    "Science of The Total Environment": "Sci Total Environ",
    "Scientific Data": "Sci Data",
    "Scientific Reports": "Sci Rep",
    "Transactions of the Royal Society of South Australia": "Trans R Soc S Aust",
    "Trends in Ecology &amp; Evolution": "Trends Ecol Evol",
    "AMBIO: A Journal of the Human Environment": "Ambio",
}


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


def sanitize_journal_name(name):
    return re.sub(r"\s+", " ", name.replace(".", "")).strip()


def normalized_journal_key(name):
    return sanitize_journal_name(name).replace("&amp;", "&").lower()


def abbreviate_journal_name(full_title, crossref_message):
    override = JOURNAL_ABBREVIATION_OVERRIDES.get(full_title)
    if override:
        return override

    for short_title in crossref_message.get("short-container-title", []):
        if short_title and normalized_journal_key(short_title) != normalized_journal_key(full_title):
            return sanitize_journal_name(short_title)

    return sanitize_journal_name(full_title)


def fetch_crossref_metadata(doi, journal):
    try:
        r = requests.get(f"https://api.crossref.org/works/{doi}", timeout=10)
        if r.ok:
            message = r.json()["message"]
            return {
                "citations": message.get("is-referenced-by-count", 0),
                "journal": abbreviate_journal_name(journal, message),
            }
    except Exception:
        pass
    return {
        "citations": 0,
        "journal": abbreviate_journal_name(journal, {}),
    }


def normalize_author_case(author):
    surname, separator, initials = author.partition(",")
    if not separator:
        return author.strip()

    surname = surname.strip()
    initials = initials.strip()

    if surname.isupper():
        surname = surname.title()

    if BRADSHAW_RE.fullmatch(surname):
        surname = "Bradshaw"
        initials = "CJA"

    return f"{surname}{separator} {initials}"


def normalize_authors(authors):
    return [
        normalize_author_case(author)
        for author in authors.split(";")
        if author.strip()
    ]


def should_truncate_authors(authors):
    if len(authors) <= MAX_DISPLAY_AUTHORS:
        return False

    for author in authors[MAX_DISPLAY_AUTHORS:]:
        if BRADSHAW_RE.search(author):
            return False

    return True


def format_authors(authors):
    normalized_authors = normalize_authors(authors)
    masked_authors = [
        "..." if author in MASKED_AUTHORS else author
        for author in normalized_authors
    ]

    truncated = should_truncate_authors(normalized_authors)
    visible_authors = masked_authors[:MAX_DISPLAY_AUTHORS] if truncated else masked_authors
    formatted = "; ".join(visible_authors)

    if truncated:
        formatted = f"{formatted}; et al."

    return BRADSHAW_RE.sub(
        lambda match: f"<strong>{match.group(0)}</strong>",
        formatted,
    )


def plain_text_authors(authors):
    normalized_authors = normalize_authors(authors)

    truncated = should_truncate_authors(normalized_authors)
    visible_authors = normalized_authors[:MAX_DISPLAY_AUTHORS] if truncated else normalized_authors
    formatted = "; ".join(visible_authors)

    if truncated:
        formatted = f"{formatted}; et al."

    return formatted


def write_csv(rows):
    with CSV_OUTPUT_FILE.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "rank",
                "doi",
                "year",
                "authors",
                "title",
                "journal",
                "citations",
                "altmetric_score",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


# -------------------------------
# Fetch metrics for all papers
# -------------------------------

for p in papers:
    doi = p.get("doi")
    if not doi:
        raise RuntimeError("Every paper entry must include a DOI")

    crossref = fetch_crossref_metadata(doi, p.get("journal", ""))
    p["citations"] = crossref["citations"]
    p["journal_abbrev"] = crossref["journal"]
    p["altmetric"] = None

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
    print("No ALTMETRIC_API_KEY set; using papers.yaml order.")

# -------------------------------
# Render HTML
# -------------------------------
items = []
csv_rows = []
last_updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

for rank, p in enumerate(papers, start=1):
    doi = p.get("doi", "")
    title = p.get("title", "")
    summary = p.get("summary", "").strip()
    raw_authors = p.get("authors", "")
    authors = format_authors(raw_authors)
    authors_plain = plain_text_authors(raw_authors)
    journal = p.get("journal_abbrev") or p.get("journal", "")
    year = p.get("year") or "n.d."
    image = p.get("image")
    alt = p.get("altmetric")
    cites = p.get("citations", 0)

    icon = f'<img src="{image}" class="paper-icon" alt="Journal icon">' if image else ""
    summary_html = f'      <div class="paper-summary"><em>{escape(summary)}</em></div>' if summary else ""

    items.append(
    f'<li class="paper">'
    f'  <div class="paper-row">'
    f'    <div class="citation">'
    f'      {authors} {year}. '
    f'      <a href="https://doi.org/{doi}">{title}</a>. '
    f'      <span class="journal"><em>{journal}</em></span>. '
    f'      doi:{doi}'
    f'      {summary_html}'
    f'    </div>'
    f'    <div class="paper-icon-container">{icon}</div>'
    f'  </div>'
    f'  <div class="metrics-row">'
    f'    <span class="altmetric-embed" '
    f'          data-badge-popover="right" '
    f'          data-badge-type="donut" '
    f'          data-doi="{doi}"></span>'
    f'    <span class="metrics">citations: {cites}</span>'
    f'  </div>'
    f'</li>'
    f'<hr>'
)

    csv_rows.append({
        "rank": rank,
        "doi": doi,
        "year": year,
        "authors": unescape(authors_plain),
        "title": unescape(title),
        "journal": unescape(journal),
        "citations": cites,
        "altmetric_score": "" if alt is None else alt,
    })

html = TEMPLATE_FILE.read_text(encoding="utf-8")

if CONTENT_PLACEHOLDER not in html:
    raise RuntimeError("Missing <!-- GENERATED CONTENT --> in index.template.html")

if META_PLACEHOLDER not in html:
    raise RuntimeError("Missing <!-- GENERATED META --> in index.template.html")

meta_html = (
    f'<div class="page-meta">'
    f'  <div class="last-updated">Last updated: {last_updated}</div>'
    f'  <a class="download-button" href="{CSV_OUTPUT_FILE.name}" download>download CSV</a>'
    f'</div>'
)

html = html.replace(META_PLACEHOLDER, meta_html)
html = html.replace(CONTENT_PLACEHOLDER, "\n\n".join(items))
OUTPUT_FILE.write_text(html, encoding="utf-8")
write_csv(csv_rows)

print(f"✅ index.html regenerated with {len(items)} papers")
