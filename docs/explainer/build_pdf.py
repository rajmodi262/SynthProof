"""Renders `EXPLAINER.md` to `docs/explainer/SynthProof-Explainer.pdf`.

Two things this script does beyond formatting:

1. **It registers real TrueType fonts.** ReportLab's built-in faces are WinAnsi-encoded and
   have no Greek, so every epsilon and delta would render as a solid black box. Times New
   Roman and Arial cover the whole character set this document uses.

2. **It verifies the numbers.** The explainer quotes measurements, and a document that drifts
   away from the results files is worse than no document — it teaches four people to defend a
   number that is no longer true. `verify_numbers()` re-reads the committed JSON and refuses
   to build if any headline figure in the prose has gone stale. Add a check here whenever you
   add a number to the text.

Run from the repository root:

    python docs/explainer/build_pdf.py
"""

from __future__ import annotations

import json
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
SRC = Path(__file__).resolve().parent / "EXPLAINER.md"
OUT = Path(__file__).resolve().parent / "SynthProof-Explainer.pdf"

# The deck's palette, so the two deliverables read as one project.
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
        "Body", normal="Body", bold="Body-Bold", italic="Body-Italic",
        boldItalic="Body-BoldItalic",
    )


# ── number verification ────────────────────────────────────────────────────────


def verify_numbers(text: str) -> list[str]:
    """Re-reads the committed results and checks the prose still agrees with them.

    Returns a list of complaints. A non-empty list aborts the build: a study document that
    quietly disagrees with the data is the specific failure this project exists to prevent.
    """
    problems: list[str] = []

    def load(rel: str) -> dict:
        return json.loads((ROOT / rel).read_text(encoding="utf-8"))

    def cell(block: dict, mech: str, eps: float) -> dict:
        return next(c for c in block["cells"] if c["mechanism"] == mech and c["target_eps"] == eps)

    def want(label: str, value: float, shown: str, places: int = 4) -> None:
        if f"{value:.{places}f}" != shown:
            problems.append(f"{label}: prose says {shown}, results say {value:.{places}f}")

    adult = load("results/h1_all_families.json")
    acs = load("results/acs/h1_all_families.json")
    for name, block, mech, shown in [
        ("H1 adult aim eps8", adult, "aim", "0.0078"),
        ("H1 adult independent eps8", adult, "independent", "0.0947"),
        ("H1 adult pairwise eps8", adult, "pairwise", "0.0283"),
        ("H1 acs aim eps8", acs, "aim", "0.0626"),
        ("H1 acs independent eps8", acs, "independent", "0.0535"),
        ("H1 acs pairwise eps8", acs, "pairwise", "0.0202"),
    ]:
        v = cell(block, mech, 8.0)["correlation_error"]["mean"]
        want(name, v, shown)
        if shown not in text:
            problems.append(f"{name}: {shown} no longer appears in the prose")

    h2a = load("results/h2_analysis.json")["detectability"]
    h2c = load("results/acs/h2_analysis.json")["detectability"]
    want("H2 adult ceiling", h2a["ceiling"], "3.27", 2)
    want("H2 adult observed max", h2a["observed_max_epsilon"], "0.036", 3)
    want("H2 adult MDE", h2a["mde_epsilon"], "0.008", 3)
    if len(load("results/h2_analysis.json")["multiplicity"]["labels"]) != 14:
        problems.append("H2 adult: prose says 14 tests")
    if len(load("results/acs/h2_analysis.json")["multiplicity"]["labels"]) != 22:
        problems.append("H2 acs: prose says 22 tests")
    if any(load("results/h2_analysis.json")["multiplicity"]["bh_reject"]):
        problems.append("H2 adult: prose says zero survive FDR, but something does")
    if h2c["num_canaries"] != 44:
        problems.append("H2 acs canary count changed")

    conf = load("results/clique_confound.json")["summary"]["conditional"]
    for label, key, shown in [
        ("confound aim selected", "aim_on_selected", "0.026"),
        ("confound indep selected", "independent_on_selected", "0.112"),
        ("confound aim unselected", "aim_on_unselected", "0.059"),
        ("confound indep unselected", "independent_on_unselected", "0.061"),
    ]:
        want(label, conf[key]["mean"], shown, 3)
    # RETRACTION GATE, added 2026-08-25. `confound_confirmed` was renamed to
    # `confound_confirmed_RETRACTED` when a controlled ablation
    # (scripts/run_selection_ablation.py, 175 fits) showed the benefit of measuring a pair
    # scales with that pair's true dependence (corr = -0.898), so AIM's advantage on the pairs
    # it selects is the mechanism working as designed rather than an artefact of selection.
    # This gate now fails until the prose stops asserting the retracted claim -- which is the
    # whole point of having a gate that checks prose against committed JSON.
    adult_conf = load("results/clique_confound.json")
    if "confound_confirmed" in adult_conf:
        problems.append(
            "confound: results/clique_confound.json has been un-retracted; see "
            "results/SELECTION_ABLATION.md before restoring the claim"
        )
    if "superseded_by" not in adult_conf:
        problems.append("confound: expected a supersession note in clique_confound.json")
    explainer_text = (ROOT / "docs" / "explainer" / "EXPLAINER.md").read_text(encoding="utf-8")
    if "SELECTION_ABLATION" not in explainer_text:
        problems.append(
            "confound: EXPLAINER.md still presents the clique-selection confound without the "
            "2026-08-25 retraction. Cite results/SELECTION_ABLATION.md and state that the "
            "strong reading was withdrawn, or remove the claim."
        )

    floor = load("results/detection_floor.json")
    for c in floor["cells"]:
        if c["leak_fraction"] == 1.0 and c["num_canaries"] == 10:
            if c["mean_tpr"] != 1.0 or c["mean_fpr"] != 0.0:
                problems.append("floor: prose says 100% copying is caught perfectly at r=10")
    # The prose reports the negative control honestly rather than as a clean sweep: 34 of 35
    # runs at zero, one false positive at r=100. That single alarm is the expected behaviour
    # of a test run at alpha=0.05, and an earlier draft of this document claimed "exactly
    # zero" everywhere until this check caught it. Both halves are asserted.
    ctrl = [c for c in floor["cells"] if c["leak_fraction"] == 0.0]
    runs = sum(c["seeds"] for c in ctrl)
    alarms = sum(round(c["detection_rate"] * c["seeds"]) for c in ctrl)
    if runs != 35 or alarms != 1:
        problems.append(
            f"floor: prose says 34 of 35 control runs reported zero; results say "
            f"{runs - alarms} of {runs}"
        )
    hit = next(c for c in ctrl if c["detection_rate"] > 0)
    if hit["num_canaries"] != 100 or f"{hit['max_audited_eps']:.3f}" != "0.070":
        problems.append("floor: the single control false positive is no longer r=100 at 0.070")
    if floor["floors"].get("0.05") is not None:
        problems.append("floor: prose says 5% copying is never reliably detected")

    # The ceiling is a closed form, so check the two values the prose derives by hand.
    import math

    def eps_max(r: int, alpha: float = 0.05) -> float:
        a = alpha ** (1 / r)
        return math.log(a / (1 - a))

    want("ceiling r=10", eps_max(10), "1.05", 2)
    want("ceiling r=30", eps_max(30), "2.25", 2)

    return problems


