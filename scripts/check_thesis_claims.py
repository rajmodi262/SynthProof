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
        # Two narrowings, both for false positives the 2026-09-13 repo-wide sweep exposed, and
        # neither weakening a true detection -- "we derive the ceiling" is still caught:
        #   \b before the alternation. Without it "four" matched "our", so "the four synopsis
        #     contributions locked" tripped the rule.
        #   [^.\n] rather than [^.]. A claim is a sentence, not a span reaching across a line
        #     break into an unrelated one. The same false positive joined "our" in one question
        #     to a COMPUTE ceiling -- a hardware budget -- in another.
        r"\b(our|we|this (work|project|thesis))[^.\n]{0,80}\b(derive|prove|establish|discover|"
        r"contribut)\w*[^.\n]{0,60}\bceiling\b",
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
        # `first(?!-class)` -- "charged domain discovery as a FIRST-CLASS mode" in
        # docs/design/USER_FACING_SYSTEM.md is a design term for a supported top-level
        # feature, not a priority claim. No real claim is weakened by excluding the
        # compound, and leaving it in produced a report no writer could act on.
        r"\b(charg\w+|account\w+) (the |for )?(domain|profil)\w*[^.]{0,80}\b(novel|new|"
        r"contribution|first(?!-class))\b",
        "Published by Ganev, Annamalai, Mahiou & De Cristofaro (arXiv 2504.08254, Apr 2025), "
        "which studies the same three domain strategies.",
        "Our contribution is the checkable `domain_source` FIELD, not the insight.",
    ),
    (
        "refusal-novel",
        # Same exclusion as profiling-novel: "refusal as a first-class outcome" is a
        # design term, not a claim to have been first.
        r"\b(refus\w+|pre-?flight|gate)\b[^.]{0,80}"
        r"\b(novel|unique|first(?!-class)|nobody else|no other)\b",
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
    # ---- added 2026-08-25, after three more claims died in one day -----------------------
    # NOTE ON THE GAPS. These use `[^\n]` rather than `[^.]`. A dot-excluding gap cannot cross
    # "et al." or a decimal, and these sentences are full of both -- written with `[^.]` all
    # three rules matched nothing and gave false confidence. Verified against known-bad text.
    (
        "clique-confound-as-finding",
        # Two shapes, because the first-person form turned out to be only half of it. On
        # 2026-09-12 results/RESULTS.md -- the first file anyone opens to see what this
        # project found -- still listed the retracted confound with a star and the words
        # "The strongest result here", and sailed straight through: no "we", no "found",
        # just a table row. A gate that passes the headline document is worse than the
        # sentence it missed, because the team has stopped reading that document itself and
        # is trusting the gate instead. The second and third alternatives catch the bare
        # assertion, in either order.
        r"(?:we|our|this (?:work|project|thesis))[^\n]{0,100}"
        r"(?:find|found|show|showed|demonstrat\w*|discover\w*|reveal\w*|establish\w*)"
        r"[^\n]{0,100}(?:clique[- ]selection|selection[- ]confound)"
        r"|(?:clique[- ]selection|selection[- ]confound)[^\n]{0,140}?"
        r"(?:⭐|strongest|headline|key (?:result|finding)|our (?:result|finding|contribution))"
        r"|(?:⭐|strongest|headline|key (?:result|finding))[^\n]{0,140}?"
        r"(?:clique[- ]selection|selection[- ]confound)",
        "RETRACTED 2026-08-25. Published three times -- AIM's own paper (arXiv:2201.12677 S5) "
        "partitions supported/unsupported marginals with separate bounds and Fig 2c; Ganev, Xu "
        "& De Cristofaro CCS 2024 S5.3; Chen, Gong & Wang arXiv:2511.13893 S6.3. And our own "
        "ablation refuted the reading: measuring helps in proportion to TRUE DEPENDENCE "
        "(r = -0.898), so AIM's advantage is the mechanism working as designed.",
        "Cite the three papers and present the fixed-workload ablation as a REPLICATION with a "
        "selection-deleted control arm. See results/SELECTION_ABLATION.md.",
    ),
    (
        "measuring-hurts-as-finding",
        r"(?:we|our|this (?:work|project|thesis))[^\n]{0,100}"
        r"(?:find|found|show|showed|demonstrat\w*|discover\w*|new result)"
        r"[^\n]{0,140}measur\w+[^\n]{0,80}(?:worse|harm\w*|degrad\w*|hurts?)",
        "RETRACTED 2026-08-25. PrivSyn (arXiv:2012.15128) S3.2 states it verbatim: 'When some "
        "attributes are independent, capturing the relationship among them actually increases "
        "the amount of noise.' S4.2 formalises the select-or-omit tradeoff with "
        "InDif = |M_ab - M_a x M_b|_1. AIM Eq. (1) encodes the same rule and lets it go negative.",
        "Cite PrivSyn and AIM Eq. (1). Ours is a CALIBRATION of where the crossover falls, for "
        "a validation-methodology chapter -- never a discovery.",
    ),
    (
        "ganev-as-one-run-full-aim",
        # Proximity is not a claim. The 140-char gap crossed sentence boundaries and
        # flagged a topic list, a heading, and a citation of Mahloujifar et al. for the
        # f-DP one-run idea -- none of which say Ganev's audit is one-run. A verb of
        # assertion has to sit immediately before the phrase.
        r"(?:2604\.18352|Ganev)[^\n]{0,140}?"
        r"\b(?:is|are|was|were|use[sd]?|using|obtain\w*|perform\w*|report\w*|"
        r"give[sn]?|provide[sd]?|a|an|their)\s+(?:a\s+)?"
        r"(?:tight\s+|genuine\s+|true\s+)?one[- ]run\b",
        "Their audit is NOT one-run: 10,000 independent models, 5,000 per world, one target "
        "record on an 11-record worst-case dataset. It also audits a RESTRICTED configuration "
        "(fixed dependency graph, one-way marginals only), so AIM reduces to independent "
        "marginals -- it is not a tight audit of AIM as deployed.",
        "Describe it as a many-run worst-case GDP audit of a restricted configuration.",
    ),
    # ---------------------------------------------------------------- added 2026-09-06
    # Nine more died during the novelty protocol's second pass. Each has a fetched citation.
    (
        "complete-case-as-ours",
        r"(we|our|this (work|thesis))[^.]{0,90}\b(first|show|demonstrat|measur|discover)\w*"
        r"[^.]{0,90}\b(complete[- ]case|listwise|incomplete rows|dropna)\b",
        "FairPrep (Schelter, He, Khilnani & Stoyanovich, arXiv:1911.12587, 2019) S5.3 already "
        "reports 24% vs 14% high-income between complete and incomplete records ON UCI ADULT -- "
        "the same quantities we measured -- and S2.4 already names silent deletion as an "
        "evaluation-instrument shortcoming. Mohapatra et al. (PVLDB 17(8) 2024) already evaluate "
        "against the UN-deleted ground truth and measure the damage for five DP synthesizers.",
        "Do not claim it. If the topic is discussed at all, cite FairPrep and Mohapatra as prior "
        "statements of the defect.",
    ),
    (
        "folktables-defect-as-ours",
        r"(we|our)[^.]{0,80}\b(found|discover|identif|report)\w*[^.]{0,80}"
        r"\b(folktables|nan_to_num|sentinel)\b",
        "The folktables np.nan_to_num argument-position defect is GitHub issue #39 on "
        "socialfoundations/folktables, open since 2024-01-04.",
        "Cite the issue. It is prior art, not a finding.",
    ),
    (
        "selection-deleted-as-ours",
        r"(we|our)[^.]{0,80}\b(contribut|introduc|propose|first)\w*[^.]{0,90}"
        r"\b(selection[- ]deleted|fixed[- ]workload|deleting the selection)\b",
        "Asiaee & Aryan (arXiv:2607.08122, Jul 2026) run exactly this design -- fixed arm "
        "measures all m coordinates once, same epsilon, same Private-PGM reconstruction, as a "
        "named Algorithm 2. AND OpenDP SmartNoise's MWEM ships a documented `measure_only` "
        "parameter that deletes the selection spend, with the comparison already in its docs.",
        "Present the fixed_workload arm as experimental hygiene and a replication, never as a "
        "contribution.",
    ),
    (
        "signature-attack-as-ours",
        r"(we|our)[^.]{0,80}\b(first|discover|identif|new)\w*[^.]{0,110}"
        r"\b(signed (but|and still)|signature valid|mirrored field)\b",
        "This is XML Signature Wrapping ported to JSON-LD -- a known attack class since "
        "McIntosh & Austel 2005 -- and has a 2026 CVE in this exact shape (CVE-2026-42462, "
        "Fedify, 2026-05-20).",
        "Cite XSW and the CVE. What we did is implement the mirrored-field cross-check for DP "
        "privacy metadata; that is engineering, not discovery.",
    ),
    (
        "gdp-auditing-as-ours",
        r"(we|our)[^.]{0,80}\b(propose|introduc|contribut|first|develop)\w*[^.]{0,90}"
        r"\b(GDP|f-DP|Gaussian[- ]DP)\b[^.]{0,60}\baudit",
        "Ganev, Annamalai & Kulynych (arXiv:2604.18352, TPDP 2026) published GDP/f-DP tradeoff "
        "auditing of MST and AIM -- our headline mechanism -- with public code.",
        "results/GDP_AUDIT.md already frames our run as a replication. Keep it that way.",
    ),
    (
        "amplification-audit-as-first",
        r"(we|our)[^.]{0,60}\bfirst\b[^.]{0,110}\baudit\w*[^.]{0,60}\bamplification\b",
        "Annamalai, Balle, Hayes & De Cristofaro (arXiv:2411.10614, NDSS 2026) already audit an "
        "amplification credit applied under an assumption that does not hold, and report the "
        "audited bound violating the amplified one (up to 4x, 10x for variants).",
        "If this line is pursued at all it is a TRANSFER to a new amplification source, stated "
        "as such.",
    ),
    (
        "canary-contamination-as-first",
        r"(we|our)[^.]{0,70}\bfirst\b[^.]{0,110}\bcanar\w+[^.]{0,80}"
        r"\b(destroy|degrad|contaminat|damag)\w*",
        "Panda et al. (arXiv:2503.06808) measure canary-induced perplexity cost; Mitchell et al. "
        "(arXiv:2606.10481) measure held-out-loss and MAUVE damage, describe diffuse "
        "contamination in S4, AND already recommend the two-fit split in S3.",
        "The residue is narrow: WHICH statistic it lands on in tabular DP synthesis, and that "
        "the damage is mechanism-DIFFERENTIAL. Never the phenomenon, never the remedy.",
    ),
    (
        "two-fit-split-as-ours",
        r"(we|our)[^.]{0,80}\b(propose|introduc|devis|contribut)\w*[^.]{0,90}"
        r"\b(two[- ]fit|separate fit|second fit|fit twice)\b",
        "Mitchell et al. (arXiv:2606.10481) S3, verbatim: 'In some applications it may not be "
        "prohibitive to train two models with identical hyper parameters, one with canaries "
        "inserted just for auditing.'",
        "Say we QUANTIFY a separation Mitchell et al. recommend. They assert it qualitatively; "
        "we measured 58% at eps=8.",
    ),
    (
        "evaluation-bias-direction-as-ours",
        r"(we|our)[^.]{0,90}\b(show|first|discover|find)\w*[^.]{0,110}"
        r"\b(simpler|less dependence|independence)\b[^.]{0,70}\b(favou?r|bias)",
        "DPBench (Hay et al., SIGMOD 2016, arXiv:1512.04817) S8 already states that complex "
        "data-dependent algorithms lose to simple data-independent ones in a describable regime, "
        "and already resolves an inverted published ranking via an unreported evaluation choice.",
        "DPBench attributes the direction to a real signal-to-noise regime. Any claim here must "
        "distinguish CONTAMINATION OF THE APPARATUS from that, with a matched-regime control.",
    ),
    (
        "canary-89-percent",
        # The percentage is only a dead claim IN CANARY CONTEXT. A bare `\b89\s?%` flagged
        # REPORTS/00-MASTER-REPORT.md lines 70 and 78, which report that 8 of 73 surveyed
        # papers used a DP generator and "the other 89% have no formal guarantee" -- true,
        # unrelated, and unfixable by writing. A checker that reports problems a writer
        # cannot fix is one that gets ignored, and the temptation is then to edit correct
        # prose to appease it. So the percentage now requires canary/contamination/signal
        # language within ~90 characters on the same line, either side of the match.
        # 0.0109 stays unconditional: that value is specific to this measurement.
        # Written as two directional alternatives rather than a lookbehind, because Python's
        # `re` has no variable-length lookbehind. The keyword may sit either side of the
        # number, so the match simply spans from one to the other; `m.group(0)` is truncated
        # to 70 characters when reported, and the extra context is an improvement anyway.
        r"\b0\.0109\b"
        r"|(?<![\d.])89\s?%[^\n]{0,90}?\b(?:canar|contaminat|signal|corr\()"
        r"|\b(?:canar|contaminat|signal)\w*[^\n]{0,90}?(?<![\d.])89\s?%",
        "The 89% canary-contamination figure DOES NOT REPLICATE. Over 40 seeds the real "
        "CanaryAuditor at the configuration it was recorded for (Adult, n=6,000, m=60) destroys "
        "about 4.5%, and the effect is not significant there (t=1.85). At 8 seeds the same cells "
        "read roughly twice what they read at 40 -- it was never a stable measurement. See "
        "results/CANARY_DOSE_RESPONSE.md.",
        "Report the SHAPE, not a number: contamination scales with canary FRACTION m/(n+m), is "
        "significant only above ~3%, and depends strongly on canary design. The two-fit decision "
        "still stands on its own, and Mitchell et al. arXiv:2606.10481 S3 recommend it anyway.",
    ),
]

