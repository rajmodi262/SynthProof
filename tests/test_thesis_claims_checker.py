"""Tests for the thesis claims checker.

A checker that cries wolf gets switched off, and a checker that stays silent protects nobody.
Both halves therefore need pinning, and both classes of false positive fixed by hand on
2026-08-23 are regression-tested here:

  * it flagged "we found no system that ..." -- the exact hedge it recommends;
  * it flagged "NOT cross-release: there is no cross-session enforcement" -- a retraction;
  * it flagged every citation of Carlini et al.'s LiRA in the literature review.

Each is now a test, because each was a real mistake that would have taught a writer to ignore
the tool.
"""

from pathlib import Path

import pytest

from scripts.check_thesis_claims import DEAD_CLAIMS, check


def _write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "chapter.md"
    p.write_text(text, encoding="utf-8")
    return p


def labels(problems: list[str]) -> set[str]:
    out = set()
    for p in problems:
        if "[" in p:
            out.add(p.split("[", 1)[1].split("]", 1)[0])
    return out


# ----------------------------------------------------------------- it fires when it should


@pytest.mark.parametrize(
    "text,expected",
    [
        ("No existing system ships both bounds.", "no-existing-system"),
        ("We are the first system to do this.", "first-to"),
        ("The ledger is append-only.", "append-only"),
        ("The ledger supports cross-release composition.", "cross-release"),
        ("We derive the ceiling, which is our contribution.", "ceiling-as-ours"),
        ("Our refusal gate is novel.", "refusal-novel"),
        ("We implemented LiRA and report its AUC.", "lira-as-ours"),
    ],
)
def test_a_dead_claim_is_caught(tmp_path, text, expected):
    assert expected in labels(check(_write(tmp_path, text))), f"missed: {text!r}"


# ----------------------------------------------------------------- it stays quiet when it should


def test_the_recommended_hedge_is_not_flagged(tmp_path):
    """It must not punish the phrasing it tells you to use."""
    text = "We found no system that releases a dataset accompanied by both bounds."
    assert "no-existing-system" not in labels(check(_write(tmp_path, text)))


def test_a_retraction_is_not_flagged(tmp_path):
    """Saying a claim is false necessarily contains the claim."""
    text = "**Not** cross-release: there is no cross-session budget enforcement, and DPolicy does."
    assert "cross-release" not in labels(check(_write(tmp_path, text)))


def test_citing_lira_as_prior_work_is_fine(tmp_path):
    """ch02 must be able to discuss Carlini et al. without tripping the checker."""
    text = (
        "Carlini et al. [2022] substantially strengthened this with LiRA, which fits "
        "per-example Gaussians to the IN and OUT score distributions."
    )
    assert "lira-as-ours" not in labels(check(_write(tmp_path, text)))


def test_saying_lira_is_not_implemented_is_fine(tmp_path):
    text = "We did not implement LiRA; it is not present in the codebase."
    assert "lira-as-ours" not in labels(check(_write(tmp_path, text)))


def test_blockquoted_text_is_exempt(tmp_path):
    """Warning blocks quote dead claims deliberately in order to retract them."""
    text = "> Do not write: no existing system ships both bounds.\n\nReal prose here.\n"
    assert "no-existing-system" not in labels(check(_write(tmp_path, text)))


# ----------------------------------------------------------------- reported positions are usable


def test_line_numbers_survive_a_blockquote(tmp_path):
    """Blockquotes are masked, not deleted -- deleting them shifted every later line number."""
    text = "> quoted warning line\n> second quoted line\n\nThe ledger is append-only.\n"
    problems = check(_write(tmp_path, text))
    assert any(":4" in p for p in problems), problems


def test_a_clean_chapter_reports_nothing(tmp_path):
    text = (
        "We found no system that signs the claim. The ceiling follows from Steinke et al. "
        "(2023) Thm 2.1, and eps_audited is reported beside its ceiling throughout.\n"
    )
    assert check(_write(tmp_path, text)) == []


# ----------------------------------------------------------------- the rule table itself


def test_every_rule_explains_itself():
    """A finding without a remedy is a complaint. Each rule owes the writer both."""
    for label, pattern, why, instead in DEAD_CLAIMS:
        assert label and pattern, label
        assert len(why) > 40, f"{label}: 'dead because' is too thin to act on"
        assert len(instead) > 25, f"{label}: no usable replacement offered"


