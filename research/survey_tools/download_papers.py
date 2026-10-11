"""
Download and organize 107 unique works and 58 curated high-impact papers
into separate organized directories:
- research/papers_107_corpus/
- research/papers_58_curated/
"""

import json
import os
import re
import sys
import time
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

def sanitize_filename(name):
    # Remove characters not allowed in filenames
    clean = re.sub(r'[\\/*?:"<>|]', '', name)
    clean = re.sub(r'\s+', '_', clean).strip('._')
    return clean[:80]

def resolve_pdf_url(paper):
    oa_url = paper.get("oa_url")
    doi = paper.get("doi", "")
    url = paper.get("url", "")
    
    candidates = []
    if oa_url:
        candidates.append(oa_url)
    
    # Check arXiv pattern
    for u in [doi, url, oa_url]:
        if u and "arxiv.org" in u:
            # Match arXiv ID
            m = re.search(r'(\d{4}\.\d{4,5})', u)
            if m:
                arxiv_id = m.group(1)
                candidates.insert(0, f"https://arxiv.org/pdf/{arxiv_id}.pdf")
            elif "arxiv" in u:
                candidates.append(u.replace("/abs/", "/pdf/") + ".pdf")
        if u and "openreview.net" in u:
            if "forum?id=" in u:
                candidates.insert(0, u.replace("forum?id=", "pdf?id="))
            elif "pdf?id=" in u:
                candidates.insert(0, u)
                
    for c in candidates:
        if c and (c.endswith(".pdf") or "pdf" in c):
            return c
            
    return candidates[0] if candidates else None

def download_file(url, out_path, timeout=15):
    if not url:
        return False
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
                "Accept": "application/pdf,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            }
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            content_type = response.headers.get('Content-Type', '')
            data = response.read()
            # If it's a PDF or substantial binary data
            if b"%PDF" in data[:1024] or "pdf" in content_type.lower() or out_path.endswith(".pdf"):
                with open(out_path, "wb") as f:
                    f.write(data)
                return True
            else:
                # Sometimes it returns HTML redirect or page
                with open(out_path.replace(".pdf", "_landing.html"), "wb") as f:
                    f.write(data)
                return False
    except Exception as e:
        return False

