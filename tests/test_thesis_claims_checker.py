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