def test_the_audit_rule_demands_a_ceiling(tmp_path):
    """A zero with no ceiling beside it is the failure Dibia et al.'s experts named."""
    bare = "We report eps_audited = 0.000 across every cell."
    assert "missing-ceiling" in labels(check(_write(tmp_path, bare)))

    withceiling = bare + " The ceiling at m = 60 is 2.97, so the value is uninformative."
    assert "missing-ceiling" not in labels(check(_write(tmp_path, withceiling)))


def test_a_quoted_dead_phrase_is_not_flagged(tmp_path):
    """A document warning against a phrase necessarily contains it.

    Third false-positive class of this kind: the checker flagged ch04's own retraction
    ('do not call this "append-only"') and the ch05 evidence map's identical warning.
    Quoting or prohibiting is correct behaviour; only the bare assertion is a claim.
    """
    warned = 'Do not call this ledger "append-only" — nothing prevents an append.'
    assert "append-only" not in labels(check(_write(tmp_path, warned)))

    asserted = "The ledger is append-only and signed."
    assert "append-only" in labels(check(_write(tmp_path, asserted)))


def test_a_hedge_inside_the_matched_span_is_respected(tmp_path):
    """Fourth false-positive class, and the one that forced a general fix.

    A loose pattern often swallows the very words that negate it. Here 'unrefuted' and
    'rather than' both fall INSIDE the match, so a guard that only inspected the text
    around the span still fired. The window now spans the match itself.
    """
    hedged = (
        "The SDC Handbook was unreachable, so the refusal gate is *unrefuted* rather than novel."
    )
    assert "refusal-novel" not in labels(check(_write(tmp_path, hedged)))

    asserted = "Our refusal gate is novel and no other system does this."
    assert "refusal-novel" in labels(check(_write(tmp_path, asserted)))


def test_the_generated_evidence_maps_are_clean(tmp_path):
    """The maps tell writers what not to say; they must not trip the rule themselves."""
    from scripts.check_thesis_claims import THESIS

    for name in ("ch01-evidence.md", "ch05-evidence.md", "ch08-evidence.md"):
        p = THESIS / name
        if p.exists():
            assert check(p) == [], f"{name} states a dead claim: {check(p)}"


# ----------------------------------------------------------------- citations


def test_every_cited_key_resolves_and_nothing_is_entered_twice():
    """Guards three failures, all of which were live on 2026-08-23.

    A dangling key renders as [?]. A key defined in two files lets BibTeX pick the wrong
    venue silently. The same work under two keys prints twice and reads as two results --
    which is what happened to Ganev et al.'s Robin Hood paper, entered once under its arXiv
    year and once under its ICML year.
    """
    from scripts.check_citations import collect_bib, collect_cites

    keys, titles = collect_bib()
    cites = collect_cites()

    dangling = sorted(k for k in cites if k not in keys)
    assert not dangling, f"cited but undefined: {dangling}"

    dup_keys = sorted(k for k, files in keys.items() if len(files) > 1)
    assert not dup_keys, f"defined in more than one bib file: {dup_keys}"

    dup_works = []
    for title, entries in titles.items():
        by_author = {}
        for key, _path, first in entries:
            by_author.setdefault(first, set()).add(key)
        for ks in by_author.values():
            if len(ks) > 1:
                dup_works.append((title[:50], sorted(ks)))
    assert not dup_works, f"same work under multiple keys: {dup_works}"


def test_a_shared_title_by_different_authors_is_not_a_duplicate():
    """'Verifiable Differential Privacy' is Narayan et al. (EuroSys 2015) AND Biswas &
    Cormode (2022). Matching on title alone flagged them; the check needs the author too."""
    from scripts.check_citations import collect_bib

    _, titles = collect_bib()
    vdp = titles.get("verifiable differential privacy", [])
    if vdp:
        assert len({a for _k, _p, a in vdp}) > 1, "expected distinct first authors"


# ------------------------------------------------- the nine claims that died on 2026-09-06