# ── mini-markdown ──────────────────────────────────────────────────────────────

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
        "body", fontName="Body", fontSize=10.4, leading=14.6, textColor=INK,
        alignment=TA_LEFT, spaceAfter=6.5,
    )
    return {
        "body": base,
        "title": ParagraphStyle("title", parent=base, fontName="Head", fontSize=27,
                                leading=30, textColor=INK, spaceAfter=6),
        "h2": ParagraphStyle("h2", parent=base, fontName="Head", fontSize=16.5, leading=20,
                             textColor=PROVED, spaceBefore=2, spaceAfter=8),
        "h3": ParagraphStyle("h3", parent=base, fontName="Head", fontSize=11.2, leading=14.5,
                             textColor=INK, spaceBefore=9, spaceAfter=4),
        "bullet": ParagraphStyle("bullet", parent=base, leftIndent=13, bulletIndent=3,
                                 spaceAfter=3.5),
        "quote": ParagraphStyle("quote", parent=base, fontSize=10.6, leading=15,
                                leftIndent=9, rightIndent=6, textColor=INK,
                                spaceBefore=3, spaceAfter=3),
        "cellhead": ParagraphStyle("cellhead", parent=base, fontName="Head-Regular",
                                   fontSize=8.3, leading=11, textColor=SOFT, spaceAfter=0),
        "cell": ParagraphStyle("cell", parent=base, fontSize=9.2, leading=12, spaceAfter=0),
        # Worked calculations. Monospaced so the columns of an equation line up down the
        # page, which is most of what makes an arithmetic step followable by hand.
        "calc": ParagraphStyle("calc", parent=base, fontName="Mono", fontSize=9,
                               leading=14.5, textColor=INK, spaceAfter=0),
        "coverlead": ParagraphStyle("coverlead", parent=base, fontSize=12.4, leading=17.6,
                                    textColor=SOFT, spaceAfter=9),
        "toc": ParagraphStyle("toc", parent=base, fontSize=10, leading=15.5, spaceAfter=0),
    }


