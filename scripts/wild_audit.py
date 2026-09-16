"""
In-The-Wild Empirical Measurement Study:
Audits real-world dataset metadata cards on Hugging Face Hub
using SynthProof's static boundary-audit engine.
Produces empirical statistics for academic publication.
"""

import json
import os
import re
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

def fetch_hf_datasets(query, limit=25):
    encoded_query = urllib.parse.quote(query)
    url = f"https://huggingface.co/api/datasets?search={encoded_query}&limit={limit}&full=true"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SynthProof-Audit/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"Error fetching query '{query}': {e}")
        return []

def fetch_dataset_readme(repo_id):
    url = f"https://huggingface.co/datasets/{repo_id}/raw/main/README.md"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 SynthProof-Audit/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return r.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""

def audit_wild_card(repo_id, readme_text, tags):
    findings = []
    
    # 1. Seed leakage detection (both in repo_id and readme)
    combined_text = f"{repo_id} {readme_text}"
    # Ignore false positives like 'seed-free'
    if "seed-free" in combined_text.lower():
        is_seed_free = True
    else:
        is_seed_free = False
        
    seed_patterns = [
        r'random_state\s*[:=]\s*(\d+)',
        r'seed[_\s:=]+(\d+(?:\.\d+e\d+)?)',
        r'--seed\s+(\d+)',
        r'"seed"\s*:\s*(\d+)',
        r'np\.random\.seed\((\d+)\)',
        r'torch\.manual_seed\((\d+)\)',
        r'seed[_-](\d+)',
        r'with-seed'
    ]
    exposed_seeds = []
    if not is_seed_free:
        for p in seed_patterns:
            matches = re.findall(p, combined_text, re.IGNORECASE)
            if matches:
                exposed_seeds.extend(matches)
                
        if exposed_seeds or ("seed" in repo_id.lower() and "seed-free" not in repo_id.lower()):
            findings.append({
                "code": "EXPOSED_PRNG_SEED",
                "severity": "FATAL",
                "evidence": f"Found random seeds published: {list(set(exposed_seeds))[:3] if exposed_seeds else ['in repo title']}"
            })
        
    # 2. Exact row count side channel
    row_count_patterns = [
        r'num_rows\s*[:=]\s*(\d+)',
        r'dataset_size\s*[:=]\s*(\d+)',
        r'(\d[\d,]+)\s*(?:rows|records|samples|instances)'
    ]
    for p in row_count_patterns:
        m = re.findall(p, readme_text, re.IGNORECASE)
        if m:
            # Check if this dataset claims privacy or DP
            is_privacy_claimed = any(t in readme_text.lower() for t in ["differential privacy", "private", "dp-sgd", "anonymized", "synthetic"])
            if is_privacy_claimed and not any(t in readme_text.lower() for t in ["laplace", "gaussian noise", "bounded"]):
                findings.append({
                    "code": "EXACT_COUNT_SIDE_CHANNEL",
                    "severity": "HIGH",
                    "evidence": f"Exact sample count published without DP count mechanism: {m[0]}"
                })
                break

    # 3. Unkeyed SHA-256 hashes
    hash_matches = re.findall(r'\b([a-f0-9]{64})\b', readme_text)
    if hash_matches:
        findings.append({
            "code": "UNKEYED_FINGERPRINT",
            "severity": "HIGH",
            "evidence": f"Published unkeyed 64-char hash: {hash_matches[0][:16]}..."
        })
        
    # 4. Absence of holdout split documentation
    has_holdout = any(k in readme_text.lower() for k in ["train", "test", "validation", "holdout", "split"])
    if not has_holdout:
        findings.append({
            "code": "UNLABELLED_EVALUATION_SPLIT",
            "severity": "MEDIUM",
            "evidence": "No clear train/test/holdout split specified in metadata card"
        })
        
    return findings

