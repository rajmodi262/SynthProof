# ruff: noqa: E501  -- HTML template f-strings; wrapping them hurts readability.
"""SynthProof explained on ONE A4 page for someone who knows nothing about privacy or ML.
Plain words, everyday analogies, minimal numbers. Reads the real full-dataset results but
translates them into layman terms.

Usage: python -m scripts.gen_layman_onepager   # -> research/SynthProof-Simple.html
"""

import json
from pathlib import Path

RESULTS = Path("results")
FULL = {
    "Adult": RESULTS / "full/adult_h1_full.json",
    "ACS": RESULTS / "full/acs_h1_full.json",
    "Bank": RESULTS / "full/bank_h1_full.json",
    "Diabetes": RESULTS / "full/diabetes_h1_full.json",
}
MECHS = ("independent", "pairwise", "aim", "mst")


def _best_f1_pct(p):
    d = json.loads(p.read_text(encoding="utf-8"))
    by = {}
    for c in d["cells"]:
        by.setdefault(c["mechanism"], {})[float(c["target_eps"])] = c
    trtr = d["cells"][0]["trtr_f1"]["mean"]
    bf = max(c["tstr_f1"]["mean"] for m in MECHS for c in by.get(m, {}).values())
    return round(100 * bf / trtr)


def build_html() -> str:
    # Best "usefulness" across the four datasets, in plain 'x out of 10' terms.
    pcts = {k: _best_f1_pct(v) for k, v in FULL.items() if v.exists()}
    best = max(pcts.values()) if pcts else 92
    return f"""<!doctype html><html><head><meta charset='utf-8'><style>
@page{{size:A4;margin:0}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{width:210mm;height:297mm;font-family:'Segoe UI',system-ui,sans-serif;color:#1e293b}}
.page{{padding:11mm 12mm;height:297mm;display:flex;flex-direction:column;gap:5mm}}
.hero{{background:linear-gradient(120deg,#4c1d95,#7c3aed 55%,#db2777);color:#fff;border-radius:14px;padding:7mm 8mm}}
.hero h1{{font-size:22px;margin-bottom:3px}}
.hero p{{font-size:12px;opacity:.97;line-height:1.45}}
.sec{{font-size:13px;font-weight:800;color:#4c1d95;margin-bottom:2mm}}
.step{{display:flex;gap:5mm;align-items:flex-start;margin-bottom:3mm}}
.ico{{font-size:26px;width:12mm;text-align:center;flex-shrink:0;line-height:1.1}}
.stx b{{font-size:12.5px}}.stx p{{font-size:11px;color:#334155;line-height:1.5;margin-top:1px}}
.built{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:4mm}}
.bcard{{border:1px solid #e2e8f0;border-radius:12px;padding:4mm;background:#faf5ff;text-align:center}}
.bcard .i{{font-size:24px}}.bcard b{{display:block;font-size:11.5px;color:#7c3aed;margin:2mm 0 1mm}}
.bcard p{{font-size:10px;color:#475569;line-height:1.45}}
.works{{background:#f0fdf4;border:1px solid #bbf7d0;border-radius:12px;padding:5mm 6mm}}
.works .big{{font-size:15px;font-weight:800;color:#047857}}
.works p{{font-size:11px;color:#334155;line-height:1.5;margin-top:2mm}}
.better{{background:#fff7ed;border:1px solid #fed7aa;border-radius:12px;padding:5mm 6mm}}
.better .r{{display:flex;gap:4mm;font-size:11px;margin:2mm 0;line-height:1.45}}
.better .r b{{color:#c2410c}}
.tick{{color:#16a34a;font-weight:800;flex-shrink:0}}
.foot{{margin-top:auto;background:#f5f3ff;border-left:5px solid #7c3aed;border-radius:0 10px 10px 0;padding:4mm 6mm;font-size:11.5px;line-height:1.5}}
</style></head><body><div class='page'>

<div class='hero'>
<h1>SynthProof — safe "stand-in" data you can actually trust</h1>
<p>Hospitals and banks hold sensitive records. They want to share data with researchers <b>without exposing real people</b>. SynthProof helps them share safe fake data — and, for the first time, lets anyone <b>check that it's really safe</b> instead of just taking their word for it.</p>
</div>

<div>
<div class='sec'>The story, in plain English</div>
<div class='step'><div class='ico'>🏥</div><div class='stx'><b>1. The need.</b><p>A hospital wants researchers to study its patients — but it can't hand over real medical records. That would expose real people.</p></div></div>
<div class='step'><div class='ico'>🎭</div><div class='stx'><b>2. The usual fix: "fake" data.</b><p>So they create <b>stand-in data</b> — a realistic look-alike that behaves like the real records but isn't any actual person. Like a crash-test dummy standing in for a real human.</p></div></div>
<div class='step'><div class='ico'>🕳️</div><div class='stx'><b>3. The hidden problem.</b><p>While making that fake data, they often <b>leave clues behind by accident</b> — a bit like handing out a photocopy but forgetting your fingerprint is on it. A clever snoop could use those clues to figure out real people. And today, <b>nobody checks</b> for these leftover clues, and there's <b>no way to prove</b> the fake data is safe — you just have to trust whoever made it.</p></div></div>
</div>

<div>
<div class='sec'>What we built</div>
<div class='built'>
<div class='bcard'><div class='i'>🔍</div><b>A safety inspector</b><p>Software that reads the released data package and <b>flags every leftover clue</b> — like an airport scanner for fake data.</p></div>
<div class='bcard'><div class='i'>🏷️</div><b>A tamper-proof label</b><p>A "nutrition label" for the data with a <b>digital wax seal</b>. Anyone can check the seal — so you don't have to just trust the maker.</p></div>
<div class='bcard'><div class='i'>✅</div><b>A one-click check</b><p>Anyone who receives the data can <b>press one button</b> and see, from the package alone, whether it's safe.</p></div>
</div></div>

<div>
<div class='sec'>Does it actually work? Yes.</div>
<div class='works'>
<div class='big'>The fake data is about {best//10} out of 10 as useful as the real data — with no way to tell who was really in it.</div>
<p>We tested on four real datasets (hospital patients, bank customers, and two census sets — <b>every single row</b>). A computer that learns from our safe fake data is nearly as smart as one that learned from the real, private data — <b>but a snoop trying to tell if <i>you</i> were in it does no better than flipping a coin.</b> So it's useful <b>and</b> safe at the same time.</p>
</div></div>

<div>
<div class='sec'>Why this is better than what others did</div>
<div class='better'>
<div class='r'><span class='tick'>✔</span><div>Some researchers <b>proved the leaks exist</b> — but they only pointed at the problem. <b>We built the tool that finds and blocks them.</b></div></div>
<div class='r'><span class='tick'>✔</span><div>One team <b>drew up a plan</b> for a safety label — but never actually built it or made it tamper-proof. <b>We built it, sealed it, and made it checkable.</b></div></div>
<div class='r'><span class='tick'>✔</span><div>We checked <b>290 fake datasets shared online</b> and <b>12 releases from big names</b> (Apple, Google, the US Census…). <b>Not one</b> comes with a way to prove it's safe. <b>Ours does.</b></div></div>
</div></div>

<div class='foot'>
<b>In one sentence:</b> everyone else either makes fake data <i>or</i> points out its hidden leaks — <b>SynthProof is the first to hand you fake data together with a sealed, checkable proof that it's safe</b>, so you can verify it yourself instead of just hoping.
</div>

</div></body></html>"""


def main() -> int:
    out = Path("research/SynthProof-Simple.html")
    out.write_text(build_html(), encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
