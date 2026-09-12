"""Renders `DEFENCE.md` to `SynthProof-Defence-Pack.pdf` beside the SynthProof folder.

This is the document the team carries into a viva when the panel asks about validity, the
literature, and whether the numbers are real. Which makes a stale number here worse than a
stale number anywhere else in the project: it would teach four people to defend, out loud and
under questioning, a figure the data no longer supports.

So `verify_numbers()` re-reads the committed result JSON and **refuses to build** if any
headline figure in the prose has drifted. Add a check here whenever you add a number to the
text. The rule the whole project runs on applies hardest to this file: fix the prose, never
the check.

Run from the repository root:

    python docs/defence/build_pdf.py
"""

from __future__ import annotations

import json
import math
import os
import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[2]
SRC = Path(__file__).resolve().parent / "DEFENCE.md"
# The deliverables folder, not the folder above the repo. Before the 2026-09-12
# reorganisation these three builders wrote straight into the CAPSTONE root, which is where
# the PDFs used to live; after it they kept writing there while the shipped copies moved into
# 01_Thesis_and_Deliverables/, so `make defence` silently left the deliverable stale and
# dropped a stray file at the root. Created if absent so a standalone clone still builds.
DELIVERABLES = ROOT.parent / "01_Thesis_and_Deliverables"
DELIVERABLES.mkdir(parents=True, exist_ok=True)
OUT = DELIVERABLES / "SynthProof-Defence-Pack.pdf"

INK = colors.HexColor("#1B1D24")
SOFT = colors.HexColor("#4C5160")
FAINT = colors.HexColor("#8A8F9E")
PROVED = colors.HexColor("#4B46C4")
AUDITED = colors.HexColor("#C2622A")
RULE = colors.HexColor("#D8D6CE")
WASH = colors.HexColor("#F4F3EE")


# ── fonts ──────────────────────────────────────────────────────────────────────

FONT_DIR = Path("C:/Windows/Fonts")
FACES = {
    "Body": "times.ttf",
    "Body-Bold": "timesbd.ttf",
    "Body-Italic": "timesi.ttf",
    "Body-BoldItalic": "timesbi.ttf",
    "Head": "arialbd.ttf",
    "Head-Regular": "arial.ttf",
    "Mono": "consola.ttf",
    "Mono-Bold": "consolab.ttf",
}


def register_fonts() -> None:
    missing = [f for f in FACES.values() if not (FONT_DIR / f).exists()]
    if missing:
        sys.exit(f"Missing system fonts: {missing}. This build script assumes Windows.")
    for name, file in FACES.items():
        pdfmetrics.registerFont(TTFont(name, str(FONT_DIR / file)))
    pdfmetrics.registerFontFamily(
        "Body",
        normal="Body",
        bold="Body-Bold",
        italic="Body-Italic",
        boldItalic="Body-BoldItalic",
    )


# ── number verification ────────────────────────────────────────────────────────


def eps_max(r: int, alpha: float = 0.05) -> float:
    """The one-run audit ceiling: the largest epsilon r guesses can certify.

    Solves p**r = alpha for a perfect adversary. This is the arithmetic behind the whole of
    section 7.1, so the document's claims about it are checked against the formula rather
    than against a table someone typed.
    """
    a = alpha ** (1.0 / r)
    return math.log(a / (1.0 - a))


def canaries_for(eps: float, alpha: float = 0.05) -> int:
    """Smallest r whose ceiling reaches eps."""
    r = 1
    while eps_max(r, alpha) < eps:
        r += 1
    return r