def split_row(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def build_table(rows: list[list[str]], st: dict) -> Table:
    head, body = rows[0], rows[1:]
    data = [[Paragraph(inline(c), st["cellhead"]) for c in head]]
    data += [[Paragraph(inline(c), st["cell"]) for c in r] for r in body]
    t = Table(data, hAlign="LEFT", repeatRows=1)
    t.setStyle(
        TableStyle([
            ("LINEBELOW", (0, 0), (-1, 0), 0.7, PROVED),
            ("LINEBELOW", (0, 1), (-1, -2), 0.3, RULE),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (0, -1), 0),
            ("RIGHTPADDING", (-1, 0), (-1, -1), 0),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, WASH]),
        ])
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
            box.setStyle(TableStyle([
                ("LINEBEFORE", (0, 0), (0, -1), 2.2, AUDITED),
                ("BACKGROUND", (0, 0), (-1, -1), WASH),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]))
            story.append(box)
            story.append(Spacer(1, 7))
            quote = []

    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()

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
            # Non-breaking spaces, because ReportLab collapses runs of ordinary ones and the
            # alignment of these columns is the whole point of showing the working.
            rendered = "<br/>".join(inline(b).replace(" ", " ") for b in block)
            box = Table([[Paragraph(rendered, st["calc"])]], colWidths=[165 * mm], hAlign="LEFT")
            box.setStyle(TableStyle([
                ("LINEBEFORE", (0, 0), (0, -1), 2.2, PROVED),
                ("BACKGROUND", (0, 0), (-1, -1), WASH),
                ("LEFTPADDING", (0, 0), (-1, -1), 11),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ]))
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
            story.append(Spacer(1, 26 * mm))
            story.append(Paragraph(inline(line[2:]), st["title"]))
            story.append(HRFlowable(width="100%", thickness=2, color=PROVED,
                                    spaceBefore=4, spaceAfter=12))
            i += 1
            continue

        # The cover's contents list is built from the section headings themselves, so it can
        # never drift out of step with the document the way a hand-typed one would.
        if line.strip() == "<!--contents-->":
            flush_para()
            story.append(Spacer(1, 8))
            story.append(Paragraph("What is in here", st["h3"]))
            story.append(HRFlowable(width="100%", thickness=0.6, color=RULE,
                                    spaceBefore=2, spaceAfter=7))
            entries = [ln[3:].strip() for ln in lines if ln.startswith("## ")]
            rows = [[Paragraph(inline(e), st["toc"])] for e in entries[1:]]
            toc = Table(rows, colWidths=[120 * mm], hAlign="LEFT")
            toc.setStyle(TableStyle([
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 1.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
            ]))
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
            story.append(HRFlowable(width="100%", thickness=0.6, color=RULE,
                                    spaceBefore=0, spaceAfter=9))
            i += 1
            continue

        if line.startswith("### "):
            flush_para()
            # A heading stranded at the foot of a page reads as a missing section.
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
            story.append(Paragraph(inline(content), st["bullet"], bulletText=bullet))
            i += 1
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
        canvas.drawString(22 * mm, h - 13 * mm, "SYNTHPROOF  ·  EXPLAINER")
        canvas.drawRightString(w - 22 * mm, h - 13 * mm, "EVERY NUMBER TRACES TO A COMMITTED FILE")
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.4)
        canvas.line(22 * mm, h - 15.5 * mm, w - 22 * mm, h - 15.5 * mm)
    canvas.drawCentredString(w / 2, 12 * mm, str(doc.page))
    canvas.restoreState()


def main() -> None:
    register_fonts()
    text = SRC.read_text(encoding="utf-8")

    problems = verify_numbers(text)
    if problems:
        print("REFUSING TO BUILD — the explainer disagrees with the committed results:")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)

    st = styles()
    doc = BaseDocTemplate(
        str(OUT), pagesize=A4,
        leftMargin=22 * mm, rightMargin=22 * mm, topMargin=20 * mm, bottomMargin=18 * mm,
        title="SynthProof, explained from scratch",
        author="SynthProof capstone team",
        subject="A plain-language explainer for presenting and defending the project",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="all", frames=[frame], onPage=decorate)])
    doc.build(render(text, st))

    from pypdf import PdfReader  # type: ignore

    pages = len(PdfReader(str(OUT)).pages)
    print(f"wrote {OUT.relative_to(ROOT)} — {pages} pages, all numbers verified against results/")
    if pages > 20:
        print(f"WARNING: {pages} pages, over the 20-page budget.")


if __name__ == "__main__":
    main()