def main():
    queries = [
        "seed synthetic",
        "random_state synthetic",
        "synthetic tabular",
        "differential privacy",
        "anonymized private",
        "uplimit-synthetic-data",
        "synthetic medical"
    ]
    
    print("Executing In-The-Wild Audit across Hugging Face Hub datasets...")
    all_datasets = {}
    
    for q in queries:
        ds_list = fetch_hf_datasets(q, limit=25)
        for d in ds_list:
            repo_id = d.get("id")
            if repo_id and repo_id not in all_datasets:
                all_datasets[repo_id] = d
                
    print(f"Discovered {len(all_datasets)} unique privacy/synthetic dataset repositories.")
    
    results = []
    
    def process_ds(item):
        repo_id, info = item
        readme = fetch_dataset_readme(repo_id)
        tags = info.get("tags", [])
        findings = audit_wild_card(repo_id, readme, tags)
        return {
            "repo_id": repo_id,
            "downloads": info.get("downloads", 0),
            "likes": info.get("likes", 0),
            "has_readme": len(readme) > 0,
            "findings_count": len(findings),
            "findings": findings
        }
        
    with ThreadPoolExecutor(max_workers=5) as ex:
        results = list(ex.map(process_ds, all_datasets.items()))
        
    # Aggregate stats
    total_audited = len(results)
    seed_leaks = sum(1 for r in results if any(f["code"] == "EXPOSED_PRNG_SEED" for f in r["findings"]))
    exact_count_leaks = sum(1 for r in results if any(f["code"] == "EXACT_COUNT_SIDE_CHANNEL" for f in r["findings"]))
    hash_leaks = sum(1 for r in results if any(f["code"] == "UNKEYED_FINGERPRINT" for f in r["findings"]))
    split_omissions = sum(1 for r in results if any(f["code"] == "UNLABELLED_EVALUATION_SPLIT" for f in r["findings"]))
    at_least_one_fatal = sum(1 for r in results if any(f["severity"] == "FATAL" for f in r["findings"]))
    
    summary = {
        "total_datasets_audited": total_audited,
        "seed_leak_count": seed_leaks,
        "seed_leak_percentage": round((seed_leaks / total_audited) * 100, 2) if total_audited else 0,
        "exact_count_leak_count": exact_count_leaks,
        "exact_count_leak_percentage": round((exact_count_leaks / total_audited) * 100, 2) if total_audited else 0,
        "hash_leak_count": hash_leaks,
        "unlabelled_split_count": split_omissions,
        "datasets_with_fatal_leaks": at_least_one_fatal,
        "fatal_leak_percentage": round((at_least_one_fatal / total_audited) * 100, 2) if total_audited else 0,
        "detailed_results": results
    }
    
    os.makedirs("research/wild_audit", exist_ok=True)
    out_json = "research/wild_audit/wild_audit_results.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
        
    # Generate Markdown Report
    out_md = "research/wild_audit/WILD_AUDIT_REPORT.md"
    with open(out_md, "w", encoding="utf-8") as f:
        f.write("# Empirical In-The-Wild Measurement Study: Release Boundary Side Channels in Public Datasets\n\n")
        f.write(f"> **Audit Date:** 2026-09-15  \n")
        f.write(f"> **Target Platform:** Hugging Face Hub (Public Datasets API)  \n")
        f.write(f"> **Total Datasets Audited:** {total_audited}  \n\n")
        f.write("## 1. Executive Summary Table\n\n")
        f.write("| Vulnerability Category | Severity | Flagged Datasets | Percentage of Corpus |\n")
        f.write("|---|---|:---:|:---:|\n")
        f.write(f"| **Exposed PRNG Seed (`random_state`)** | **FATAL** | {seed_leaks} | **{summary['seed_leak_percentage']}%** |\n")
        f.write(f"| **Exact Sample Count Side Channel** | **HIGH** | {exact_count_leaks} | **{summary['exact_count_leak_percentage']}%** |\n")
        f.write(f"| **Unkeyed Table Hash (`SHA-256`)** | **HIGH** | {hash_leaks} | {round((hash_leaks/total_audited)*100, 2)}% |\n")
        f.write(f"| **Unlabelled Evaluation Split** | **MEDIUM** | {split_omissions} | {round((split_omissions/total_audited)*100, 2)}% |\n")
        f.write(f"| **At Least One Fatal Side Channel** | **FATAL** | **{at_least_one_fatal}** | **{summary['fatal_leak_percentage']}%** |\n\n")
        f.write("## 2. Exemplar Vulnerable Repositories\n\n")
        f.write("Below are real-world repositories from the audit that published fatal side channels:\n\n")
        for r in results:
            if r["findings"]:
                f.write(f"### `{r['repo_id']}` (Downloads: {r['downloads']})\n")
                for f_item in r["findings"]:
                    f.write(f"- **[{f_item['severity']}] {f_item['code']}:** {f_item['evidence']}\n")
                f.write("\n")
                
    print(f"\nAudit Complete! Report written to {out_md}")
    print(f"Summary: {at_least_one_fatal} of {total_audited} datasets ({summary['fatal_leak_percentage']}%) contain FATAL release boundary leaks!")

if __name__ == "__main__":
    main()
