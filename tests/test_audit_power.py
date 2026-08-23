"""Tests for `synthproof audit-power` -- the pre-audit power analysis.

The command answers, before an audit runs, whether it could certify the epsilon being sought.
This project ran the experiment that motivates it: H1 used 60 canaries against a proved epsilon
of 7.36, where the ceiling is 2.97, so the reported zero could never have been anything else.

These tests pin the command against the figures already committed to `results/`. If the CLI ever
disagrees with them, one of the two is wrong and the build should stop -- which is the same
principle the PDF builders use.
"""

import json

import pytest
from click.testing import CliRunner

from synthproof.audit.steinke import canaries_needed_for, max_provable_epsilon
from synthproof.cli import main


@pytest.fixture
def run():
    runner = CliRunner()

    def _run(*args):
        return runner.invoke(main, ["audit-power", *args])

    return _run


# ------------------------------------------------------- agreement with committed results


def test_the_ceiling_matches_the_committed_h1_figure(run):
    """results/AUDITOR_COMPARISON.md reports a one-run ceiling of 2.972 at 60 canaries."""
    r = run("--eps", "7.36", "--canaries", "60", "--json")
    assert r.exit_code == 0, r.output
    got = json.loads(r.output)
    assert got["ceiling"] == pytest.approx(2.972, abs=5e-4)
    assert got["can_certify_target"] is False


def test_the_subgroup_ceiling_matches_the_committed_h2_figure(run):
    """results/H2_RESULTS.md reports a per-subgroup ceiling of 3.27 at 80 canaries per group."""
    r = run("--eps", "7.36", "--canaries", "400", "--subgroups", "5", "--json")
    assert r.exit_code == 0, r.output
    got = json.loads(r.output)
    assert got["canaries_per_subgroup"] == 80
    assert got["ceiling"] == pytest.approx(3.27, abs=5e-3)


def test_the_canary_requirement_matches_the_committed_table(run):
    """AUDITOR_COMPARISON.md: certifying eps = 7.36 needs about 4,711 perfect guesses."""
    r = run("--eps", "7.36", "--json")
    assert r.exit_code == 0, r.output
    assert json.loads(r.output)["canaries_required_total"] == 4711


@pytest.mark.parametrize("eps,expected", [(1.0, 10), (2.0, 24), (4.0, 166)])
def test_small_epsilon_requirements_match_the_committed_table(run, eps, expected):
    r = run("--eps", str(eps), "--json")
    assert json.loads(r.output)["canaries_required_total"] == expected


# ------------------------------------------------------- the verdict is the point


def test_it_refuses_an_audit_that_could_not_answer_the_question(run):
    r = run("--eps", "7.36", "--canaries", "60")
    assert r.exit_code == 0
    assert "CANNOT certify" in r.output
    # The reason a zero would be uninformative must be stated, not merely implied.
    assert "not evidence of no leakage" in r.output


def test_it_approves_an_audit_that_can(run):
    """At eps = 1 the ceiling needs only ~10 guesses, so 60 is comfortably enough."""
    r = run("--eps", "1.0", "--canaries", "60")
    assert r.exit_code == 0
    assert "CAN certify" in r.output


def test_the_requirement_scales_with_subgroup_count(run):
    """Splitting a budget across subgroups multiplies the requirement; H2 lives with this."""
    one = json.loads(run("--eps", "4.0", "--json").output)["canaries_required_total"]
    five = json.loads(run("--eps", "4.0", "--subgroups", "5", "--json").output)[
        "canaries_required_total"
    ]
    assert five == one * 5


# ------------------------------------------------------- the maths behind it


def test_the_cli_agrees_with_the_library_it_wraps(run):
    for r_ in (10, 60, 400, 800):
        got = json.loads(run("--eps", "1.0", "--canaries", str(r_), "--json").output)
        assert got["ceiling"] == pytest.approx(max_provable_epsilon(r_), rel=1e-12)


def test_the_ceiling_is_the_steinke_corollary_not_our_own_theorem():
    """Attribution, pinned as a test so nobody re-promotes it to a contribution.

    Steinke, Nasr & Jagielski (2023) Thm 2.1 / Eq. (3) bound the correct-guess count by
    `P[Binomial(r, p(eps)) >= v]`. Set v = r and it reduces to `p(eps)^r <= beta`, which is
    exactly `max_provable_epsilon`. If these ever diverge, the docstring attribution in
    `audit/steinke.py` has become false.
    """
    import math

    def steinke_corollary(r, beta=0.05):
        b = beta ** (1.0 / r)
        return math.log(b / (1.0 - b))

    for r_ in (10, 60, 100, 400, 800):
        assert max_provable_epsilon(r_) == pytest.approx(steinke_corollary(r_), rel=1e-12)


def test_certifying_a_larger_epsilon_costs_exponentially_more():
    """The shape that survives every escape route in the 2025-26 literature."""
    counts = [canaries_needed_for(e) for e in (1.0, 2.0, 3.0, 4.0)]
    assert counts == sorted(counts)
    # counts[:-1] not counts -- zip(strict=True) requires equal lengths, and pairing a list
    # with its own tail is the classic way to violate that.
    ratios = [b / a for a, b in zip(counts[:-1], counts[1:], strict=True)]
    assert all(x > 2.0 for x in ratios), ratios


# ------------------------------------------------------- input validation


@pytest.mark.parametrize(
    "args", [("--eps", "0"), ("--eps", "-1"), ("--eps", "1", "--canaries", "0")]
)
def test_impossible_inputs_are_refused(run, args):
    assert run(*args).exit_code != 0


def test_subgroups_must_be_at_least_one(run):
    assert run("--eps", "1.0", "--subgroups", "0").exit_code != 0