# Phrases that must appear somewhere if the chapter discusses the audit at all.
# (label, trigger, required, why). The label matters: three rules reporting under one name
# leaves a writer unable to tell which fix is being asked for.
REQUIRED_WITH_AUDIT: list[tuple[str, str, str, str]] = [
    (
        "missing-ceiling",
        r"\b(eps|epsilon|ε)[_ ]?audited\b",
        r"\bceiling\b",
        "This chapter reports an audited epsilon without ever mentioning the ceiling. A zero "
        "with no ceiling beside it is the 'privacy theater' failure Dibia et al.'s experts "
        "warned about.",
    ),
    # Added 2026-09-06. The ceiling-as-a-reported-field claim is a TRANSFER of limit-of-detection
    # reporting. An examiner with any lab-science background will say "this is just LoD" -- and
    # if we have not said it first, the claim reads as an undone literature search and dies on
    # the spot. So the attribution is required wherever the claim is made.
    (
        "missing-lod-transfer",
        r"\b(audit[_ ]?ceiling|operating range|maximum auditable)\b",
        r"\b(MIQE|limit of detection|LoD|LLOQ)\b",
        "This chapter claims the ceiling as a reported field without citing the convention it "
        "transfers. MIQE 2.0 (Bustin et al., Clinical Chemistry 2025;71(6):634-651) mandates "
        "LoD/LLOQ reporting; analytical labs report 'Not Detected, < LOD'. Cite it OURSELVES.",
    ),
    (
        "missing-ceiling-attribution",
        r"\b(audit[_ ]?ceiling|operating range)\b",
        r"\b(Steinke|maximum auditable|Annamalai)\b",
        "This chapter discusses the ceiling without attributing it. It is a corollary of Steinke "
        "et al. Thm 2.1, and the concept is already NAMED 'maximum auditable epsilon' by "
        "Annamalai, Ganev & De Cristofaro (arXiv:2405.10994) S2.2. Citing only Steinke is "
        "insufficient -- that paper is one we already cite, and an examiner who opens it will "
        "find our framing there under a different name.",
    ),
]