def verify_numbers(text: str) -> list[str]:
    """Re-reads the committed results and checks the prose still agrees with them."""
    problems: list[str] = []

    def load(rel: str) -> dict:
        return json.loads((ROOT / rel).read_text(encoding="utf-8"))

    def want(label: str, value: float, shown: str, places: int = 4) -> None:
        if f"{value:.{places}f}" != shown:
            problems.append(f"{label}: results say {value:.{places}f}, document says {shown}")

    def need(needle: str, why: str) -> None:
        if needle not in text:
            problems.append(f"missing from the document — {why}: {needle!r}")

    # ── H1, UCI Adult ─────────────────────────────────────────────────────────
    adult = load("results/h1_all_families.json")

    def cell(block: dict, mech: str, eps: float) -> dict:
        for c in block["cells"]:
            if c["mechanism"] == mech and abs(c["target_eps"] - eps) < 1e-9:
                return c
        problems.append(f"no cell for {mech} at eps={eps}")
        return {}

    for mech, eps, corr in [
        ("independent", 0.5, "0.0934"),
        ("independent", 8.0, "0.0947"),
        ("pairwise", 4.0, "0.0197"),
        ("pairwise", 8.0, "0.0283"),
        ("aim", 1.0, "0.0424"),
        ("aim", 8.0, "0.0078"),
    ]:
        c = cell(adult, mech, eps)
        if c:
            want(f"Adult {mech} eps={eps} correlation_error", c["correlation_error"]["mean"], corr)

    for mech, eps, f1 in [("aim", 1.0, "0.540"), ("aim", 8.0, "0.505")]:
        c = cell(adult, mech, eps)
        if c:
            want(f"Adult {mech} eps={eps} tstr_f1", c["tstr_f1"]["mean"], f1, places=3)

    trtr = cell(adult, "independent", 0.5).get("trtr_f1")
    if trtr:
        want("Adult TRTR mean", trtr["mean"], "0.660", places=3)
        want("Adult TRTR lo", trtr["lo"], "0.646", places=3)
        want("Adult TRTR hi", trtr["hi"], "0.674", places=3)

    # The independent baseline being FLAT in epsilon is a control, and the document leans on
    # it. If it ever stops being flat, the claim must change.
    lo = cell(adult, "independent", 0.5).get("correlation_error", {}).get("mean")
    hi = cell(adult, "independent", 8.0).get("correlation_error", {}).get("mean")
    if lo is not None and hi is not None and abs(hi - lo) > 0.01:
        problems.append(
            f"the 'independent is flat in epsilon' control no longer holds: "
            f"{lo:.4f} at eps=0.5 vs {hi:.4f} at eps=8"
        )

    # ── H1, ACSIncome: the ordering that did NOT transfer ─────────────────────
    acs = load("results/acs/h1_all_families.json")
    acs_vals = {}
    for mech, shown in [("independent", "0.0535"), ("pairwise", "0.0202"), ("aim", "0.0626")]:
        c = cell(acs, mech, 8.0)
        if c:
            acs_vals[mech] = c["correlation_error"]["mean"]
            want(f"ACS {mech} eps=8 correlation_error", acs_vals[mech], shown)

    if len(acs_vals) == 3:
        # The whole of section 7.2 rests on pairwise beating both others on ACS while aim
        # does NOT beat independent. If that inverts back, the finding is gone.
        if not acs_vals["pairwise"] < acs_vals["independent"] < acs_vals["aim"]:
            problems.append(
                "the ACS ordering the document reports (pairwise < independent < aim) no "
                f"longer holds: {acs_vals}"
            )

    adult_aim = cell(adult, "aim", 8.0).get("correlation_error", {}).get("mean")
    if adult_aim is not None and acs_vals.get("aim") is not None:
        if not adult_aim < acs_vals["aim"]:
            problems.append("AIM is no longer better on Adult than on ACS at eps=8")

    # ── the audit ceiling, checked against the formula itself ─────────────────
    want("ceiling at m=60", eps_max(60), "2.97", places=2)
    if f"{canaries_for(7.36)}" not in ("4711", "4710", "4712"):
        problems.append(
            f"canaries needed to certify eps=7.36 is now {canaries_for(7.36)}, "
            "document says 4,711"
        )
    for r, shown in [(10, "1.05"), (400, "4.89"), (800, "5.59")]:
        want(f"one-run ceiling at r={r}", eps_max(r), shown, places=2)

    # The paired auditor has a DIFFERENT ceiling, and the two were conflated in an early
    # draft of this document. Check the measured row against the file it came from, not
    # against the one-run formula.
    floor = load("results/detection_floor.json")
    measured = {
        c["num_canaries"]: c["max_audited_eps"] for c in floor["cells"] if c["leak_fraction"] == 1.0
    }
    for m, shown in [(10, "0.81"), (400, "4.68"), (800, "5.38")]:
        if m in measured:
            want(f"paired ceiling measured at m={m}", measured[m], shown, places=2)
        else:
            problems.append(f"detection_floor.json has no leak=1.0 cell at m={m}")

    # ── provenance ────────────────────────────────────────────────────────────
    manifest = load("results/MANIFEST.json")
    commit = manifest["git"]["commit"]
    if commit[:7] not in text:
        problems.append(f"manifest commit {commit[:7]} is not quoted in the document")

    # ── structural checks on the document itself ──────────────────────────────
    n_q = len(re.findall(r"^\*\*\d+\. ", text, re.M))
    if n_q < 45:
        problems.append(f"only {n_q} panel questions; the document promises 45")

    for heading, why in [
        ("## 3. Literature survey", "the panel asked about the literature survey"),
        ("## 4. Validity", "the panel asked about validity"),
        ("## 5. Authenticity", "the panel asked about authenticity"),
        ("## 8. Limitations", "limitations must be volunteered, not extracted"),
        ("### 3.10", "the survey must state its own gaps"),
    ]:
        need(heading, why)

    return problems