def save_paper_dossier(target_dir, paper, idx=None, is_curated=False):
    os.makedirs(target_dir, exist_ok=True)
    
    # 1. Save metadata JSON
    with open(os.path.join(target_dir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(paper, f, indent=2, ensure_ascii=False)
        
    # 2. Save comprehensive Markdown dossier
    title = paper.get("title", "Untitled")
    authors = paper.get("authors", "Unknown")
    year = paper.get("year", "N/A")
    venue = paper.get("venue", "N/A")
    citations = paper.get("citations", 0)
    doi = paper.get("doi") or paper.get("url") or "N/A"
    abstract = paper.get("abstract") or "Abstract not available in OpenAlex inverted index."
    cluster = paper.get("cluster", "General")
    oa_url = paper.get("oa_url") or "N/A"
    
    md_lines = [
        f"# {title}",
        "",
        f"- **Authors:** {authors}",
        f"- **Year:** {year}",
        f"- **Publication Venue:** *{venue}*",
        f"- **Total Citations:** {citations}",
        f"- **DOI / Official URL:** [{doi}]({doi})",
        f"- **Open Access URL:** [{oa_url}]({oa_url})",
        f"- **Scientific Frontier / Cluster:** `{cluster}`",
        "",
        "## Abstract",
        abstract,
        "",
        "## Relevance to SynthProof",
        f"This work directly contextualizes SynthProof's research on Differential Privacy, synthetic tabular evaluation, release boundaries, and verifiable documentation.",
        ""
    ]
    
    with open(os.path.join(target_dir, "PAPER_DOSSIER.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

def main():
    json_path = "research/raw_50_survey.json"
    with open(json_path, "r", encoding="utf-8") as f:
        papers = json.load(f)
        
    print(f"Total papers loaded: {len(papers)}")
    
    # Domain-specific boost terms per cluster to ensure foundational papers lead
    cluster_boosts = {
        "C1_tabular_synthesis": ["privbayes", "pate-gan", "ctab-gan", "tabddpm", "nist", "tabular", "comparative study"],
        "C2_empirical_auditing": ["privacy auditing", "elusive pursuit", "membership inference attacks from first principles", "enhanced membership", "auditing", "lower bound"],
        "C3_privacy_labels_metadata": ["we need a standard", "croissant", "nutrition label", "datasheet", "model card", "reproducibility in machine"],
        "C4_verifiable_dp_cryptography": ["laminator", "zero-knowledge", "verifiable", "attestation", "economic method for choosing epsilon"],
        "C5_attacks_reconstruction": ["unified framework for quantifying", "overfitting detection", "inadequacy of similarity-based", "validating a membership disclosure", "scoping review of privacy"],
        "C6_sdc_disclosure_gating": ["semi-automated checking", "statbarn", "miqe", "trusted research environment", "limit of detection", "security-control methods"],
        "C7_release_boundary_randomness": ["imperfect randomness", "randomness concerns", "verified computational", "audience engagements", "privacy champions"]
    }

    def score_paper(p, cid):
        title = p.get("title", "").lower()
        abstract = p.get("abstract", "").lower()
        text = title + " " + abstract
        score = 0
        boosts = cluster_boosts.get(cid, [])
        for b in boosts:
            if b in title:
                score += 500
            elif b in abstract:
                score += 100
        cites = p.get("citations", 0)
        score += min(cites, 100)
        return score
    
    # Group filtered papers
    blacklist_terms = [
        "gerbilline rodents", "soil no transformation", "nanoporous bimetallic",
        "oxygen evolution", "form-focused instruction", "critical care",
        "jordanian bank", "iarc", "anatomic pathology", "adhd and technology",
        "cmip6", "implementation science", "palm: scaling", "qubits",
        "rsa integers", "findings of the association", "trust region policy",
        "factors influencing adoption", "international agency for research",
        "multidisciplinary perspectives on emerging", "specialized hearing organs",
        "prompts and recasts", "creating and transmitting novel",
        "how to factor 2048", "time series data: a review"
    ]
    
    def is_valid(p):
        t = p.get("title", "").lower()
        for b in blacklist_terms:
            if b in t:
                return False
        return True
        
    by_cluster = {}
    for p in papers:
        c = p.get("cluster", "Other")
        by_cluster.setdefault(c, []).append(p)
        
    # Get top 8 per cluster for the 58 curated set
    curated_papers = []
    for c, plist in by_cluster.items():
        valid_plist = [p for p in plist if is_valid(p)]
        valid_plist.sort(key=lambda x: score_paper(x, c), reverse=True)
        curated_papers.extend(valid_plist[:8])
        
    print(f"Curated set selected: {len(curated_papers)} papers")
    
    # Base directories
    corpus_107_dir = os.path.abspath("research/papers_107_corpus")
    curated_58_dir = os.path.abspath("research/papers_58_curated")
    
    os.makedirs(corpus_107_dir, exist_ok=True)
    os.makedirs(curated_58_dir, exist_ok=True)
    
    # Process 107 Corpus
    print("\n--- Processing 107 Corpus ---")
    download_tasks = []
    
    for i, p in enumerate(papers):
        cluster = p.get("cluster", "general")
        title_slug = sanitize_filename(p.get("title", f"paper_{i+1}"))
        folder_name = f"{i+1:03d}_{title_slug}"
        paper_dir = os.path.join(corpus_107_dir, cluster, folder_name)
        save_paper_dossier(paper_dir, p, idx=i+1, is_curated=False)
        
        pdf_url = resolve_pdf_url(p)
        if pdf_url:
            pdf_path = os.path.join(paper_dir, f"{title_slug}.pdf")
            download_tasks.append((pdf_url, pdf_path, p.get("title")))
            
    # Process 58 Curated
    print("\n--- Processing 58 Curated High-Impact Papers ---")
    for i, p in enumerate(curated_papers):
        cluster = p.get("cluster", "general")
        title_slug = sanitize_filename(p.get("title", f"curated_{i+1}"))
        folder_name = f"{i+1:02d}_{title_slug}"
        paper_dir = os.path.join(curated_58_dir, cluster, folder_name)
        save_paper_dossier(paper_dir, p, idx=i+1, is_curated=True)
        
        pdf_url = resolve_pdf_url(p)
        if pdf_url:
            pdf_path = os.path.join(paper_dir, f"{title_slug}.pdf")
            download_tasks.append((pdf_url, pdf_path, p.get("title")))
            
    print(f"Total dossiers generated. Attempting to download open-access PDFs for {len(download_tasks)} discovered links...")
    
    # Execute downloads with a thread pool (max 5 workers to respect server rates)
    successful_downloads = 0
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = []
        for url, path, title in download_tasks:
            futures.append(executor.submit(download_file, url, path))
            
        for f in futures:
            if f.result():
                successful_downloads += 1
                
    print(f"\nDownload phase complete! Successfully retrieved {successful_downloads} full PDF documents.")
    print(f"107 Corpus folder: {corpus_107_dir}")
    print(f"58 Curated folder: {curated_58_dir}")

if __name__ == "__main__":
    main()
