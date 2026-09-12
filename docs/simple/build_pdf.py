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
SRC = Path(__file__).resolve().parent / "SIMPLE.md"
# The outermost folder, alongside the decks, so it is easy to find and share.
OUT = ROOT.parent / "SynthProof-Simple-Guide.pdf"

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
    """Checks the few properties this guide relies on.

    Unlike the results explainer, this document deliberately quotes no measurements — it
    describes the design and the plan, so there is nothing to drift against the JSON. What it
    DOES rely on is arithmetic the reader is invited to check by hand, and the promise that
    every section a presenter is told to study actually exists. Both are worth asserting.
    """
    problems: list[str] = []

    # The coin-flip worked example on page ~4. If any of these stop reconciling, the reader
    # following along with a calculator will catch it before the panel does.
    cheat, total, p_yes_cheat, p_yes_clean = 300, 1000, 0.75, 0.25
    observed = cheat * p_yes_cheat + (total - cheat) * p_yes_clean
    if observed != 400:
        problems.append(f"coin-flip example: expected 400 yeses, arithmetic gives {observed}")
    recovered = (observed - p_yes_clean * total) / (p_yes_cheat - p_yes_clean)
    if round(recovered) != cheat:
        problems.append(f"coin-flip example: recovery gives {recovered}, not {cheat}")

    # The re-identification funnel on page ~3.
    v = 100_000
    for bucket in (15, 12, 31, 60):
        v /= bucket
    if not (0.2 < v < 0.4):
        problems.append(f"re-identification funnel ends at {v:.2f}, prose says about 0.3")

    # Sections the cheat sheet and the intro send the reader to.
    for needed in ("## 13.", "## 14.", "## 6.", "## 8."):
        if needed not in text:
            problems.append(f"missing section {needed} that the guide tells the reader to study")

    # The headline promise of the document.
    n_questions = len(re.findall(r"^\*\*\d+\. ", text, flags=re.M))
    if n_questions < 100:
        problems.append(f"only {n_questions} numbered questions; the guide promises at least 100")

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
            # A list item may be soft-wrapped across several source lines with the
            # continuation indented. Without this the continuation fell through to the
            # ordinary-paragraph branch and rendered flush against the left margin,
            # visually detached from its own bullet.
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
        canvas.drawString(22 * mm, h - 13 * mm, "SYNTHPROOF  ·  SIMPLE GUIDE")
        canvas.drawRightString(w - 22 * mm, h - 13 * mm, "READ PART 3 TWICE")
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
    tmp = OUT.with_suffix(".building.pdf")
    doc = BaseDocTemplate(
        str(tmp), pagesize=A4,
        leftMargin=22 * mm, rightMargin=22 * mm, topMargin=20 * mm, bottomMargin=18 * mm,
        title="SynthProof — the simple guide",
        author="SynthProof capstone team",
        subject="A from-zero explanation plus 120 questions a panel might ask",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="all", frames=[frame], onPage=decorate)])
    doc.build(render(text, st))

    # Windows refuses to overwrite a PDF that is open in a viewer, and the failure lands
    # halfway through with a stack trace and no output. Building to a temp file first means a
    # locked target costs nothing and produces a message a human can act on.
    try:
        os.replace(tmp, OUT)
    except PermissionError:
        msg = (
            f"Could not write {OUT.name} - it is open in another program. "
            f"Close the PDF viewer and run this again. "
            f"(The freshly built copy is at {tmp}.)"
        )
        sys.exit(msg)

    from pypdf import PdfReader  # type: ignore

    pages = len(PdfReader(str(OUT)).pages)
    print(f"wrote {OUT}")
    print(f"  {pages} pages")


if __name__ == "__main__":
    main()
