# -*- coding: utf-8 -*-
"""Generate a colourful literature-survey PDF report (HTML -> Edge print)."""
import math, html, os

OUT_HTML = r"D:\03_Study\CAPSTONE\SynthProof\research\Literature-Survey-Report.html"

# ---- palette ----
CAT = {
 "attack":   ("#E5484D", "Attacks"),
 "audit":    ("#F5A623", "Mechanism audits"),
 "preproc":  ("#C98A2B", "Preprocessing audits"),
 "mech":     ("#3E7BFA", "Generative mechanisms"),
 "deploy":   ("#12B5A5", "Real deployment"),
 "human":    ("#7C3AED", "Standards & human factors"),
}
INK="#191627"; MUT="#5b5670"; PAPERBG="#FBF7F0"; CARD="#ffffff"
GREEN="#2FA36B"; CORAL="#E5484D"

# ---- the 11 papers (all verified) ----
P = [
 dict(id="P1", auth="Stadler, Oprisanu & Troncoso", short="Stadler et al.",
      title="Synthetic Data — Anonymisation Groundhog Day", year=2022, venue="USENIX Security",
      cat="attack", pages=19, data=["Adult","Texas"],
      did="First quantitative proof that synthetic data leaks membership for outlier records; open-source attack framework.",
      gap="No signed or checkable release artifact; the DP fix needs a public dataset most curators lack.",
      fill="A data-blind linter + signed sheet that flags the very leak (domain/seed) they found."),
 dict(id="P2", auth="Annamalai, Ganev & De Cristofaro", short="Annamalai et al.",
      title="\u201cWhat do you want from theory alone?\u201d Tight Auditing of DP-SDG", year=2024, venue="USENIX Security",
      cat="audit", pages=17, data=["Adult","SF Fire"],
      did="Tight empirical auditing of 6 DP synthesizers; black-box MIAs read \u03b5\u22480 even at true \u03b5=4.",
      gap="Audits the mechanism \u2014 needs code, model internals & worst-case data; not the shipped document.",
      fill="Grounds our audit ceiling; explains why our audited \u03b5=0.000 is loose, not \u2018safe\u2019."),
 dict(id="P3", auth="Cebere, Erb, Desfontaines, Bellet & Fitzsimons", short="Cebere et al.",
      title="Privacy in Theory, Bugs in Practice: Grey-Box Auditing of DP Libraries", year=2026, venue="PoPETs",
      cat="audit", pages=17, data=["\u2014"],
      did="\u2018Re:cord-play\u2019 grey-box audit: 13 privacy violations across 12 DP libraries.",
      gap="Audits library code, not the released artifact/document.",
      fill="Same \u2018neighbours + identical randomness\u2019 trick as our seed-replay; motivates our 2nd accountant."),
 dict(id="P4", auth="Ganev, Annamalai, Mahiou & De Cristofaro", short="Ganev et al.",
      title="Understanding the Impact of Data Domain Extraction on Synthetic-Data Privacy", year=2025, venue="ICLR SynthData",
      cat="preproc", pages=7, data=["Wine"],
      did="Reading the data domain from the input breaks end-to-end DP \u2192 MIA AUC \u2248 1.0.",
      gap="No artifact field records the domain's provenance so a validator could check it.",
      fill="External proof of our D1 / domain-source rule; boundary-audit flags data-derived domains."),
 dict(id="P5", auth="Ganev, Annamalai, Mahiou & De Cristofaro", short="Ganev et al.",
      title="The Importance of Being Discrete: Discretization in End-to-End DP", year=2025, venue="ACM CCS",
      cat="preproc", pages=15, data=["Adult","Gas","Wine"],
      did="Discretization strongly affects utility (+9\u201344%) and DP; DP domain drops MIA 100%\u219250%.",
      gap="Audits discretization; ships no checkable release.",
      fill="With P4/P6 maps the preprocessing subfield \u2014 missing-data handling is the slot we fill."),
 dict(id="P6", auth="Ganev, Nazari, Davison \u2026 De Cristofaro", short="Ganev et al.",
      title="SMOTE and Mirrors: Privacy Leakage from Synthetic Minority Oversampling", year=2026, venue="ICLR",
      cat="attack", pages=18, data=["8 imbalanced","cardio","creditcard","higgs"],
      did="SMOTE is inherently non-private; ReconSMOTE reconstructs minority records (precision 1.0).",
      gap="Naive metrics (DCR) miss it; no audit of missing-data handling; no artifact check.",
      fill="Validates our sanity-gate design; our kNN imputation arm is the SMOTE-like risk we test."),
 dict(id="P7", auth="Mohapatra, Zong, Kerschbaum & He", short="Mohapatra et al.",
      title="Differentially Private Data Generation with Missing Data", year=2024, venue="VLDB",
      cat="mech", pages=18, data=["Adult","Bank","BR2000","National"],
      did="First to study DP synthesis with missing data; imputation is n\u03b5-expensive; missingness amplifies privacy.",
      gap="Never audits whether the missing-data handling leaks membership.",
      fill="THE base for our imputation audit \u2014 we run the membership check they leave open."),
 dict(id="P8", auth="McKenna, Mullins, Sheldon & Miklau", short="McKenna et al.",
      title="AIM: An Adaptive and Iterative Mechanism for DP Synthetic Data", year=2022, venue="VLDB",
      cat="mech", pages=23, data=["Adult","salary","msnbc","fire","nltcs","titanic"],
      did="State-of-the-art marginal synthesizer (up to 118\u00d7 lower workload error than MST).",
      gap="Ships a model, not a signed/boundary-checked release; reads the domain from data.",
      fill="The generator we USE; our D1 fix corrects its uncharged use of the private row count."),
 dict(id="P9", auth="Abowd et al. (U.S. Census Bureau)", short="Abowd et al.",
      title="The 2020 Census Disclosure Avoidance System TopDown Algorithm", year=2022, venue="Harvard Data Sci. Review",
      cat="deploy", pages=55, data=["Census (restricted)"],
      did="Nationwide DP deployment (zCDP + discrete Gaussian); ships \u2018invariants\u2019 outside \u03b5.",
      gap="Invariants documented only in prose/policy \u2014 not a machine-checkable field.",
      fill="Our real-world case study; we make \u2018which fields are outside \u03b5\u2019 signed & checkable."),
 dict(id="P10", auth="Dibia, Lu, Bhattacharjee, Near & Feng", short="Dibia et al.",
      title="\u201cWe Need a Standard\u201d: Toward an Expert-Informed Privacy Label for DP", year=2026, venue="PoPETs",
      cat="human", pages=21, data=["\u2014 (12 experts)"],
      did="Expert-elicited 9-category DP privacy label (\u2248 our Privacy Data Sheet, field for field).",
      gap="No signing, and no way to report a metric's limits \u2014 an expert called it \u2018privacy theater\u2019.",
      fill="\u2605 LEAD: we sign the label, make it machine-checkable, and report the audit's operating range."),
 dict(id="P11", auth="Song, Sarathy, Shoemate & Vadhan", short="Song et al.",
      title="\u201cI inherently just trust that it works\u201d: Mental Models of DP Libraries", year=2024, venue="CSCW",
      cat="human", pages=39, data=["\u2014 (5+17 people)"],
      did="Data analysts trust DP libraries implicitly and do not verify guarantees.",
      gap="Diagnoses blind trust but builds no tool.",
      fill="\u2605 THE PREMISE: why an automatic, signed, checkable release is needed."),
]
byid={p["id"]:p for p in P}

