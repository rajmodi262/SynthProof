"""The certificate must not misdescribe which attacks ran.

THE DEFECT THIS PINS. `frontier/certificate.py` hardcoded
`attacks_not_implemented=["LiRA", "DOMIAS", "attribute_inference"]` while `run_cell` was
calling DOMIAS on every cell and recording its AUC. Every signed Privacy Data Sheet therefore
told its recipient that an attack which had run was not implemented -- a false statement inside
a cryptographically signed payload, in a project whose entire argument is that signed claims
should be checkable.

It is the mirror image of audit finding G1, where the console hardcoded four PASSED verdicts
including one for an attack that did not exist. That one overstated, this one understated; both
are the same root cause, which is a hand-maintained list that does not read the code.

So these tests do not check a list against another list. They check the list against the
modules that exist and against what a real release actually produces.
"""

import importlib

import pytest

from synthproof.frontier.certificate import ATTACKS_NOT_IMPLEMENTED

# (module, exported class). If a module imports, the attack is implemented -- whether or not
# the pipeline currently calls it.
ATTACK_MODULES = {
    "distance_mia": ("synthproof.attacks.distance_mia", "DistanceMIABaseline"),
    "domias": ("synthproof.attacks.domias", "DOMIAS"),
    "exact_match_risk": ("synthproof.attacks.exact_match_risk", "ExactMatchRiskEvaluator"),
    "attribute_inference": (
        "synthproof.attacks.attribute_inference",
        "AttributeInferenceAttack",
    ),
}


@pytest.mark.parametrize("name,spec", sorted(ATTACK_MODULES.items()))
def test_an_implemented_attack_is_never_declared_unimplemented(name, spec):
    """The regression. If the class imports, the name must not appear on the absent list."""
    module, cls = spec
    assert hasattr(importlib.import_module(module), cls), f"{name} no longer importable"
    lowered = [a.lower() for a in ATTACKS_NOT_IMPLEMENTED]
    assert name.lower() not in lowered, (
        f"{name} is implemented ({module}.{cls}) but the signed certificate declares it "
        f"not implemented. That is a false claim in the payload."
    )


def test_only_lira_is_declared_unimplemented():
    """LiRA's absence is a decision, not a gap, and it is the only one.

    If another name is added here, it must be because the module was genuinely removed --
    in which case the parametrised test above will fail first and say so.
    """
    assert ATTACKS_NOT_IMPLEMENTED == ["LiRA"], ATTACKS_NOT_IMPLEMENTED


def test_the_api_and_the_certificate_agree_about_what_is_missing():
    """Two hardcoded lists drifted apart once already; they must not disagree again."""
    # Moved out of main.py in the 2026-09-13 split: it is reference data about what the
    # system does NOT do, which is the vocabulary, not the application.
    from synthproof.api.descriptions import NOT_IMPLEMENTED_ATTACKS

    api_names = {a["name"].lower() for a in NOT_IMPLEMENTED_ATTACKS}
    cert_names = {a.lower() for a in ATTACKS_NOT_IMPLEMENTED}
    assert api_names == cert_names, f"API says {api_names}, certificate says {cert_names}"


def test_every_absent_attack_gives_a_reason_in_the_api():
    """A capability reported as missing without a reason reads as an oversight."""
    # Moved out of main.py in the 2026-09-13 split: it is reference data about what the
    # system does NOT do, which is the vocabulary, not the application.
    from synthproof.api.descriptions import NOT_IMPLEMENTED_ATTACKS

    for entry in NOT_IMPLEMENTED_ATTACKS:
        assert entry.get("reason"), entry
        assert len(entry["reason"]) > 40, f"reason too thin to act on: {entry}"


def test_a_real_release_reports_the_attacks_it_actually_ran():
    """End to end: the list on the sheet is derived from the run, not from a constant."""
    from synthproof.data.dataset import TabularDataset
    from synthproof.frontier.certificate import FrontierEngine

    ds = TabularDataset.create_synthetic_toy(num_rows=600, seed=7)
    sheet = FrontierEngine(seed=7).run_sweep(
        ds, eps_grid=[1.0], mechanism="pairwise", num_canaries=20
    )

    # Every attack the pipeline calls must be named as run.
    for expected in ("canary_audit", "distance_mia", "domias"):
        assert expected in sheet.attacks_run, sheet.attacks_run

    # And nothing may be on both lists at once.
    overlap = set(sheet.attacks_run) & set(sheet.attacks_not_implemented)
    assert not overlap, f"claimed both run and unimplemented: {overlap}"
