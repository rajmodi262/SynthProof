"""Fails if a thesis chapter states something the evidence no longer supports.

WHY THIS EXISTS. Four chapters are still unwritten, and eight claims died on 2026-08-23 when
the novelty protocol in `research/` completed. The realistic failure is not that someone lies
-- it is that someone drafts ch07 or ch08 next week from last month's understanding and writes,
in good faith, a sentence that was true when the outline was made and is false now.

A reviewer would catch it. So would an examiner. This catches it first, in CI, at the moment
the sentence is written.

WHAT IT DOES NOT DO. It cannot check an argument, only a phrase. Passing means "you did not
write one of the known-dead claims", not "this chapter is honest". The judgement is still
yours; this only removes the mistakes we already know the shape of.

Run from the repository root:

    python scripts/check_thesis_claims.py
    python scripts/check_thesis_claims.py docs/thesis/ch08-discussion.md   # one file
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
THESIS = ROOT / "docs" / "thesis"

# Each entry: (label, regex, why it is dead, what to write instead).
# Regexes are deliberately loose -- a false positive costs ten seconds, a false negative
# costs the viva.
DEAD_CLAIMS: list[tuple[str, str, str, str]] = [
    (
        "ceiling-as-ours",
        r"(our|we|this (work|project|thesis))[^.]{0,80}\b(derive|prove|establish|discover|"
        r"contribut)\w*[^.]{0,60}\bceiling\b",
        "The ceiling is a one-line corollary of Steinke, Nasr & Jagielski (2023) Thm 2.1 / "
        "Eq. (3) -- the paper we implement. Verified bit-identical to max_provable_epsilon.",
        "Attribute it to Steinke et al. Ours is the MEASUREMENT of where it bites, not the "
        "inequality.",
    ),
    (
        # "We found no system that ..." is the CORRECT hedge and must not be flagged, or the
        # checker punishes the phrasing it recommends and gets ignored. Only the unhedged
        # existence claim is dead.
        "no-existing-system",
        r"(?<!found )(?<!find )\bno (existing )?(system|tool|work|approach)\b[^.]{0,120}"
        r"\b(both bounds|ships|attach\w*|accompan\w*)",
        "Dual-sided assurance is occupied (Annamalai, Ganev & De Cristofaro, USENIX Sec 2024); "
        "structured privacy labels by Dibia et al. 2025; checkable artefacts by Croissant, "
        "MRM3 and Laminator.",
        "Say what we found, not what exists: 'we found no system that ...', and name the "
        "adjacent work.",
    ),
    (
        "first-to",
        r"\b(we are|this is) the first\b|\bfirst (system|tool|work) to\b",
        "No first-to claim survived the protocol. research/08_novelty_verdict.md lists eight "
        "dead claims and three narrow, unrefuted survivors.",
        "Drop it. A narrow unrefuted claim is defensible; a priority claim is not.",
    ),
    (
        "profiling-novel",
        r"\b(charg\w+|account\w+) (the |for )?(domain|profil)\w*[^.]{0,80}\b(novel|new|"
        r"contribution|first)\b",
        "Published by Ganev, Annamalai, Mahiou & De Cristofaro (arXiv 2504.08254, Apr 2025), "
        "which studies the same three domain strategies.",
        "Our contribution is the checkable `domain_source` FIELD, not the insight.",
    ),
    (
        "refusal-novel",
        r"\b(refus\w+|pre-?flight|gate)\b[^.]{0,80}\b(novel|unique|first|nobody else|no other)\b",
        "Automated release gating is production practice under Five Safes; SACRO has automated "
        "it since 2022. The SDC Handbook could not be retrieved, so our search is incomplete.",
        "State the schema-only difference as UNREFUTED, never as novel.",
    ),
    (
        "audited-gap-as-finding",
        r"\b(eps|epsilon|ε)[_ ]?audited\b[^.]{0,60}\b(0|zero)\b[^.]{0,80}\b(shows?|demonstrat\w+|"
        r"prov\w+|means?)\b",
        "At m = 60 the ceiling is 2.97 against a proved eps of 7.36. The instrument could not "
        "have reported otherwise even against a 100% verbatim release.",
        "Always report the ceiling beside the audited epsilon, and say the gap was "
        "structurally guaranteed.",
    ),
    (
        # A retraction contains the dead phrase by necessity ("NOT cross-release: there is no
        # cross-session enforcement"). Negation within the same clause means the writer already
        # knows, so only the affirmative claim is flagged.
        "cross-release",
        r"(?<!not )(?<!Not )(?<!no )(?<!No )\bcross-?release\b(?![^.]{0,60}\b(not|no|never)\b)"
        r"[^.]{0,80}\b(compos\w+|enforc\w+|support\w+)\b",
        "There is no cross-session budget enforcement -- the README says so, and DPolicy "
        "(arXiv 2505.06747) is the system that does this properly.",
        "Move it to future work and cite DPolicy.",
    ),
    (
        # Citing Carlini et al.'s LiRA as prior work is correct and expected in ch02. What is
        # wrong is presenting it as something WE ran. So this fires only when LiRA sits near a
        # first-person or reporting verb, and not when 'not' follows shortly after.
        "lira-as-ours",
        r"\bLiRA\b(?![^.]{0,60}\bnot\b)(?=[^.]{0,90}\b(we|our|ours|implement\w*|ran|run|"
        r"report\w*|measur\w*|result\w*)\b)"
        r"|\b(we|our|ours|implement\w*|ran|report\w*|measur\w*)\b[^.]{0,90}\bLiRA\b"
        r"(?![^.]{0,60}\bnot\b)",
        "LiRA is deliberately NOT implemented. attacks/distance_mia.py is a nearest-neighbour "
        "baseline and says so; an earlier version was misnamed and reported a fabricated AUC.",
        "Cite LiRA as prior work freely. Only claim it as ours to say it is NOT implemented, "
        "and why (~21h compute for a likely wide-CI null).",
    ),
    (
        # Third rule to need this, so state the pattern once: a document that WARNS against a
        # dead phrase necessarily contains it. Quoting ("append-only") or prohibiting it
        # ("do not call this append-only") is the correct behaviour and must not be flagged.
        # Only the bare assertion is.
        "append-only",
        r"(?<![\"'`])(?<!not call this )(?<!not call the ledger )\bappend-only\b(?![\"'`])",
        "Hash chaining alone does not detect truncation -- a shortened chain is internally "
        "consistent. That is why the signed ledger_head exists.",
        "Say 'hash-chained and signed, with a head committing to (entry_count, tip_hash)'.",
    ),
]

# Phrases that must appear somewhere if the chapter discusses the audit at all.
REQUIRED_WITH_AUDIT: list[tuple[str, str, str]] = [
    (
        r"\b(eps|epsilon|ε)[_ ]?audited\b",
        r"\bceiling\b",
        "This chapter reports an audited epsilon without ever mentioning the ceiling. A zero "
        "with no ceiling beside it is the 'privacy theater' failure Dibia et al.'s experts "
        "warned about.",
    ),
]


def check(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    # Blockquotes are where we deliberately QUOTE dead claims in order to retract them, so
    # they are MASKED rather than removed -- deleting them shifts every line number after the
    # first quote and sends the writer to the wrong line.
    prose = "\n".join("" if ln.lstrip().startswith(">") else ln for ln in text.split("\n"))
    problems: list[str] = []

    for label, pattern, why, instead in DEAD_CLAIMS:
        for m in re.finditer(pattern, prose, re.I):
            line = prose[: m.start()].count("\n") + 1
            problems.append(
                f"{path.name}:{line}  [{label}]  {m.group(0)[:70]!r}\n"
                f"    dead because: {why}\n"
                f"    write instead: {instead}"
            )

    for trigger, required, why in REQUIRED_WITH_AUDIT:
        if re.search(trigger, prose, re.I) and not re.search(required, prose, re.I):
            problems.append(f"{path.name}  [missing-ceiling]\n    {why}")

    return problems


def main() -> None:
    targets = (
        [Path(a) for a in sys.argv[1:]]
        if len(sys.argv) > 1
        else sorted(THESIS.glob("ch0*.md"))
    )
    missing = [p for p in targets if not p.exists()]
    if missing:
        sys.exit(f"no such file: {', '.join(str(m) for m in missing)}")

    problems: list[str] = []
    for p in targets:
        problems.extend(check(p))

    if not problems:
        print(f"OK - {len(targets)} chapter(s) checked, no known-dead claim found.")
        print("     This does not mean the argument is sound. It means you did not write one")
        print("     of the eight claims research/08_novelty_verdict.md already killed.")
        return

    print(f"FOUND {len(problems)} claim(s) the evidence no longer supports:\n")
    for p in problems:
        print(f"  - {p}\n")
    print("Fix the prose, never the check. See docs/thesis/WRITING_NOTICE.md.")
    sys.exit(1)


if __name__ == "__main__":
    main()
