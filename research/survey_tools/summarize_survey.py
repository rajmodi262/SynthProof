import json

data = json.load(open('research/raw_50_survey.json', encoding='utf-8'))

clusters = sorted(set(p['cluster'] for p in data))
with open('research/survey_summary.txt', 'w', encoding='utf-8') as out:
    for c in clusters:
        out.write(f"\n=======================================================\n")
        out.write(f"CLUSTER: {c}\n")
        out.write(f"=======================================================\n")
        c_papers = [p for p in data if p['cluster'] == c]
        for i, p in enumerate(c_papers, 1):
            doi_url = p.get('doi') or p.get('url')
            out.write(f"{i}. \"{p['title']}\" ({p.get('year')})\n")
            out.write(f"   Authors: {p['authors']}\n")
            out.write(f"   Venue: {p['venue']}\n")
            out.write(f"   Citations: {p['citations']}\n")
            out.write(f"   URL: {doi_url}\n")
            out.write(f"   Abstract: {p['abstract'][:180]}...\n\n")