@pytest.mark.parametrize(
    "label,asserted,hedged",
    [
        (
            "complete-case-as-ours",
            "We are the first to show that complete-case deletion biases the reference.",
            "FairPrep reported this in 2019, so we do not claim complete-case deletion as ours.",
        ),
        (
            "folktables-defect-as-ours",
            "We found the folktables nan_to_num defect.",
            "The folktables nan_to_num defect is not ours -- it is GitHub issue #39.",
        ),
        (
            "selection-deleted-as-ours",
            "We contribute a selection-deleted control arm for workload-adaptive mechanisms.",
            "The selection-deleted arm is not a contribution; SmartNoise ships measure_only.",
        ),
        (
            "gdp-auditing-as-ours",
            "We propose a GDP tradeoff-curve audit of marginal mechanisms.",
            "GDP auditing is occupied by Ganev et al., so we do not propose it.",
        ),
        (
            "amplification-audit-as-first",
            "We are the first to audit an amplification bound empirically.",
            "We are not the first to audit an amplification bound -- Annamalai et al. were.",
        ),
        (
            "two-fit-split-as-ours",
            "We propose a two-fit split separating the audit from the utility measurement.",
            "The two-fit split is not ours; Mitchell et al. recommend it. We only quantify it.",
        ),
    ],
)
def test_each_new_dead_claim_fires_when_asserted_and_not_when_hedged(
    tmp_path, label, asserted, hedged
):
    """Both halves matter. A checker that cries wolf on a retraction gets switched off."""
    assert label in labels(check(_write(tmp_path, asserted))), f"{label} did not fire"
    assert label not in labels(check(_write(tmp_path, hedged))), f"{label} fired on a hedge"


def test_the_ceiling_claim_must_carry_its_limit_of_detection_attribution(tmp_path):
    """An examiner with lab-science background says 'this is just LoD'. We must say it first."""
    bare = "The artefact reports the audit_ceiling beside the audited epsilon."
    assert "missing-lod-transfer" in labels(check(_write(tmp_path, bare)))

    cited = (
        "The artefact reports the audit_ceiling beside the audited epsilon. This transfers the "
        "limit of detection convention that MIQE 2.0 mandates for qPCR, and we cite it as such. "
        "The quantity is a corollary of Steinke et al."
    )
    assert "missing-lod-transfer" not in labels(check(_write(tmp_path, cited)))


def test_the_ceiling_must_be_attributed_not_only_to_steinke(tmp_path):
    """The concept already has a published NAME in this exact sub-domain."""
    bare = "We report the operating range of the empirical metric."
    assert "missing-ceiling-attribution" in labels(check(_write(tmp_path, bare)))

    named = (
        "We report the operating range of the empirical metric, which Annamalai, Ganev & "
        "De Cristofaro call the maximum auditable epsilon, following MIQE 2.0's limit of "
        "detection convention."
    )
    assert "missing-ceiling-attribution" not in labels(check(_write(tmp_path, named)))


def test_generated_evidence_maps_are_exempt_from_pairing_rules_but_not_dead_claims(tmp_path):
    """A generated index makes no claims, so it cannot be asked to carry an attribution.

    It can still repeat a dead phrase, so the DEAD_CLAIMS half must still apply to it.
    """
    p = tmp_path / "ch99-evidence.md"
    p.write_text("Section 7.2 reports the audit_ceiling. See results/RESULTS.md.", encoding="utf-8")
    assert "missing-lod-transfer" not in labels(check(p))

    p.write_text("We found the folktables nan_to_num defect.", encoding="utf-8")
    assert "folktables-defect-as-ours" in labels(check(p))


def test_the_refuted_canary_percentage_cannot_come_back(tmp_path):
    """It does not replicate (results/CANARY_DOSE_RESPONSE.md), so the number is now a dead claim."""
    assert "canary-89-percent" in labels(
        check(_write(tmp_path, "Planting canaries destroyed 89% of the correlation signal."))
    )
    assert "canary-89-percent" in labels(
        check(_write(tmp_path, "corr fell from 0.1014 to 0.0109 on the augmented split."))
    )
    hedged = (
        "The previously reported 0.0109 does not replicate and is superseded; we report the "
        "dose-response shape instead."
    )
    assert "canary-89-percent" not in labels(check(_write(tmp_path, hedged)))
