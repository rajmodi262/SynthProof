"""Exhaustive literature survey script across 7 research clusters using OpenAlex API.
Fetches verified bibliographic data (Title, Authors, Year, Venue, DOI/URL, Abstract, Citation Count).
"""

import json
import time
import urllib.request
import urllib.parse
from pathlib import Path

CLUSTERS = {
    "C1_tabular_synthesis": [
        "differential privacy synthetic tabular data",
        "AIM adaptive marginals differential privacy",
        "PrivBayes private data release",
        "PATE-GAN Generating Synthetic Data",
        "Private-PGM graphical models differential privacy",
        "diffusion models differential privacy tabular"
    ],
    "C2_empirical_auditing": [
        "auditing differential privacy lower bounds",
        "empirical privacy audit canary",
        "grey box auditing differential privacy libraries",
        "DP-Auditorium automated auditing",
        "membership inference lower bound Steinke"
    ],
    "C3_privacy_labels_metadata": [
        "differential privacy label Dibia",
        "Croissant machine learning datasets metadata",
        "Datasheets for Datasets Gebru",
        "Model Cards for Model Reporting Mitchell",
        "privacy nutrition label data"
    ],
    "C4_verifiable_dp_cryptography": [
        "verifiable differential privacy zero knowledge",
        "proof carrying differential privacy",
        "trusted execution environment differential privacy",
        "PrivateKube privacy budget ledger",
        "Laminator attested property cards"
    ],
    "C5_attacks_reconstruction": [
        "membership inference attacks synthetic data Stadler",
        "reconstruction attacks differential privacy synthetic data",
        "DOMIAS density based membership inference synthetic data",
        "membership inference risk synthetic data Annamalai"
    ],
    "C6_sdc_disclosure_gating": [
        "Statistical Analysis Output Checker Research Outputs SACRO",
        "Statistical Disclosure Control synthetic data",
        "Five Safes trusted research environment",
        "limit of detection analytical chemistry MIQE"
    ],
    "C7_release_boundary_randomness": [
        "differential privacy imperfect randomness Dodis",
        "On Significance Least Significant Bits Mironov",
        "differential privacy pseudo random generator",
        "LinkedIn Audience Engagements API differential privacy"
    ]
}

def fetch_openalex_papers():
    seen_titles = set()
    seen_dois = set()
    collected = []

    for cluster_name, queries in CLUSTERS.items():
        print(f"--- Querying Cluster: {cluster_name} ---")
        for q in queries:
            encoded_q = urllib.parse.quote(q)
            url = f"https://api.openalex.org/works?search={encoded_q}&per_page=4&sort=relevance_score:desc&mailto=research@synthproof.org"
            req = urllib.request.Request(url, headers={"User-Agent": "SynthProofSurvey/1.0 (mailto:research@synthproof.org)"})
            try:
                with urllib.request.urlopen(req, timeout=12) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    results = data.get("results", [])
                    for item in results:
                        title = item.get("title")
                        if not title:
                            continue
                        norm_title = title.lower().strip()
                        doi = item.get("doi") or item.get("id")
                        if norm_title in seen_titles or doi in seen_dois:
                            continue
                        seen_titles.add(norm_title)
                        if doi:
                            seen_dois.add(doi)

                        # Extract authors
                        authorships = item.get("authorships", [])
                        author_names = [a.get("author", {}).get("display_name") for a in authorships if a.get("author", {}).get("display_name")]
                        if len(author_names) > 3:
                            author_str = f"{author_names[0]}, {author_names[1]}, {author_names[2]} et al."
                        elif author_names:
                            author_str = ", ".join(author_names)
                        else:
                            author_str = "Unknown"

                        # Extract venue
                        primary_location = item.get("primary_location") or {}
                        source = primary_location.get("source") or {}
                        venue = source.get("display_name") or primary_location.get("landing_page_url") or "Preprint / Archive"

                        # Extract abstract
                        abstract = ""
                        inv_index = item.get("abstract_inverted_index")
                        if inv_index:
                            word_positions = []
                            for word, positions in inv_index.items():
                                for pos in positions:
                                    word_positions.append((pos, word))
                            word_positions.sort()
                            abstract = " ".join(w for _, w in word_positions[:80]) + "..."

                        collected.append({
                            "cluster": cluster_name,
                            "title": title,
                            "authors": author_str,
                            "year": item.get("publication_year"),
                            "venue": venue,
                            "doi": item.get("doi"),
                            "url": item.get("doi") or primary_location.get("landing_page_url") or item.get("id"),
                            "citations": item.get("cited_by_count", 0),
                            "abstract": abstract,
                            "open_access": item.get("open_access", {}).get("is_oa", False),
                            "oa_url": item.get("open_access", {}).get("oa_url")
                        })
                time.sleep(0.2)
            except Exception as e:
                print(f"Error querying '{q}': {e}")
                time.sleep(0.5)

    print(f"Total unique papers collected: {len(collected)}")
    out_path = Path("research/raw_50_survey.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(collected, indent=2), encoding="utf-8")
    print(f"Saved to {out_path}")

if __name__ == "__main__":
    fetch_openalex_papers()
