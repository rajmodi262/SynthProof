"""Assembles the eight chapters into one document and renders it to PDF.

WHAT IT ASSEMBLES. `docs/thesis/ch01..ch08` in order, with `ch07-tables.md` spliced into
Chapter 7 -- those tables are thesis content, generated from `results/` so they cannot drift.
The `*-evidence.md` maps are NOT included: they are scaffolding for writing, they contain
`[WRITE: ...]` instructions, and putting them in the submitted document would be a category
error.

WHAT IT REFUSES TO HIDE. The thesis is incomplete, and a build that quietly emitted 8,000 words
as though they were 15,700 would be the same class of dishonesty this project exists to catch.
So the front matter carries a **draft status page**: per-chapter word counts against target,
the shortfall, and every unwritten section named. If a chapter is a stub, the PDF says so on
page two, in a table, before anyone reads a word of it.

It also runs the dead-claim check first and refuses to build on a failure, for the same reason
the explainer and simple-guide builders refuse when their numbers drift.

Run from the repository root:

    python scripts/build_thesis.py
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
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

ROOT = Path(__file__).resolve().parents[1]
THESIS = ROOT / "docs" / "thesis"
MD_OUT = THESIS / "THESIS.md"
PDF_OUT = ROOT.parent / "SynthProof-Thesis.pdf"

TITLE = "SynthProof: Synthetic Data That Ships With Its Proof"
SUBTITLE = (
    "Differentially private synthetic tabular data with a signed, "
    "machine-checkable release certificate"
)
TEAM = ["Raj Modi", "Krishna Renuse", "Aaditya Kumar Sinha", "Levinesh G R"]
INSTITUTION = "MIT-WPU · School of Computer Science and Engineering · CSE-AIDS"
PROGRAMME = "B.Tech Capstone Project 2026-27 · Panel B"

# A section with fewer prose words than this is an outline, not a written section. Chosen so a
# heading plus its one-line "what goes here" note counts as unwritten, while a real short
# subsection does not.
SECTION_WRITTEN_WORDS = 90

# (file stem, chapter title, word target). Targets are the ones written into each stub.
CHAPTERS = [
    ("ch01-introduction", "Introduction", 1500),
    ("ch02-literature-review", "Literature Review", 2500),
    ("ch03-threat-model", "Threat Model and Scope", 1500),
    ("ch04-system-design", "System Design", 2000),
    ("ch05-implementation", "Implementation", 1500),
    ("ch06-methodology", "Methodology", 2500),
    ("ch07-results", "Results and Analysis", 2500),
    ("ch08-discussion", "Discussion and Conclusion", 1700),
]

INK = colors.HexColor("#1B1D24")
SOFT = colors.HexColor("#4C5160")
FAINT = colors.HexColor("#8A8F9E")
ACCENT = colors.HexColor("#4B46C4")
WARN = colors.HexColor("#C2622A")
RULE = colors.HexColor("#D8D6CE")
WASH = colors.HexColor("#F4F3EE")

FONT_DIR = Path("C:/Windows/Fonts")
FACES = {
    "Body": "times.ttf",
    "Body-Bold": "timesbd.ttf",
    "Body-Italic": "timesi.ttf",
    "Body-BoldItalic": "timesbi.ttf",
    "Head": "arialbd.ttf",
    "Head-Regular": "arial.ttf",
    "Mono": "consola.ttf",
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


# ── assembly ───────────────────────────────────────────────────────────────────


def words(text: str) -> int:
    """Word count of prose only -- tables, code and WRITE markers are not written words."""
    out = []
    for line in text.split("\n"):
        s = line.strip()
        if s.startswith("|") or s.startswith("```") or s.startswith("[WRITE:"):
            continue
        out.append(s)
    return len(" ".join(out).split())


def unwritten(text: str, stem: str = "") -> list[str]:
    """What is still to be written, as an instruction a person can act on.

    Two sources, because the chapters are in two states. Chapters with generated companions
    carry explicit `[WRITE: ...]` markers; the stub chapters carry an outline instead, so
    their `##` headings are what remains. Listing "~250 words" -- the budget clause the
    marker opens with -- tells the writer nothing, so it is stripped and the instruction
    that follows is kept.
    """
    found = []
    for m in re.finditer(r"\[WRITE:\s*(.+?)\]", text, re.S):
        body = " ".join(m.group(1).split())
        budget = re.match(r"^~?[\d,]+\s*words\.\s*", body)
        if budget:
            body = body[budget.end():]
        found.append(body[:150].rstrip() + ("..." if len(body) > 150 else ""))
    if found or not stem:
        return found

    # No markers, so fall back to per-section word counts. Listing EVERY heading was wrong:
    # it reported ch02 (2,333 words, drafted) as entirely unwritten. Only sections whose own
    # prose is below the threshold are outstanding.
    src = (THESIS / f"{stem}.md").read_text(encoding="utf-8")
    skip = ("Discipline", "Figures", "Writing note", "Sources to obtain", "Sources")
    sections: list[tuple[str, list[str]]] = []
    for line in src.split("\n"):
        if line.startswith("## "):
            sections.append((" ".join(line[3:].split()), []))
        elif sections:
            sections[-1][1].append(line)

    thin = []
    for heading, lines in sections:
        if any(s in heading for s in skip):
            continue
        if words("\n".join(lines)) < SECTION_WRITTEN_WORDS:
            thin.append(heading)
    return thin


def chapter_text(stem: str) -> str:
    """Chapter body, with the generated tables spliced in where a companion exists."""
    body = (THESIS / f"{stem}.md").read_text(encoding="utf-8")
    companion = THESIS / f"{stem.split('-')[0]}-tables.md"
    if companion.exists():
        tables = companion.read_text(encoding="utf-8")
        # Drop the companion's own H1 and its do-not-edit banner; keep the sections.
        tables = re.sub(r"\A#[^\n]*\n", "", tables)
        tables = re.sub(r"^>.*$", "", tables, flags=re.M)
        body = body.rstrip() + "\n\n" + tables.strip() + "\n"
    return body


def status_rows() -> tuple[list[list[str]], int, int]:
    rows = [["Chapter", "Words", "Target", "Status"]]
    total = target_total = 0
    for stem, title, target in CHAPTERS:
        text = (THESIS / f"{stem}.md").read_text(encoding="utf-8")
        n = words(text)
        total += n
        target_total += target
        if n >= target * 0.9:
            state = "drafted"
        elif n >= target * 0.4:
            state = "PARTIAL"
        else:
            state = "STUB — not written"
        rows.append([title, f"{n:,}", f"{target:,}", state])
    rows.append(["**Total**", f"**{total:,}**", f"**{target_total:,}**",
                 f"**{total / target_total:.0%} of target**"])
    return rows, total, target_total


def assemble() -> str:
    parts: list[str] = []
    for stem, title, _t in CHAPTERS:
        num = stem[2:4].lstrip("0")
        text = chapter_text(stem)
        # Normalise the chapter heading so numbering is consistent in the PDF.
        text = re.sub(r"\A#\s+.*$", f"# Chapter {num} — {title}", text, count=1, flags=re.M)
        parts.append(text.rstrip())
    return "\n\n".join(parts) + "\n"


# ── markdown → flowables ───────────────────────────────────────────────────────

INLINE = [
    (re.compile(r"\*\*(.+?)\*\*"), r"<b>\1</b>"),
    (re.compile(r"(?<!\w)\*(?!\s)(.+?)(?<!\s)\*(?!\w)"), r"<i>\1</i>"),
    (re.compile(r"`(.+?)`"), r'<font name="Mono" size="8.6">\1</font>'),
]


def inline(s: str) -> str:
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    for pattern, repl in INLINE:
        s = pattern.sub(repl, s)
    return s


def styles() -> dict[str, ParagraphStyle]:
    base = ParagraphStyle(
        "body", fontName="Body", fontSize=10.6, leading=15.4, textColor=INK,
        alignment=TA_LEFT, spaceAfter=7,
    )
    return {
        "body": base,
        "chapter": ParagraphStyle("chapter", parent=base, fontName="Head", fontSize=21,
                                  leading=25, textColor=INK, spaceBefore=0, spaceAfter=10),
        "h2": ParagraphStyle("h2", parent=base, fontName="Head", fontSize=13.5, leading=17,
                             textColor=ACCENT, spaceBefore=13, spaceAfter=6),
        "h3": ParagraphStyle("h3", parent=base, fontName="Head", fontSize=11, leading=14,
                             textColor=INK, spaceBefore=10, spaceAfter=4),
        "bullet": ParagraphStyle("bullet", parent=base, leftIndent=13, bulletIndent=3,
                                 spaceAfter=4),
        "quote": ParagraphStyle("quote", parent=base, fontSize=10.2, leading=14.4,
                                leftIndent=9, rightIndent=6, spaceBefore=3, spaceAfter=3),
        "todo": ParagraphStyle("todo", parent=base, fontName="Head-Regular", fontSize=9.4,
                               leading=13, textColor=WARN, leftIndent=9, spaceAfter=4),
        "cellhead": ParagraphStyle("cellhead", parent=base, fontName="Head-Regular",
                                   fontSize=8.2, leading=10.8, textColor=SOFT, spaceAfter=0),
        "cell": ParagraphStyle("cell", parent=base, fontSize=8.9, leading=11.8, spaceAfter=0),
        "mono": ParagraphStyle("mono", parent=base, fontName="Mono", fontSize=8.6,
                               leading=13, spaceAfter=0),
        "title": ParagraphStyle("title", parent=base, fontName="Head", fontSize=25, leading=30,
                                alignment=TA_CENTER, spaceAfter=10),
        "sub": ParagraphStyle("sub", parent=base, fontSize=12.4, leading=17,
                              alignment=TA_CENTER, textColor=SOFT, spaceAfter=8),
        "centre": ParagraphStyle("centre", parent=base, alignment=TA_CENTER, spaceAfter=4),
    }


def build_table(rows: list[list[str]], st: dict) -> Table:
    head, body = rows[0], rows[1:]
    data = [[Paragraph(inline(c), st["cellhead"]) for c in head]]
    data += [[Paragraph(inline(c), st["cell"]) for c in r] for r in body]
    t = Table(data, hAlign="LEFT", repeatRows=1)
    t.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, 0), 0.7, ACCENT),
        ("LINEBELOW", (0, 1), (-1, -2), 0.3, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("LEFTPADDING", (0, 0), (0, -1), 0),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, WASH]),
    ]))
    return t


def render(text: str, st: dict) -> list:
    story: list = []
    lines = text.split("\n")
    i = 0
    para: list[str] = []
    first_chapter = True

    def flush() -> None:
        nonlocal para
        if para:
            story.append(Paragraph(inline(" ".join(para)), st["body"]))
            para = []

    while i < len(lines):
        line = lines[i].rstrip()

        if not line.strip():
            flush()
            i += 1
            continue

        if line.startswith("# "):
            flush()
            if not first_chapter:
                story.append(PageBreak())
            first_chapter = False
            story.append(Paragraph(inline(line[2:]), st["chapter"]))
            story.append(HRFlowable(width="100%", thickness=1.6, color=ACCENT,
                                    spaceBefore=2, spaceAfter=12))
            i += 1
            continue

        if line.startswith("## "):
            flush()
            story.append(KeepTogether([Paragraph(inline(line[3:]), st["h2"])]))
            i += 1
            continue

        if line.startswith("### "):
            flush()
            story.append(KeepTogether([Paragraph(inline(line[4:]), st["h3"])]))
            i += 1
            continue

        # An unwritten section is rendered as a visible marker, never silently dropped.
        if line.startswith("[WRITE:"):
            flush()
            block = line
            while "]" not in block and i + 1 < len(lines):
                i += 1
                block += " " + lines[i].strip()
            story.append(Paragraph("NOT YET WRITTEN — " + inline(block[7:].rstrip("]").strip()),
                                   st["todo"]))
            i += 1
            continue

        if line.startswith("```"):
            flush()
            i += 1
            block = []
            while i < len(lines) and not lines[i].startswith("```"):
                block.append(lines[i])
                i += 1
            i += 1
            rendered = "<br/>".join(inline(b).replace(" ", "\u00a0") for b in block)
            box = Table([[Paragraph(rendered, st["mono"])]], colWidths=[160 * mm], hAlign="LEFT")
            box.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), WASH),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]))
            story.append(box)
            story.append(Spacer(1, 7))
            continue

        if line.startswith("|"):
            flush()
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(set(c) <= set("-: ") for c in cells):
                    rows.append(cells)
                i += 1
            if rows:
                story.append(build_table(rows, st))
                story.append(Spacer(1, 8))
            continue

        if line.startswith("> "):
            flush()
            story.append(Paragraph(inline(line[2:]), st["quote"]))
            i += 1
            continue

        if line.strip() in ("---", "***"):
            flush()
            i += 1
            continue

        if line.startswith("- ") or re.match(r"^\d+\. ", line):
            flush()
            if line.startswith("- "):
                bullet, content = "\u2013", line[2:]
            else:
                num, content = line.split(". ", 1)
                bullet = f"{num}."
            i += 1
            while i < len(lines) and lines[i].startswith("  ") and lines[i].strip():
                content += " " + lines[i].strip()
                i += 1
            story.append(Paragraph(inline(content), st["bullet"], bulletText=bullet))
            continue

        para.append(line.strip())
        i += 1

    flush()
    return story


def front_matter(st: dict, total: int, target_total: int, todos: list[tuple[str, list[str]]]):
    story = [Spacer(1, 38 * mm), Paragraph(TITLE, st["title"]),
             Paragraph(SUBTITLE, st["sub"]),
             HRFlowable(width="55%", thickness=1.2, color=ACCENT, spaceBefore=8, spaceAfter=16)]
    for name in TEAM:
        story.append(Paragraph(name, st["centre"]))
    story += [Spacer(1, 8), Paragraph(INSTITUTION, st["sub"]),
              Paragraph(PROGRAMME, st["sub"]), PageBreak()]

    story.append(Paragraph("Draft status", st["chapter"]))
    story.append(HRFlowable(width="100%", thickness=1.6, color=ACCENT,
                            spaceBefore=2, spaceAfter=12))
    story.append(Paragraph(
        "This document is <b>incomplete</b> and this page says so before anything else. "
        "Word counts below are prose only — generated tables and unwritten-section markers are "
        "excluded, so the figure is what has actually been written rather than what the file "
        "contains.", st["body"]))
    rows, _t, _tt = status_rows()
    story.append(build_table(rows, st))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        f"<b>{target_total - total:,} words remain.</b> Every unwritten section is listed "
        "below and appears again, in place, in the body of the document.", st["body"]))

    for title, items in todos:
        if not items:
            continue
        story.append(Paragraph(title, st["h3"]))
        for it in items:
            story.append(Paragraph(inline(it), st["todo"], bulletText="–"))
    story.append(PageBreak())
    return story


def decorate(canvas, doc) -> None:
    canvas.saveState()
    w, h = A4
    canvas.setFont("Head-Regular", 7.4)
    canvas.setFillColor(FAINT)
    if doc.page > 1:
        canvas.drawString(22 * mm, h - 13 * mm, "SYNTHPROOF  ·  CAPSTONE THESIS  ·  DRAFT")
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.4)
        canvas.line(22 * mm, h - 15.5 * mm, w - 22 * mm, h - 15.5 * mm)
        canvas.drawCentredString(w / 2, 12 * mm, str(doc.page))
    canvas.restoreState()


def main() -> None:
    # Same discipline as the other builders: refuse to render a known-dead claim.
    check = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_thesis_claims.py")],
        capture_output=True, text=True,
    )
    if check.returncode != 0:
        blocking = [ln for ln in check.stdout.split("\n") if "missing-ceiling" not in ln]
        if any(ln.strip().startswith("- ") for ln in blocking):
            print("REFUSING TO BUILD — a chapter states a claim the evidence no longer supports:")
            print(check.stdout)
            sys.exit(1)
        print("note: only 'missing-ceiling' to-dos outstanding; continuing.\n")

    register_fonts()
    body = assemble()
    MD_OUT.write_text(body, encoding="utf-8")

    rows, total, target_total = status_rows()
    todos = [
        (f"Chapter {stem[2:4].lstrip('0')} — {title}", unwritten(chapter_text(stem), stem))
        for stem, title, _t in CHAPTERS
    ]

    st = styles()
    tmp = PDF_OUT.with_suffix(".building.pdf")
    doc = BaseDocTemplate(
        str(tmp), pagesize=A4,
        leftMargin=24 * mm, rightMargin=24 * mm, topMargin=22 * mm, bottomMargin=20 * mm,
        title=TITLE, author=", ".join(TEAM), subject=SUBTITLE,
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="all", frames=[frame], onPage=decorate)])
    doc.build(front_matter(st, total, target_total, todos) + render(body, st))

    from pypdf import PdfReader  # type: ignore

    pages = len(PdfReader(str(tmp)).pages)
    try:
        os.replace(tmp, PDF_OUT)
    except PermissionError:
        sys.exit(
            f"Could not write {PDF_OUT.name} — it is open in another program. Close the viewer "
            f"and run this again. (The freshly built copy is at {tmp}.)"
        )

    n_todo = sum(len(t) for _title, t in todos)
    print(f"wrote {MD_OUT.relative_to(ROOT)}")
    print(f"wrote {PDF_OUT}")
    print(f"  {pages} pages · {total:,} of {target_total:,} words written "
          f"({total / target_total:.0%}) · {n_todo} sections still to write")


if __name__ == "__main__":
    main()
