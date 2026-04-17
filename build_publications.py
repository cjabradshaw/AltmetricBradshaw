import yaml, requests, time

with open("papers.yaml") as f:
    papers = yaml.safe_load(f)

def altmetric(doi):
    r = requests.get(f"https://api.altmetric.com/v1/doi/{doi}")
    return r.json().get("score", 0) if r.ok else 0

def citations(doi):
    r = requests.get(f"https://api.crossref.org/works/{doi}")
    return r.json()["message"].get("is-referenced-by-count", 0) if r.ok else 0

for p in papers:
    p["altmetric"] = altmetric(p["doi"])
    p["citations"] = citations(p["doi"])
    time.sleep(1)   # be courteous

papers.sort(key=lambda x: x["altmetric"], reverse=True)

with open("index.html", "w") as out:
    for p in papers:
        out.write(
          f"""<li data-altmetric="{p['altmetric']}"
                  data-citations="{p['citations']}"
                  data-year="{p['year']}">
          {p['authors']} ({p['year']}).
          https://doi.org/{p['doi']}{p['title']}</a>
          <span class="altmetric-embed" data-doi="{p['doi']}"></span>
          </li>\n"""
        )