# ── markdown → flowables ───────────────────────────────────────────────────────

INLINE = [
    (re.compile(r"\*\*(.+?)\*\*"), r"<b>\1</b>"),
    (re.compile(r"(?<!\w)\*(?!\s)(.+?)(?<!\s)\*(?!\w)"), r"<i>\1</i>"),
    (re.compile(r"`(.+?)`"), r'<font name="Mono" size="8.6" color="#4B46C4">\1</font>'),
]


def inline(s: str) -> str:
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    for pattern, repl in INLINE:
        s = pattern.sub(repl, s)
    return s


def styles() -> dict[str, ParagraphStyle]:
    base = ParagraphStyle(
        "body",
        fontName="Body",
        fontSize=10.2,
        leading=14.2,
        textColor=INK,
        alignment=TA_LEFT,
        spaceAfter=6.2,
    )
    return {
        "body": base,
        "title": ParagraphStyle(
            "title",
            parent=base,
            fontName="Head",
            fontSize=26,
            leading=29,
            textColor=INK,
            spaceAfter=6,
        ),
        "h2": ParagraphStyle(
            "h2",
            parent=base,
            fontName="Head",
            fontSize=16,
            leading=19.5,
            textColor=PROVED,
            spaceBefore=2,
            spaceAfter=8,
        ),
        "h3": ParagraphStyle(
            "h3",
            parent=base,
            fontName="Head",
            fontSize=11,
            leading=14.2,
            textColor=INK,
            spaceBefore=9,
            spaceAfter=4,
        ),
        "bullet": ParagraphStyle(
            "bullet", parent=base, leftIndent=13, bulletIndent=3, spaceAfter=3.5
        ),
        "quote": ParagraphStyle(
            "quote",
            parent=base,
            fontSize=10.4,
            leading=14.6,
            leftIndent=9,
            rightIndent=6,
            textColor=INK,
            spaceBefore=3,
            spaceAfter=3,
        ),
        "cellhead": ParagraphStyle(
            "cellhead",
            parent=base,
            fontName="Head-Regular",
            fontSize=8.1,
            leading=10.6,
            textColor=SOFT,
            spaceAfter=0,
        ),
        "cell": ParagraphStyle("cell", parent=base, fontSize=8.9, leading=11.6, spaceAfter=0),
        "calc": ParagraphStyle(
            "calc",
            parent=base,
            fontName="Mono",
            fontSize=8.6,
            leading=13.6,
            textColor=INK,
            spaceAfter=0,
        ),
        "toc": ParagraphStyle("toc", parent=base, fontSize=10, leading=15, spaceAfter=0),
    }