# A document that WARNS against a dead claim necessarily contains it. Four rules needed this
# guard before it was worth generalising -- "we found no system", "NOT cross-release",
# 'do not call this "append-only"', and "unrefuted rather than novel". Rather than bolt a
# lookbehind onto each pattern, any match whose immediate neighbourhood carries a negation or
# prohibition marker is dropped. False negatives here are cheap: a writer who types "not novel"
# already knows.
_HEDGE = re.compile(
    # "retracted", "refuted" and "superseded" belong here for exactly the reason the rest do:
    # a document that RETRACTS a claim necessarily restates it. Their absence meant a properly
    # written retraction tripped the very rule that had asked for it, and the writer's only
    # way out was to describe the retraction more vaguely -- the opposite of the intent.
    r"\b(not|never|no longer|rather than|instead of|unrefuted|avoid|do not|don't|"
    r"must not|cannot|stop claiming|dead|killed|occupied|retract\w*|refut\w*|superseded)\b",
    re.I,
)
_HEDGE_WINDOW = 60


def _is_hedged(text: str, start: int, end: int) -> bool:
    """True if a negation sits close enough to be governing this match.

    The window spans the match itself as well as its neighbourhood: a loose pattern often
    swallows the very words that negate it, as in "the refusal gate is *unrefuted* rather
    than novel" -- where both hedges fall inside the matched span.
    """
    window = text[max(0, start - _HEDGE_WINDOW) : end + _HEDGE_WINDOW]
    if _HEDGE.search(window):
        return True
    # A long match can carry its own refutation further away than the window reaches. Where a
    # rule allows a gap of 100+ characters the match may span most of a line, and the negation
    # that governs it sits at the start of that line -- as in "It is NOT a one-run audit ...",
    # which then quotes the description it is refuting. For those, consider the whole line.
    if end - start > _HEDGE_WINDOW:
        return bool(_HEDGE.search(_line_of(text, start)))
    return False


