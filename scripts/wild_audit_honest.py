"""Honest in-the-wild measurement of release-boundary hygiene on the Hugging Face Hub.

WHY THIS REPLACES scripts/wild_audit.py. The first version flagged any dataset with the word
"seed" in its name as a FATAL differential-privacy breach. That is wrong twice over: (1) a published
seed only breaks privacy for a mechanism that is *actually* differentially private and whose noise
derives from that seed, and (2) 17 of its 22 "FATAL" hits were forks of ONE course-exercise dataset
(`uplimit-synthetic-data-week-1-with-seed`). Neither of those is a DP release. The "30% fatal leak
rate" measured the string "seed", not a privacy failure.

WHAT THIS MEASURES INSTEAD, honestly:
  1. The DP-release population on the Hub. Does a genuine corpus of differentially private data
     releases even exist here? (Preview: it essentially does not — that is itself a finding.)
  2. Seed-publication PREVALENCE among synthetic-data releases, DEDUPLICATED by base repo so eight
     forks of one tutorial count once. Framed honestly: this is the reproducibility practice that DP
     forbids, and measuring how normalized it is motivates the boundary-audit tool. It is NOT
     claimed as a set of DP breaches.
  3. For any dataset that DOES claim DP (states an epsilon), disclosure completeness in the sense of
     Dibia et al. (PoPETs 2026): is the epsilon even interpretable — is delta, the mechanism, and
     the NEIGHBOUR RELATION (add/remove vs replace) stated? An epsilon with no neighbour relation is
     ambiguous, which is the standard's whole point and our D2 finding.

LIMITATIONS, stated up front and repeated in the report:
  - Metadata/text only. We read repo ids, tags, and README cards; we do not download or inspect the
    data. DP detection is keyword-based and can miss or over-count.
  - Hugging Face is one hub. Government DP releases (US Census 2020 DAS), the NIST/SDNist challenge,
    and OpenDP/SmartNoise examples live elsewhere and are NOT covered here.
  - Prevalence of a published seed among non-DP synthetic data is NOT a privacy breach. We report it
    as "a norm DP forbids is widespread", never as a leak count.
"""

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

OUT_DIR = Path("research/wild_audit")
UA = {"User-Agent": "Mozilla/5.0 SynthProof-Research/1.0 (academic measurement)"}

# Broad synthetic-data queries plus DP-specific ones. HF `search` is literal, so we use single
# tokens that actually return hits.
QUERIES = [
    "synthetic",
    "synthetic-data",
    "synthetic tabular",
    "private",
    "anonymized",
    "differential",
    "privacy",
    "opendp",
    "smartnoise",
    "dp-sgd",
]

# A dataset "genuinely claims DP" only if it names an epsilon value or a DP mechanism -- not merely
# the words "private"/"synthetic", which are ambient.
DP_EPSILON = re.compile(r"(epsilon|ε)\s*[=:]?\s*\d|\bε\s*=|\d+\s*-?\s*differential", re.I)
DP_MECH = re.compile(
    r"differential(ly)? privat|dp-sgd|\bopendp\b|smartnoise|rényi dp|"
    r"gaussian mechanism|laplace mechanism",
    re.I,
)
NEIGHBOUR = re.compile(r"add[/ -]?remove|replace[- ]one|bounded|unbounded|neighbou?ring|unit of privacy", re.I)  # noqa: E501
DELTA = re.compile(r"delta\s*[=:]|δ\s*=|1e-\d", re.I)

SEED = re.compile(
    r"random_state\s*[=:]\s*\d|np\.random\.seed\s*\(\s*\d|torch\.manual_seed\s*\(\s*\d|"
    r"\bseed\s*[=:]\s*\d|--seed\s+\d|\bwith-seed\b|_seed_\d|-seed-\d",
    re.I,
)


def fetch_json(url):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"  [warn] {e} for {url[:80]}", file=sys.stderr)
        return None


def fetch_readme(repo_id):
    for branch in ("main", "master"):
        url = f"https://huggingface.co/datasets/{repo_id}/raw/{branch}/README.md"
        req = urllib.request.Request(url, headers=UA)
        try:
            with urllib.request.urlopen(req, timeout=12) as r:
                return r.read().decode("utf-8", errors="ignore")
        except Exception:
            continue
    return ""


def base_repo(repo_id: str) -> str:
    """Collapse forks/variants to one base key, so 8 copies of a tutorial count once.

    Strips the owner and trailing variant suffixes (-with-seed, _seed_N, -week-N, -evol, -vN, -N).
    """
    name = repo_id.split("/", 1)[-1].lower()
    name = re.sub(r"[-_](with[-_]?seed|seed[-_]?free|evol|v?\d+|week[-_]?\d+|seed[-_]?\d+(?:\.\d+e\d+)?)$", "", name)  # noqa: E501
    name = re.sub(r"[-_]?seed[-_]?\d*(?:\.\d+e\d+)?", "", name)
    return name or repo_id