def split_row(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def build_table(rows: list[list[str]], st: dict) -> Table:
    head, body = rows[0], rows[1:]
    data = [[Paragraph(inline(c), st["cellhead"]) for c in head]]
    data += [[Paragraph(inline(c), st["cell"]) for c in r] for r in body]
    t = Table(data, hAlign="LEFT", repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("LINEBELOW", (0, 0), (-1, 0), 0.7, PROVED),
                ("LINEBELOW", (0, 1), (-1, -2), 0.3, RULE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
                ("LEFTPADDING", (0, 0), (0, -1), 0),
                ("RIGHTPADDING", (-1, 0), (-1, -1), 0),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, WASH]),
            ]
        )
    )
    return t


def render(text: str, st: dict) -> list:
    story: list = []
    lines = text.split("\n")
    i = 0
    para: list[str] = []
    quote: list[str] = []
    first_section = True

    def flush_para() -> None:
        nonlocal para
        if para:
            story.append(Paragraph(inline(" ".join(para)), st["body"]))
            para = []

    def flush_quote() -> None:
        nonlocal quote
        if quote:
            inner = Paragraph(inline(" ".join(quote)), st["quote"])
            box = Table([[inner]], colWidths=[165 * mm], hAlign="LEFT")
            box.setStyle(
                TableStyle(
                    [
                        ("LINEBEFORE", (0, 0), (0, -1), 2.2, AUDITED),
                        ("BACKGROUND", (0, 0), (-1, -1), WASH),
                        ("LEFTPADDING", (0, 0), (-1, -1), 9),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                        ("TOPPADDING", (0, 0), (-1, -1), 7),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ]
                )
            )
            story.append(box)
            story.append(Spacer(1, 7))
            quote = []

    while i < len(lines):
        line = lines[i].rstrip()

        if not line.strip():
            flush_para()
            flush_quote()
            i += 1
            continue

        if line.startswith("> "):
            flush_para()
            quote.append(line[2:].strip())
            i += 1
            continue
        flush_quote()

        if line.startswith("```"):
            flush_para()
            i += 1
            block: list[str] = []
            while i < len(lines) and not lines[i].startswith("```"):
                block.append(lines[i])
                i += 1
            i += 1
            rendered = "<br/>".join(inline(b).replace(" ", "\u00a0") for b in block)
            box = Table([[Paragraph(rendered, st["calc"])]], colWidths=[165 * mm], hAlign="LEFT")
            box.setStyle(
                TableStyle(
                    [
                        ("LINEBEFORE", (0, 0), (0, -1), 2.2, PROVED),
                        ("BACKGROUND", (0, 0), (-1, -1), WASH),
                        ("LEFTPADDING", (0, 0), (-1, -1), 11),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                        ("TOPPADDING", (0, 0), (-1, -1), 9),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                    ]
                )
            )
            story.append(box)
            story.append(Spacer(1, 8))
            continue

        if line.startswith("| "):
            flush_para()
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = split_row(lines[i])
                if not all(set(c) <= set("-: ") for c in cells):
                    rows.append(cells)
                i += 1
            story.append(build_table(rows, st))
            story.append(Spacer(1, 8))
            continue

        if line.startswith("# "):
            flush_para()
            story.append(Spacer(1, 24 * mm))
            story.append(Paragraph(inline(line[2:]), st["title"]))
            story.append(
                HRFlowable(width="100%", thickness=2, color=PROVED, spaceBefore=4, spaceAfter=12)
            )
            i += 1
            continue

        if line.strip() == "<!--contents-->":
            flush_para()
            story.append(Spacer(1, 8))
            story.append(Paragraph("What is in here", st["h3"]))
            story.append(
                HRFlowable(width="100%", thickness=0.6, color=RULE, spaceBefore=2, spaceAfter=7)
            )
            entries = [ln[3:].strip() for ln in lines if ln.startswith("## ")]
            rows = [[Paragraph(inline(e), st["toc"])] for e in entries]
            toc = Table(rows, colWidths=[140 * mm], hAlign="LEFT")
            toc.setStyle(
                TableStyle(
                    [
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("TOPPADDING", (0, 0), (-1, -1), 1.4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.4),
                    ]
                )
            )
            story.append(toc)
            story.append(Spacer(1, 12))
            i += 1
            continue

        if line.startswith("## "):
            flush_para()
            if not first_section:
                story.append(PageBreak())
            first_section = False
            story.append(Paragraph(inline(line[3:]), st["h2"]))
            story.append(
                HRFlowable(width="100%", thickness=0.6, color=RULE, spaceBefore=0, spaceAfter=9)
            )
            i += 1
            continue

        if line.startswith("### "):
            flush_para()
            story.append(KeepTogether([Paragraph(inline(line[4:]), st["h3"])]))
            i += 1
            continue

        if line.strip() == "---":
            flush_para()
            i += 1
            continue

        if line.startswith("- ") or re.match(r"^\d+\. ", line):
            flush_para()
            if line.startswith("- "):
                bullet, content = "\u2013", line[2:]
            else:
                num, content = line.split(". ", 1)
                bullet = f"{num}."
            # Wrapped list items are indented continuations, not new paragraphs.
            i += 1
            while i < len(lines) and lines[i].startswith("  ") and lines[i].strip():
                content += " " + lines[i].strip()
                i += 1
            story.append(Paragraph(inline(content), st["bullet"], bulletText=bullet))
            continue

        para.append(line.strip())
        i += 1

    flush_para()
    flush_quote()
    return story