def _line_of(text: str, pos: int) -> str:
    """The whole line containing `pos`. Context the regexes cannot see for themselves."""
    lo = text.rfind("\n", 0, pos) + 1
    hi = text.find("\n", pos)
    return text[lo:] if hi == -1 else text[lo:hi]


def _is_not_an_assertion(text: str, start: int, end: int) -> bool:
    """True when the match is on a line that cannot be asserting the claim.

    Three shapes, all of which produced unfixable false positives on 2026-09-12 -- reports a
    writer could only silence by making a true document vaguer, which is the failure mode that
    teaches people to stop trusting the gate.

      QUESTIONS.  docs/defence/DEFENCE.md is a Q&A document. Its headings are the panel's
        questions, and the answer underneath is what refutes them. "Isn't your refusal gate
        novel?" was flagged as claiming the refusal gate is novel; the paragraph below it says
        the opposite. A question states a claim in order to answer it.

      QUOTED DEAD CLAIMS.  docs/thesis/WRITING_NOTICE.md exists to LIST the killed claims so a
        writer recognises them. It quotes each one. The `append-only` rule already carried its
        own quote lookarounds; every other rule lacked them, so the notice permanently tripped
        the rules it was documenting.

      BIBLIOGRAPHY ROWS.  A reference-list entry naming a paper is a citation, not a claim of
        authorship -- and the LiRA rule's own guidance says to cite LiRA as prior work freely.
    """
    line = _line_of(text, start)
    stripped = line.strip()
    match = text[start:end]

    # A question states a claim in order to answer it. Headings in the defence pack carry
    # Markdown emphasis, so "**4a. Isn't your refusal gate novel?**" has to count as one.
    if stripped.rstrip("*_` ").endswith("?"):
        return True

    # The match sits inside quotation marks: it is being named, not asserted.
    #
    # Split rather than pair with a regex. `"[^"]{0,200}?"` under finditer drifts on a line
    # carrying several quoted spans -- one span on line 369 of the deep survey runs past 200
    # characters, so it never pairs and every pairing after it is off by one. Splitting on the
    # delimiter cannot drift: in a balanced line the odd-indexed segments are the quoted ones.
    needle = match.lower()
    for delim in (chr(34), chr(96)):
        segments = line.split(delim)
        if len(segments) > 2:
            if any(needle in seg.lower() for seg in segments[1::2]):
                return True
    # Smart quotes are asymmetric, so pair them directly.
    for quoted in re.finditer(chr(8220) + "[^" + chr(8221) + "]*" + chr(8221), line):
        if needle in quoted.group(0).lower():
            return True

    # A bibliography or reference row: "| carlini2022 | ... (LiRA) |". Citing a paper is
    # not claiming to have written it, and this rule's own guidance says to cite LiRA
    # freely as prior work.
    if stripped.startswith("|") and stripped.endswith("|"):
        has_year = re.search(r"(?:19|20)\d\d", stripped) is not None
        claims_ours = re.search(r"\b(?:we|our|ours)\b", stripped, re.I) is not None
        if has_year and not claims_ours:
            return True

    return False