def esc(s): return html.escape(str(s))

# ================= SVG: bubble landscape =================
def bubble_svg():
    W,H=1000,600; x0,x1=110,930; y0,y1=95,505
    years=[2022,2023,2024,2025,2026]
    def xpos(y): return x0+(y-2022)/(2026-2022)*(x1-x0)
    cats=list(CAT.keys())
    def ypos(c):
        i=cats.index(c); return y0+i/(len(cats)-1)*(y1-y0)
    s=[f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="Inter,Segoe UI,sans-serif">']
    # grid + year labels
    for yr in years:
        xx=xpos(yr)
        s.append(f'<line x1="{xx:.0f}" y1="{y0-15}" x2="{xx:.0f}" y2="{y1+18}" stroke="#e7e0d3" stroke-width="1"/>')
        s.append(f'<text x="{xx:.0f}" y="{y1+40}" text-anchor="middle" font-size="20" fill="{MUT}" font-weight="600">{yr}</text>')
    # category rows
    for c in cats:
        col,lab=CAT[c]; yy=ypos(c)
        s.append(f'<text x="{x0-18}" y="{yy+5}" text-anchor="end" font-size="15" fill="{col}" font-weight="700">{esc(lab)}</text>')
        s.append(f'<line x1="{x0}" y1="{yy}" x2="{x1}" y2="{yy}" stroke="{col}" stroke-opacity="0.12" stroke-width="1"/>')
    # jitter for same cat+year
    from collections import defaultdict
    seen=defaultdict(int)
    for p in P:
        key=(p["cat"],p["year"]); k=seen[key]; seen[key]+=1
    seen2=defaultdict(int)
    for p in P:
        col,_=CAT[p["cat"]]
        cx=xpos(p["year"]); cy=ypos(p["cat"])
        key=(p["cat"],p["year"]); n=seen[key]; idx=seen2[key]; seen2[key]+=1
        if n>1: cx += (idx-(n-1)/2)*46
        r=12+math.sqrt(p["pages"])*4.2
        s.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{r:.0f}" fill="{col}" fill-opacity="0.82" stroke="#fff" stroke-width="2"/>')
        s.append(f'<text x="{cx:.0f}" y="{cy+5:.0f}" text-anchor="middle" font-size="15" font-weight="800" fill="#fff">{p["id"]}</text>')
    # size legend
    s.append(f'<text x="{x0}" y="{H-16}" font-size="13" fill="{MUT}">Bubble size \u221d paper length (pages) \u00b7 colour = research angle \u00b7 x-axis = year</text>')
    s.append('</svg>')
    return "".join(s)

# ================= SVG: themes heatmap =================
THEMES=[
 ("Reads structure from private data \u2192 breaks DP", {"P1":1,"P2":1,"P4":1,"P5":1,"P11":.7,"P8":.5}),
 ("Preprocessing is a leak surface", {"P4":1,"P5":1,"P6":1,"P7":1}),
 ("Naive / black-box metrics miss leaks", {"P2":1,"P6":1,"P1":.6}),
 ("Membership / reconstruction attack", {"P1":1,"P2":1,"P4":1,"P6":1,"P7":.4}),
 ("Not signed / not machine-checkable (the gap)", {"P9":1,"P10":1,"P11":1}),
 ("Real deployment / proposed standard", {"P9":1,"P10":1}),
]
def heatmap_svg():
    rows=THEMES; cols=[p["id"] for p in P]
    left=430; top=70; cw=46; ch=46; W=left+len(cols)*cw+20; H=top+len(rows)*ch+30
    s=[f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="Inter,Segoe UI,sans-serif">']
    for j,cid in enumerate(cols):
        cx=left+j*cw+cw/2; col,_=CAT[byid[cid]["cat"]]
        s.append(f'<text x="{cx:.0f}" y="{top-14}" text-anchor="middle" font-size="15" font-weight="800" fill="{col}">{cid}</text>')
    for i,(name,mem) in enumerate(rows):
        cy=top+i*ch
        s.append(f'<text x="{left-14}" y="{cy+ch/2+5:.0f}" text-anchor="end" font-size="14.5" fill="{INK}">{esc(name)}</text>')
        for j,cid in enumerate(cols):
            cx=left+j*cw; v=mem.get(cid,0)
            if v>0:
                col,_=CAT[byid[cid]["cat"]]
                s.append(f'<rect x="{cx+3}" y="{cy+3}" width="{cw-6}" height="{ch-6}" rx="8" fill="{col}" fill-opacity="{0.28+0.62*v:.2f}"/>')
                if v>=1: s.append(f'<text x="{cx+cw/2:.0f}" y="{cy+ch/2+5:.0f}" text-anchor="middle" font-size="16" font-weight="800" fill="#fff">\u2714</text>')
            else:
                s.append(f'<rect x="{cx+3}" y="{cy+3}" width="{cw-6}" height="{ch-6}" rx="8" fill="#efe9dc"/>')
    s.append('</svg>')
    return "".join(s)

# ================= SVG: dataset overlap =================
DSETS=[("Adult",["P1","P2","P5","P7","P8"]),("Bank",["P7"]),("Wine",["P4","P5"]),
       ("Gas",["P5"]),("Texas",["P1"]),("SF Fire",["P2","P8"]),
       ("Imbalanced set","P6".split()),("Census","P9".split()),
       ("ACSIncome (ours only)",[])]
def dataset_svg():
    rows=DSETS; left=250; top=50; rh=44; W=760; H=top+len(rows)*rh+20
    s=[f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="Inter,Segoe UI,sans-serif">']
    for i,(name,ids) in enumerate(rows):
        cy=top+i*rh
        star = name.endswith("ours only)")
        s.append(f'<text x="{left-16}" y="{cy+rh/2+5:.0f}" text-anchor="end" font-size="16" font-weight="700" fill="{GREEN if star else INK}">{esc(name)}</text>')
        s.append(f'<line x1="{left}" y1="{cy+rh/2}" x2="{W-30}" y2="{cy+rh/2}" stroke="#e7e0d3" stroke-width="1"/>')
        if not ids:
            s.append(f'<text x="{left+8}" y="{cy+rh/2+5:.0f}" font-size="14" fill="{GREEN}" font-style="italic">unique to SynthProof \u2014 no surveyed paper uses it</text>')
        for k,cid in enumerate(ids):
            cx=left+34+k*70; col,_=CAT[byid[cid]["cat"]]
            s.append(f'<circle cx="{cx}" cy="{cy+rh/2}" r="18" fill="{col}" stroke="#fff" stroke-width="2"/>')
            s.append(f'<text x="{cx}" y="{cy+rh/2+5}" text-anchor="middle" font-size="13" font-weight="800" fill="#fff">{cid}</text>')
    s.append('</svg>')
    return "".join(s)

# ================= assemble HTML =================
def chip(cat):
    col,lab=CAT[cat]; return f'<span class="chip" style="background:{col}1f;color:{col};border:1px solid {col}55">{esc(lab)}</span>'

def legend():
    items="".join(f'<span class="lg"><span class="dot" style="background:{c}"></span>{esc(l)}</span>' for c,(col,l) in [(k,CAT[k]) for k in CAT] for c,l in [(col,l)])
    return f'<div class="legend">{items}</div>'

# paper catalogue rows
cat_rows=""
for p in P:
    col,lab=CAT[p["cat"]]
    ds=" ".join(f'<span class="ds">{esc(d)}</span>' for d in p["data"])
    cat_rows+=f'''<tr>
      <td class="pid" style="color:{col}">{p["id"]}</td>
      <td><div class="ptitle">{esc(p["title"])}</div><div class="pauth">{esc(p["auth"])}</div></td>
      <td class="pyear">{p["year"]}</td>
      <td class="pven">{esc(p["venue"])}</td>
      <td>{chip(p["cat"])}</td>
      <td class="pds">{ds}</td></tr>'''

# comparison scorecard cards
sc_cards=[]
for p in P:
    col,lab=CAT[p["cat"]]
    sc_cards.append(f'''<div class="sc" style="border-top:5px solid {col}">
      <div class="sc-h"><span class="sc-id" style="background:{col}">{p["id"]}</span>
      <span class="sc-name">{esc(p["short"])} <span class="sc-yr">{p["year"]}</span></span></div>
      <div class="sc-row"><span class="tick">\u2714</span><div><b>What they did</b><br>{esc(p["did"])}</div></div>
      <div class="sc-row"><span class="cross">\u2717</span><div><b>The gap</b><br>{esc(p["gap"])}</div></div>
      <div class="sc-row"><span class="seal">\u25c9</span><div><b>SynthProof fills it</b><br>{esc(p["fill"])}</div></div>
    </div>''')

CSS = """
*{box-sizing:border-box}
:root{--ink:#191627;--mut:#5b5670;--paper:#FBF7F0;--card:#fff;--green:#2FA36B;--coral:#E5484D;--gold:#C98A2B}
@page{size:A4;margin:0}
html,body{margin:0;padding:0;background:#e9e3d6;-webkit-print-color-adjust:exact;print-color-adjust:exact;color:var(--ink);
 font-family:Inter,'Segoe UI',system-ui,sans-serif}
.page{position:relative;width:210mm;min-height:292mm;background:var(--paper);padding:12mm 14mm 11mm;
 page-break-after:always;overflow:hidden}
.page:last-child{page-break-after:auto}
h1,h2,h3{font-family:Fraunces,Georgia,serif;text-wrap:balance;margin:0}
.eyebrow{font-size:12px;letter-spacing:.22em;text-transform:uppercase;color:var(--gold);font-weight:700}
.h-rule{height:5px;width:64px;background:linear-gradient(90deg,#E5484D,#F5A623,#3E7BFA,#7C3AED);border-radius:3px;margin:10px 0 18px}
.sectitle{font-size:26px;line-height:1.05;margin-bottom:3px}
.lede{color:var(--mut);font-size:12.8px;max-width:66ch;line-height:1.45}
.chip{display:inline-block;padding:3px 9px;border-radius:20px;font-size:11px;font-weight:700;white-space:nowrap}
.ds{display:inline-block;background:#efe9dc;border-radius:6px;padding:2px 7px;margin:2px 3px 0 0;font-size:11px;color:#4a4560;font-family:'JetBrains Mono',Consolas,monospace}
.legend{display:flex;flex-wrap:wrap;gap:12px 18px;margin:14px 0 6px}
.lg{display:flex;align-items:center;gap:7px;font-size:12.5px;color:var(--mut);font-weight:600}
.dot{width:12px;height:12px;border-radius:50%}
table.cat{width:100%;border-collapse:collapse;margin-top:12px;font-size:11.5px}
table.cat td{padding:4px 8px;border-bottom:1px solid #eadfce;vertical-align:top}
.pid{font-family:'JetBrains Mono',monospace;font-weight:800;font-size:14px;width:34px}
.ptitle{font-weight:700;color:var(--ink);line-height:1.14;font-size:11px}
.pauth{color:var(--mut);font-size:10px;margin-top:1px}
.pyear{font-family:'JetBrains Mono',monospace;font-weight:700;color:var(--mut)}
.pven{font-size:11.5px;color:#4a4560;width:120px}
.pds{width:150px}
.card{background:var(--card);border-radius:16px;padding:16px 18px;box-shadow:0 8px 24px rgba(30,20,10,.06);border:1px solid #efe7d7}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.scores{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:8px}
.sc{background:var(--card);border-radius:10px;padding:4px 9px;box-shadow:0 4px 10px rgba(30,20,10,.05);border:1px solid #efe7d7}
.sc-h{display:flex;align-items:center;gap:6px;margin-bottom:2px}
.sc-id{color:#fff;font-family:'JetBrains Mono',monospace;font-weight:800;font-size:12px;padding:1px 7px;border-radius:6px}
.sc-name{font-weight:700;font-size:12.5px}.sc-yr{color:var(--mut);font-weight:600;font-size:10.5px}
.sc-row{display:flex;gap:6px;font-size:8.7px;line-height:1.17;margin-top:2.5px;color:#3a3550}
.sc-row b{color:var(--ink)}
.tick{color:var(--green);font-weight:900}.cross{color:var(--coral);font-weight:900}.seal{color:var(--gold);font-weight:900}
.foot{position:absolute;left:15mm;right:15mm;bottom:8mm;display:flex;justify-content:space-between;
 font-size:10.5px;color:#9a9280;border-top:1px solid #e7dcc9;padding-top:6px;font-family:'JetBrains Mono',monospace}
/* cover */
.cover{background:radial-gradient(1200px 700px at 80% -10%,#2a2450,#141126 60%);color:#f6f2ea}
.cover .eyebrow{color:#F5A623}
.cover h1{font-size:52px;line-height:1.02;color:#fff;margin-top:8px}
.cover .sub{font-size:19px;color:#c9c3e6;margin-top:14px;max-width:52ch;line-height:1.5}
.cover .tag{font-family:'JetBrains Mono',monospace;color:#12B5A5;margin-top:18px;font-size:14px}
.count{display:flex;gap:10px;margin-top:26px;flex-wrap:wrap}
.count .b{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.16);border-radius:12px;padding:10px 14px}
.count .n{font-family:Fraunces,serif;font-size:30px;font-weight:700;color:#fff}
.count .l{font-size:11px;color:#b9b3d6;letter-spacing:.04em}
.cover .authors{margin-top:auto;font-size:12.5px;color:#b9b3d6;line-height:1.6}
.flowbox{background:var(--card);border-radius:16px;border:1px solid #efe7d7;padding:14px;margin-top:12px}
.note{background:#fff8ec;border:1px solid #f0dcae;border-radius:12px;padding:12px 14px;font-size:12.5px;color:#6a5320;margin-top:12px;line-height:1.5}
.note b{color:#8a5a2b}
"""

# ---- release-boundary flowchart (static SVG) ----
def flow_svg():
    return '''<svg viewBox="0 0 1000 430" xmlns="http://www.w3.org/2000/svg" font-family="Inter,Segoe UI,sans-serif">
    <defs><marker id="ar" markerWidth="9" markerHeight="9" refX="7" refY="3" orient="auto"><path d="M0,0 L7,3 L0,6 Z" fill="#191627"/></marker></defs>
    <!-- shield over mechanism -->
    <rect x="360" y="70" width="210" height="150" rx="14" fill="#3E7BFA" fill-opacity="0.10" stroke="#3E7BFA" stroke-dasharray="5 4"/>
    <text x="465" y="60" text-anchor="middle" font-size="14" font-weight="800" fill="#3E7BFA">\u03b5 protects ONLY here</text>
    <!-- boxes -->
    <g font-size="14" font-weight="700" fill="#191627">
    <rect x="40" y="110" width="150" height="70" rx="12" fill="#fff" stroke="#e0d7c4"/><text x="115" y="140" text-anchor="middle">Sensitive</text><text x="115" y="160" text-anchor="middle">table D</text>
    <rect x="230" y="110" width="150" height="70" rx="12" fill="#fff" stroke="#C98A2B"/><text x="305" y="140" text-anchor="middle" fill="#C98A2B">Preprocessing</text><text x="305" y="160" text-anchor="middle" font-size="11" fill="#7a6a4a">impute / discretise</text>
    <rect x="410" y="110" width="150" height="70" rx="12" fill="#eef4ff" stroke="#3E7BFA"/><text x="485" y="140" text-anchor="middle" fill="#3E7BFA">DP Mechanism</text><text x="485" y="160" text-anchor="middle" font-size="11" fill="#4a6ab0">AIM (\u03b5,\u03b4)</text>
    <rect x="600" y="110" width="165" height="70" rx="12" fill="#fff" stroke="#e0d7c4"/><text x="682" y="136" text-anchor="middle">Release artifact</text><text x="682" y="156" text-anchor="middle" font-size="10.5" fill="#7a6a4a">table + SIGNED sheet</text>
    <rect x="805" y="110" width="150" height="70" rx="12" fill="#eafaf4" stroke="#12B5A5"/><text x="880" y="136" text-anchor="middle" fill="#0e8a7e">boundary-audit</text><text x="880" y="156" text-anchor="middle" font-size="10.5" fill="#3aa">+ Verifier</text>
    </g>
    <g stroke="#191627" stroke-width="2" marker-end="url(#ar)">
    <line x1="190" y1="145" x2="228" y2="145"/><line x1="380" y1="145" x2="408" y2="145"/>
    <line x1="560" y1="145" x2="598" y2="145"/><line x1="765" y1="145" x2="803" y2="145"/></g>
    <!-- leak markers -->
    <text x="305" y="250" text-anchor="middle" font-size="13" font-weight="800" fill="#E5484D">\u2191 LEAK before</text>
    <text x="305" y="268" text-anchor="middle" font-size="11" fill="#b03">preprocessing</text>
    <text x="682" y="250" text-anchor="middle" font-size="13" font-weight="800" fill="#E5484D">\u2191 LEAK after</text>
    <text x="682" y="268" text-anchor="middle" font-size="11" fill="#b03">seed \u00b7 n \u00b7 hash \u00b7 eval</text>
    <line x1="305" y1="230" x2="305" y2="185" stroke="#E5484D" stroke-width="2" stroke-dasharray="4 3"/>
    <line x1="682" y1="230" x2="682" y2="185" stroke="#E5484D" stroke-width="2" stroke-dasharray="4 3"/>
    <!-- paper tags -->
    <g font-family="'JetBrains Mono',monospace" font-size="12" font-weight="800">
    <text x="305" y="300" text-anchor="middle" fill="#C98A2B">P4 P5 P6 P7</text>
    <text x="485" y="300" text-anchor="middle" fill="#3E7BFA">P8 P2 P3</text>
    <text x="682" y="300" text-anchor="middle" fill="#E5484D">P1 P9</text>
    <text x="880" y="300" text-anchor="middle" fill="#7C3AED">P10 P11</text>
    </g>
    <g font-size="11" fill="#5b5670"><text x="305" y="318" text-anchor="middle">who audits this step</text>
    <text x="485" y="318" text-anchor="middle">the mechanism</text><text x="682" y="318" text-anchor="middle">the shipped file</text>
    <text x="880" y="318" text-anchor="middle">what SynthProof adds</text></g>
    <rect x="805" y="345" width="150" height="60" rx="12" fill="#2FA36B" fill-opacity="0.12" stroke="#2FA36B"/>
    <text x="880" y="372" text-anchor="middle" font-size="12.5" font-weight="800" fill="#2FA36B">SIGNED &amp;</text>
    <text x="880" y="390" text-anchor="middle" font-size="12.5" font-weight="800" fill="#2FA36B">CHECKABLE</text>
    </svg>'''

def foot(n):
    return f'<div class="foot"><span>SynthProof \u00b7 Literature Survey</span><span>Machine-Checkable Release-Boundary Auditing for DP Synthetic Data</span><span>{n}</span></div>'

pages=[]
# COVER
pages.append(f'''<section class="page cover" style="display:flex;flex-direction:column">
  <div class="eyebrow">B.Tech Capstone \u00b7 SCET, MIT-WPU Pune \u00b7 Visual Literature Survey</div>
  <h1>The Privacy of<br>Synthetic Data</h1>
  <div class="sub">Eleven papers that define what a differentially private data release should promise \u2014 and where each one stops short.</div>
  <div class="tag">SynthProof \u2014 synthetic data that ships with its proof</div>
  <div class="count">
    <div class="b"><div class="n">11</div><div class="l">PAPERS SURVEYED</div></div>
    <div class="b"><div class="n">2022\u20132026</div><div class="l">USENIX \u00b7 VLDB \u00b7 CCS \u00b7 PoPETs \u00b7 ICLR \u00b7 CSCW</div></div>
    <div class="b"><div class="n">6</div><div class="l">RESEARCH ANGLES</div></div>
    <div class="b"><div class="n">1</div><div class="l">GAP WE FILL</div></div>
  </div>
  <div style="margin-top:30px">{legend()}</div>
  <div class="authors">Raj Modi \u00b7 Krishna Renuse \u00b7 Levinesh G R \u00b7 Aaditya Kumar Sinha<br>Guide: Dr. Shilpa Sonawani</div>
</section>''')

# PAGE 2 catalogue
pages.append(f'''<section class="page">
  <div class="eyebrow">The corpus</div><div class="h-rule"></div>
  <h2 class="sectitle">The eleven papers at a glance</h2>
  <p class="lede">Every paper read in full and verified against its PDF \u2014 author, title, year, venue, research angle, and the datasets it used.</p>
  <table class="cat"><tr style="font-size:10.5px;letter-spacing:.08em;text-transform:uppercase;color:#9a9280">
   <td>#</td><td>Title &amp; authors</td><td>Year</td><td>Venue</td><td>Angle</td><td>Datasets</td></tr>
  {cat_rows}</table>
  {foot("02")}</section>''')

# PAGE 3 bubble landscape
pages.append(f'''<section class="page">
  <div class="eyebrow">The landscape</div><div class="h-rule"></div>
  <h2 class="sectitle">A map of the field</h2>
  <p class="lede">Each bubble is a paper, placed by <b>year</b> (left\u2192right) and <b>research angle</b> (colour &amp; row); bubble size grows with the paper's length. The field moves from attacks &amp; mechanisms (2022) toward standards &amp; human factors (2026).</p>
  <div class="card" style="margin-top:14px">{bubble_svg()}</div>
  {foot("03")}</section>''')

# PAGE 4-5 comparison scorecard (split into two balanced pages)
def sc_page(cards, sub, fn):
    return f'''<section class="page">
  <div class="eyebrow">Head to head {sub}</div><div class="h-rule"></div>
  <h2 class="sectitle">What they did \u2714 \u00b7 the gap \u2717 \u00b7 what we fill \u25c9</h2>
  <p class="lede">For every paper: its contribution, the gap it leaves, and how SynthProof closes it.</p>
  <div class="scores">{"".join(cards)}</div>
  {foot(fn)}</section>'''
pages.append(sc_page(sc_cards[:6], "\u00b7 papers 1\u20136", "04"))
pages.append(sc_page(sc_cards[6:], "\u00b7 papers 7\u201311", "05"))

# PAGE 5 flowchart
pages.append(f'''<section class="page">
  <div class="eyebrow">Where each paper sits</div><div class="h-rule"></div>
  <h2 class="sectitle">The release boundary \u2014 and who guards what</h2>
  <p class="lede">Differential privacy protects only the machine in the middle. A real deployment ships a <b>file</b>, and it can leak before the machine (preprocessing) and after it (the label). Each paper studies one stretch of this pipe; SynthProof adds the signed, checkable layer at the end.</p>
  <div class="flowbox">{flow_svg()}</div>
  <div class="note"><b>Read it like this:</b> P4/P5/P6/P7 audit the preprocessing step \u00b7 P8/P2/P3 work on the mechanism \u00b7 P1 &amp; P9 expose what leaks in the shipped artifact \u00b7 P10 &amp; P11 show the field agreed <i>what</i> to disclose but never made it checkable. That last box is SynthProof.</div>
  {foot("06")}</section>''')

# PAGE 6 themes heatmap
pages.append(f'''<section class="page">
  <div class="eyebrow">The threads that connect them</div><div class="h-rule"></div>
  <h2 class="sectitle">Cross-cutting themes</h2>
  <p class="lede">A filled cell means the paper touches that theme. Four threads run across the corpus \u2014 and the boldest one, \u201creading structure from private data breaks DP,\u201d is the exact bug our D1 fix and domain-source rule address.</p>
  <div class="card" style="margin-top:14px;overflow-x:auto">{heatmap_svg()}</div>
  {foot("07")}</section>''')

# PAGE 7 datasets + closing
pages.append(f'''<section class="page">
  <div class="eyebrow">Shared ground</div><div class="h-rule"></div>
  <h2 class="sectitle">Which paper used which dataset</h2>
  <p class="lede">UCI <b>Adult</b> is the shared benchmark (5 papers) \u2014 where our same-dataset comparison lives. <b>P7</b> also uses <b>Bank</b>. <b>ACSIncome</b> is ours alone.</p>
  <div class="card" style="margin-top:12px;overflow-x:auto">{dataset_svg()}</div>
  <div class="note" style="margin-top:16px"><b>The one-line verdict.</b> The field converged on <i>what</i> a DP release should disclose (P10) but never on making it <i>checkable</i> \u2014 no signing (P10), no limit-reporting (\u201cprivacy theater\u201d), invariants in prose only (P9), and analysts who never verify (P11). That gap \u2014 <b>signed + machine-checkable + limit-reporting</b> \u2014 is SynthProof.</div>
  {foot("08")}</section>''')

doc=f'<!doctype html><html><head><meta charset="utf-8">'\
    f'<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'\
    f'<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=Inter:wght@400;600;700;800&family=JetBrains+Mono:wght@700;800&display=swap" rel="stylesheet">'\
    f'<title>Synthetic-Data Privacy Survey</title><style>{CSS}</style></head><body>{"".join(pages)}</body></html>'

os.makedirs(os.path.dirname(OUT_HTML),exist_ok=True)
open(OUT_HTML,"w",encoding="utf-8").write(doc)
print("wrote",OUT_HTML,len(doc),"bytes")