def classify(repo_id, readme, tags):
    text = f"{repo_id}\n{readme}\n{' '.join(tags)}"
    claims_dp = bool(DP_MECH.search(text)) and bool(DP_EPSILON.search(text))
    mentions_dp = bool(DP_MECH.search(text))
    publishes_seed = bool(SEED.search(text))
    disclosure = {}
    if claims_dp:
        disclosure = {
            "states_epsilon": bool(DP_EPSILON.search(text)),
            "states_delta": bool(DELTA.search(text)),
            "states_neighbour_relation": bool(NEIGHBOUR.search(text)),
            "states_mechanism": bool(DP_MECH.search(text)),
        }
    return {
        "repo_id": repo_id,
        "base": base_repo(repo_id),
        "has_readme": bool(readme),
        "claims_dp_with_epsilon": claims_dp,
        "mentions_dp": mentions_dp,
        "publishes_seed": publishes_seed,
        "disclosure": disclosure,
    }


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    catalog = {}
    for query in QUERIES:
        url = f"https://huggingface.co/api/datasets?search={urllib.parse.quote(query)}&limit=60&full=true"
        res = fetch_json(url) or []
        print(f"query {query!r}: {len(res)} hits")
        for d in res:
            catalog.setdefault(d["id"], d)
        time.sleep(0.3)

    print(f"\nunique repos gathered: {len(catalog)}")
    records = []
    for i, (repo_id, meta) in enumerate(catalog.items(), 1):
        readme = fetch_readme(repo_id)
        tags = meta.get("tags", []) or []
        records.append(classify(repo_id, readme, tags))
        if i % 25 == 0:
            print(f"  audited {i}/{len(catalog)}")
        time.sleep(0.15)

    # ---- aggregate, DEDUPLICATED by base repo ----
    by_base = defaultdict(list)
    for r in records:
        by_base[r["base"]].append(r)
    unique_bases = list(by_base.values())

    def any_true(group, key):
        return any(r[key] for r in group)

    n_repos = len(records)
    n_bases = len(unique_bases)
    dp_repos = [r for r in records if r["claims_dp_with_epsilon"]]
    dp_bases = [g for g in unique_bases if any_true(g, "claims_dp_with_epsilon")]
    mentions_dp_bases = [g for g in unique_bases if any_true(g, "mentions_dp")]
    seed_bases = [g for g in unique_bases if any_true(g, "publishes_seed")]

    # Fork inflation illustration: the biggest duplicated base among seed publishers.
    fork_sizes = sorted(((len(g), g[0]["base"]) for g in unique_bases if any_true(g, "publishes_seed")), reverse=True)  # noqa: E501

    # Disclosure completeness among genuine DP-claiming repos.
    disc_keys = ["states_epsilon", "states_delta", "states_neighbour_relation", "states_mechanism"]
    disc_counts = {k: sum(1 for r in dp_repos if r["disclosure"].get(k)) for k in disc_keys}

    summary = {
        "corpus": {
            "queries": QUERIES,
            "repos_examined": n_repos,
            "unique_base_datasets_after_fork_dedup": n_bases,
        },
        "dp_population": {
            "base_datasets_mentioning_DP_mechanism": len(mentions_dp_bases),
            "base_datasets_claiming_DP_with_an_epsilon_value": len(dp_bases),
            "repos_claiming_DP_with_an_epsilon_value": len(dp_repos),
            "finding": "Hugging Face hosts essentially no genuine differentially private data "
            "releases; the DP-release ecosystem (Census DAS, NIST SDNist, OpenDP) is not here.",
        },
        "seed_publication_prevalence_NOT_breaches": {
            "unique_base_datasets_publishing_a_seed": len(seed_bases),
            "as_fraction_of_unique_bases": round(len(seed_bases) / max(1, n_bases), 4),
            "largest_fork_cluster_among_seed_publishers": fork_sizes[:5],
            "interpretation": "Publishing a seed is the reproducibility norm DP forbids. Among "
            "these NON-DP synthetic datasets it is not a privacy breach; it measures how "  # noqa: E501
            "normalized "
            "the risky practice is. Fork clusters are collapsed so one tutorial counts once.",
        },
        "dp_disclosure_completeness_among_DP_claimers": {
            "n_dp_claiming_repos": len(dp_repos),
            "counts": disc_counts,
            "note": "Of the (few) repos that state an epsilon, how many also state delta, the "
            "mechanism, and the NEIGHBOUR RELATION. An epsilon with no neighbour relation is "
            "ambiguous (Dibia et al. PoPETs 2026; our D2). Small n: report as case evidence, "
            "not a population statistic.",
        },
        "limitations": [
            "Metadata/text only; no data inspected. DP detection is keyword-based.",
            "Hugging Face only; government/challenge/OpenDP releases are elsewhere.",
            "Seed prevalence among non-DP data is a norm measurement, not a breach count.",
        ],
    }

    (OUT_DIR / "honest_audit_results.json").write_text(
        json.dumps({"summary": summary, "records": records}, indent=2), encoding="utf-8"
    )
    print("\n" + "=" * 78)
    print(json.dumps(summary, indent=2))
    print("=" * 78)
    print(f"wrote {OUT_DIR/'honest_audit_results.json'}")


if __name__ == "__main__":
    main()