# ── page furniture ─────────────────────────────────────────────────────────────


def decorate(canvas, doc) -> None:
    canvas.saveState()
    w, h = A4
    canvas.setFont("Head-Regular", 7.4)
    canvas.setFillColor(FAINT)
    if doc.page > 1:
        canvas.drawString(22 * mm, h - 13 * mm, "SYNTHPROOF  \u00b7  DEFENCE PACK")
        canvas.drawRightString(
            w - 22 * mm, h - 13 * mm, "EVERY NUMBER TRACES TO A COMMITTED EXPERIMENT"
        )
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.4)
        canvas.line(22 * mm, h - 15.5 * mm, w - 22 * mm, h - 15.5 * mm)
    canvas.drawCentredString(w / 2, 12 * mm, str(doc.page))
    canvas.restoreState()


def main() -> None:
    register_fonts()
    text = SRC.read_text(encoding="utf-8")

    # Provenance is INJECTED, not typed. `verify_numbers` requires the document to quote the
    # commit its numbers were pinned at, which is right -- a defence pack that cannot say
    # where its figures came from is not evidence. But the hash was maintained by hand, so it
    # went stale the first time the manifest was re-pinned and the pack became unbuildable:
    # DEFENCE.md still quoted c10968c on 2026-09-12, several manifests later, and
    # `make defence` had been refusing ever since. Substituting it here keeps the printed
    # claim true without anyone having to remember.
    text = text.replace(
        "{MANIFEST_COMMIT}",
        json.loads((ROOT / "results/MANIFEST.json").read_text(encoding="utf-8"))["git"]["commit"][
            :7
        ],
    )

    problems = verify_numbers(text)
    if problems:
        print("REFUSING TO BUILD — the defence pack disagrees with the committed results:")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)

    st = styles()
    # Build to a temp name and swap, so an open PDF viewer gives a readable message rather
    # than a PermissionError traceback halfway through a build.
    tmp = OUT.with_suffix(".building.pdf")
    doc = BaseDocTemplate(
        str(tmp),
        pagesize=A4,
        leftMargin=22 * mm,
        rightMargin=22 * mm,
        topMargin=20 * mm,
        bottomMargin=18 * mm,
        title="SynthProof Defence Pack",
        author="SynthProof capstone team",
        subject="Validity, literature, authenticity and research depth",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="all", frames=[frame], onPage=decorate)])
    doc.build(render(text, st))

    from pypdf import PdfReader  # type: ignore

    pages = len(PdfReader(str(tmp)).pages)
    try:
        os.replace(tmp, OUT)
    except PermissionError:
        sys.exit(
            f"Could not write {OUT.name} - it is open in another program. Close the PDF "
            f"viewer and run this again. (The freshly built copy is at {tmp}.)"
        )
    print(
        f"wrote {OUT} - {pages} pages, {len(text.split())} words, "
        f"all headline numbers verified against results/"
    )


if __name__ == "__main__":
    main()