def check(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    # Blockquotes are where we deliberately QUOTE dead claims in order to retract them, so
    # they are MASKED rather than removed -- deleting them shifts every line number after the
    # first quote and sends the writer to the wrong line.
    prose = "\n".join("" if ln.lstrip().startswith(">") else ln for ln in text.split("\n"))
    problems: list[str] = []

    for label, pattern, why, instead in DEAD_CLAIMS:
        for m in re.finditer(pattern, prose, re.I):
            if _is_hedged(prose, m.start(), m.end()):
                continue
            if _is_not_an_assertion(prose, m.start(), m.end()):
                continue
            line = prose[: m.start()].count("\n") + 1
            problems.append(
                f"{path.name}:{line}  [{label}]  {m.group(0)[:70]!r}\n"
                f"    dead because: {why}\n"
                f"    write instead: {instead}"
            )

    # The pairing rules say "if you make this claim, you must cite X". An evidence map makes no
    # claims -- it is a generated index of which result file backs which section -- so requiring
    # it to carry an attribution is a false positive a writer cannot fix by writing. The
    # DEAD_CLAIMS regexes above still apply to it, because a generated file can still repeat a
    # dead phrase. A checker that reports unfixable problems is a checker that gets ignored.
    if not path.name.endswith("-evidence.md"):
        for label, trigger, required, why in REQUIRED_WITH_AUDIT:
            if re.search(trigger, prose, re.I) and not re.search(required, prose, re.I):
                problems.append(f"{path.name}  [{label}]\n    {why}")

    return problems


def main() -> None:
    # The matched text can contain characters (eps, mu, en-dashes) that a Windows console's
    # cp1252 codepage cannot encode, and a checker that crashes while reporting a problem is
    # worse than no checker. Reconfigure rather than strip: the writer needs to see the actual
    # phrase in order to find it.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):  # pragma: no cover - non-reconfigurable stream
            pass

    args = [a for a in sys.argv[1:] if a != "--all"]
    if "--all" in sys.argv[1:]:
        # Repo-wide sweep. The retracted claims are asserted well outside docs/thesis --
        # ARCHITECTURE.md, the defence pack, the REPORTS folder and results/ all carry them,
        # and a chapter-only check would pass while the submitted PDF still made the claim.
        seen, targets = set(), []
        # The root and the citation metadata are included because that is exactly where a
        # dead claim survived the 2026-09-13 sweep: CITATION.cff still described the ledger as
        # "append-only" -- the phrase P2.3 removed everywhere else -- because the sweep only
        # looked at Markdown inside three directories. The blind spot, not the phrase, was the
        # defect. The outer README is included for the same reason: it is the first file a
        # stranger opens and it lives above this repository.
        for pat in (
            "docs/**/*.md",
            "results/**/*.md",
            "research/**/*.md",
            "../REPORTS/*.md",
            "*.md",
            "CITATION.cff",
            "../README.md",
            "../INDEX.md",
            "../CONTRIBUTIONS.md",
        ):
            for f in sorted(ROOT.glob(pat)):
                if f.is_file() and f not in seen:
                    seen.add(f)
                    targets.append(f)
    elif args:
        targets = [Path(a) for a in args]
    else:
        targets = sorted(THESIS.glob("ch0*.md"))
    missing = [p for p in targets if not p.exists()]
    if missing:
        sys.exit(f"no such file: {', '.join(str(m) for m in missing)}")

    problems: list[str] = []
    for p in targets:
        problems.extend(check(p))

    if not problems:
        print(f"OK - {len(targets)} file(s) checked, no known-dead claim found.")
        print("     This does not mean the argument is sound. It means you did not write one")
        print("     of the TWENTY claims killed by research/08_novelty_verdict.md,")
        print("     research/10_deep_survey_2026-08-25.md, and the 2026-09-06 kill pass")
        print("     recorded in .novelty/05_kill_report.md.")
        return

    print(f"FOUND {len(problems)} claim(s) the evidence no longer supports:\n")
    for p in problems:
        print(f"  - {p}\n")
    print("Fix the prose, never the check. See docs/thesis/WRITING_NOTICE.md.")
    sys.exit(1)


if __name__ == "__main__":
    main()
