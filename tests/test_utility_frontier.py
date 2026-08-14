"""Tests for UtilityEvaluator, the Privacy Data Sheet, and its signature."""

import json

import pytest

from synthproof.data.dataset import TabularDataset
from synthproof.evaluate.utility import UtilityEvaluator
from synthproof.frontier.certificate import FrontierEngine
from synthproof.frontier.experiment import MECHANISMS
from synthproof.ledger import signing


def test_utility_evaluator():
    ds = TabularDataset.create_synthetic_toy(num_rows=100)
    evaluator = UtilityEvaluator(target_col="category", seed=42)
    res = evaluator.evaluate(real_df=ds.df, synthetic_df=ds.df)

    assert 0.0 <= res.tstr_macro_f1 <= 1.0
    assert 0.0 <= res.trtr_macro_f1 <= 1.0
    assert res.utility_gap >= 0.0


def test_trtr_is_held_out_not_in_sample():
    """Regression: TRTR used to be `clf.predict(X_train)`, a constant ~0.971.

    The toy dataset's label is independent of its features, so an honest held-out TRTR
    must land near chance. An in-sample score would be near 1.0.
    """
    ds = TabularDataset.create_synthetic_toy(num_rows=200)
    res = UtilityEvaluator(target_col="category", seed=42).evaluate(ds.df, ds.df)
    assert res.trtr_macro_f1 < 0.6, (
        f"TRTR={res.trtr_macro_f1:.3f} is implausibly high for random labels — "
        "it is probably being scored in-sample again"
    )


def test_utility_evaluator_raises_instead_of_returning_mock_values():
    """Regression: a schema mismatch used to silently return hardcoded 0.75/0.80."""
    ds = TabularDataset.create_synthetic_toy(num_rows=50)
    with pytest.raises(ValueError, match="not found"):
        UtilityEvaluator(target_col="does_not_exist", seed=42).evaluate(ds.df, ds.df)


def test_utility_result_has_no_fabricated_fairness_field():
    ds = TabularDataset.create_synthetic_toy(num_rows=100)
    res = UtilityEvaluator(target_col="category", seed=42).evaluate(ds.df, ds.df)
    assert not hasattr(res, "fairness_drift")


# ------------------------------------------------------------------ data sheet

def _sheet(mechanism="independent", eps_grid=(1.0)):
    ds = TabularDataset.create_synthetic_toy(num_rows=200)
    grid = list(eps_grid) if isinstance(eps_grid, (list, tuple)) else [eps_grid]
    return FrontierEngine(seed=42).run_sweep(
        ds, eps_grid=grid, mechanism=mechanism, num_canaries=10
    )


def test_data_sheet_names_the_mechanism_that_actually_ran():
    """Regression for the misnaming that survived two audits.

    `certificate.py` labelled every run "AIM_Marginal_Generator" while instantiating
    `IndependentMarginalGenerator`, so the CLI, the API and the web console all reported
    AIM for a run of independent 1-D histograms. Worse, the previous version of THIS test
    asserted the false label, so the suite defended the lie. Names now come from the same
    registry the experiments use.
    """
    sheet = _sheet("independent")
    assert sheet.mechanism == "independent"
    assert sheet.mechanism in MECHANISMS
    assert "AIM" not in sheet.to_json()


def test_data_sheet_rejects_an_unknown_mechanism():
    ds = TabularDataset.create_synthetic_toy(num_rows=50)
    with pytest.raises(KeyError, match="Unknown mechanism"):
        FrontierEngine().run_sweep(ds, eps_grid=[1.0], mechanism="AIM / MST")


def test_data_sheet_carries_a_real_ledger_head_and_evaluation_context():
    sheet = _sheet(eps_grid=[0.5, 1.0])
    assert sheet.dataset_name == "toy_dataset"
    assert len(sheet.frontier_curve) == 2
    # Regression: the head used to be the all-zero genesis hash because the engine created
    # a ledger and never appended to it.
    assert sheet.ledger_hash != "0" * 64
    # Utility comes from a canary-free second fit; the sheet has to say so.
    assert sheet.evaluation["utility_source"] == "clean_fit"
    assert sheet.evaluation["canary_fraction"] == 0.0


def test_data_sheet_lists_attacks_it_did_not_run():
    sheet = _sheet()
    assert "distance_mia" in sheet.attacks_run
    assert {"LiRA", "DOMIAS", "attribute_inference"} <= set(sheet.attacks_not_implemented)


def test_unsigned_sheet_is_reported_as_unsigned(tmp_path):
    sheet = _sheet()
    assert sheet.signature is None
    with pytest.raises(signing.SignatureError, match="unsigned"):
        signing.verify_datasheet(json.loads(sheet.to_json()), key_path=tmp_path / "any")


# ------------------------------------------------------------------ signing

def test_signed_sheet_verifies_against_the_published_key(tmp_path):
    """The project's title, made literally true: a third party can check the claim."""
    priv, pub = signing.generate_keypair(key_dir=tmp_path / "keys")

    sheet = _sheet()
    signing.sign_datasheet(sheet, key_path=priv)
    assert sheet.signature and sheet.public_key

    # A verifier has only the JSON file and the public key.
    loaded = json.loads(sheet.to_json())
    assert signing.verify_datasheet(loaded, key_path=pub) is True


def test_editing_any_field_breaks_the_signature(tmp_path):
    """Altering a published epsilon must be detectable — that is the whole point."""
    priv, pub = signing.generate_keypair(key_dir=tmp_path / "keys")
    sheet = _sheet()
    signing.sign_datasheet(sheet, key_path=priv)
    loaded = json.loads(sheet.to_json())

    tampered = dict(loaded)
    tampered["total_proved_eps"] = 0.01
    with pytest.raises(signing.SignatureError, match="does not verify"):
        signing.verify_datasheet(tampered, key_path=pub)


def test_a_sheet_cannot_vouch_for_itself(tmp_path):
    """Verifying against the key embedded in the sheet proves only that it signed itself.

    An attacker who re-signs an edited sheet with their own key must not pass. The verifier
    therefore requires the expected key separately, and rejects a mismatch.
    """
    _, pub_a = signing.generate_keypair(key_dir=tmp_path / "a")
    priv_b, _ = signing.generate_keypair(key_dir=tmp_path / "b")

    sheet = _sheet()
    signing.sign_datasheet(sheet, key_path=priv_b)   # signed by B
    loaded = json.loads(sheet.to_json())

    with pytest.raises(signing.SignatureError, match="different key"):
        signing.verify_datasheet(loaded, key_path=pub_a)   # verified against A

    # And with no key at all, verification is refused rather than trusting the sheet.
    with pytest.raises(signing.SignatureError, match="public key is required"):
        signing.verify_datasheet(loaded)


def test_keygen_refuses_to_clobber_an_existing_key(tmp_path):
    """Overwriting a signing key invalidates every signature ever made with it."""
    signing.generate_keypair(key_dir=tmp_path / "keys")
    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        signing.generate_keypair(key_dir=tmp_path / "keys")
    # Explicit opt-in still works.
    signing.generate_keypair(key_dir=tmp_path / "keys", overwrite=True)


def test_missing_key_error_names_the_fix(tmp_path):
    with pytest.raises(FileNotFoundError, match="synthproof keygen"):
        signing.load_private_key(tmp_path / "absent")
