import json
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from synthproof.api.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_artifacts_missing_key_and_croissant_export(client):
    # 1. verify certificate with sheet missing public key
    res = client.post("/api/certificate/verify", json={"sheet": {"total_proved_eps": 1.0}})
    assert res.status_code == 200
    data = res.json()
    assert data["signature_valid"] is False
    assert data["key_source"] is None
    assert "Missing public key" in data["error"]

    # 2. croissant export unsigned (triggers 400 with CroissantError)
    sheet_unsigned = {
        "dataset_name": "TestDS",
        "mechanism": "independent",
        "total_proved_eps": 1.0,
        "delta": 1e-5,
    }
    res_unsigned = client.post("/api/croissant/export", json={"sheet": sheet_unsigned})
    assert res_unsigned.status_code == 400
    assert "unsigned" in res_unsigned.json()["detail"]

    # 3. croissant export valid signed sheet
    sheet_signed = {
        "dataset_name": "TestDS",
        "mechanism": "independent",
        "total_proved_eps": 1.0,
        "delta": 1e-5,
        "signature": "mock_signature_base64",
    }
    res = client.post("/api/croissant/export", json={"sheet": sheet_signed})
    assert res.status_code == 200
    assert "@context" in res.json()
    assert res.json()["name"] == "TestDS"

    # 4. croissant export with arbitrary error (triggers 400)
    with patch("synthproof.frontier.croissant.to_croissant", side_effect=ValueError("bad sheet")):
        res = client.post("/api/croissant/export", json={"sheet": {}})
        assert res.status_code == 400
        assert "Could not generate Croissant" in res.json()["detail"]


def test_artifacts_verify_certificate_full(client, tmp_path):
    from synthproof.audit.ceiling import recompute_ceiling
    from synthproof.frontier.certificate import PrivacyDataSheet
    from synthproof.ledger import signing

    exact_ceiling = recompute_ceiling("one_run", 30, 0.05)

    key_dir = tmp_path / "keys"
    priv_path, pub_path = signing.generate_keypair(key_dir=key_dir)
    pub_key_obj = signing.load_public_key(pub_path)
    pubkey_hex = signing.public_key_hex(pub_key_obj)

    pds = PrivacyDataSheet(
        dataset_name="Adult",
        num_rows=100,
        target_column="income",
        total_proved_eps=1.0,
        delta=1e-5,
        total_audited_eps=0.0,
        audit_ceiling=exact_ceiling,
        audit_estimator="one_run",
        audit_budget=30,
        audit_alpha=0.05,
        mechanism="pairwise",
        mechanism_available=True,
        seed=42,
        frontier_curve=[],
        ledger_hash="a" * 64,
    )
    signing.sign_datasheet(pds, key_path=priv_path)
    signed_sheet = pds.to_dict()

    # 1. Supplied key valid signature
    res1 = client.post(
        "/api/certificate/verify",
        json={"sheet": signed_sheet, "public_key": pubkey_hex},
    )
    assert res1.status_code == 200
    d1 = res1.json()
    assert d1["signature_valid"] is True
    assert d1["publisher_authenticated"] is True
    assert d1["key_source"] == "supplied"
    assert d1["range_tone"] == "ok"
    assert d1["range_code"] == "IN_RANGE_NOT_DETECTED"

    # 2. Embedded key valid signature
    res2 = client.post("/api/certificate/verify", json={"sheet": signed_sheet})
    assert res2.status_code == 200
    d2 = res2.json()
    assert d2["signature_valid"] is True
    assert d2["publisher_authenticated"] is False
    assert d2["key_source"] == "embedded"

    # 3. Tampered sheet
    tampered = dict(signed_sheet)
    tampered["total_proved_eps"] = 999.0
    res3 = client.post(
        "/api/certificate/verify",
        json={"sheet": tampered, "public_key": pubkey_hex},
    )
    assert res3.status_code == 200
    d3 = res3.json()
    assert d3["signature_valid"] is False
    assert d3["error"] is not None

    # 4. Range tone: warn (CLAIM_EXCEEDS_AUDIT_RANGE)
    pds_warn = PrivacyDataSheet(
        dataset_name="Adult",
        num_rows=100,
        target_column="income",
        total_proved_eps=7.356,
        delta=1e-5,
        total_audited_eps=0.0,
        audit_ceiling=exact_ceiling,
        audit_estimator="one_run",
        audit_budget=30,
        audit_alpha=0.05,
        mechanism="pairwise",
        mechanism_available=True,
        seed=42,
        frontier_curve=[],
        ledger_hash="a" * 64,
    )
    signing.sign_datasheet(pds_warn, key_path=priv_path)
    res_w = client.post("/api/certificate/verify", json={"sheet": pds_warn.to_dict()})
    assert res_w.json()["range_tone"] == "warn"
    assert res_w.json()["range_code"] == "CLAIM_EXCEEDS_AUDIT_RANGE"

    # 5. Range tone: fail (AUDIT_CONTRADICTS_PROOF)
    pds_fail1 = PrivacyDataSheet(
        dataset_name="Adult",
        num_rows=100,
        target_column="income",
        total_proved_eps=1.0,
        delta=1e-5,
        total_audited_eps=5.0,
        audit_ceiling=2.254,
        audit_estimator="one_run",
        audit_budget=30,
        audit_alpha=0.05,
        mechanism="pairwise",
        mechanism_available=True,
        seed=42,
        frontier_curve=[],
        ledger_hash="a" * 64,
    )
    signing.sign_datasheet(pds_fail1, key_path=priv_path)
    res_f1 = client.post("/api/certificate/verify", json={"sheet": pds_fail1.to_dict()})
    assert res_f1.json()["range_tone"] == "fail"
    assert res_f1.json()["range_code"] == "AUDIT_CONTRADICTS_PROOF"

    # 6. Range tone: fail (CEILING_MISMATCH)
    pds_fail2 = PrivacyDataSheet(
        dataset_name="Adult",
        num_rows=100,
        target_column="income",
        total_proved_eps=1.0,
        delta=1e-5,
        total_audited_eps=0.0,
        audit_ceiling=5.0,
        audit_estimator="one_run",
        audit_budget=30,
        audit_alpha=0.05,
        mechanism="pairwise",
        mechanism_available=True,
        seed=42,
        frontier_curve=[],
        ledger_hash="a" * 64,
    )
    signing.sign_datasheet(pds_fail2, key_path=priv_path)
    res_f2 = client.post("/api/certificate/verify", json={"sheet": pds_fail2.to_dict()})
    assert res_f2.json()["range_tone"] == "fail"
    assert res_f2.json()["range_code"] == "CEILING_MISMATCH"


def test_checkpoint_branches(tmp_path):

    from synthproof.frontier.checkpoint import (
        CellRecord,
        GridCheckpoint,
        config_hash,
        run_with_checkpoints,
    )

    # 1. config_hash with bool, list, tuple
    h1 = config_hash({"flag": True, "list": [1, 2], "tuple": (3, 4)})
    assert isinstance(h1, str)

    ckpt = GridCheckpoint(tmp_path)

    # 2. load with mismatched version
    bad_ver_file = tmp_path / "cell_0000.json"
    bad_ver_file.write_text(
        json.dumps({"index": 0, "completed": True, "config_hash": "h1", "version": "0.0.0"}),
        encoding="utf-8",
    )
    assert ckpt.load(0, "h1") is None

    # 3. load corrupted json
    bad_ver_file.write_text("not json", encoding="utf-8")
    assert ckpt.load(0, "h1") is None

    # 4. completed_indices with bad file
    assert ckpt.completed_indices() == []

    # 5. save exception cleanup
    with patch("os.replace", side_effect=OSError("disk fail")):
        with pytest.raises(OSError):
            ckpt.save(CellRecord(index=1, config={"a": 1}, config_hash="abc", metrics={"m": 0.5}))

    # 6. run_with_checkpoints with progress callback and cached cell
    ckpt_dir = tmp_path / "ckpts"
    progress_msgs = []
    cells = [{"mechanism": "test", "target_eps": 1.0, "seed": 0}, {"other": "val"}]

    # Run 1: compute both
    res1 = run_with_checkpoints(
        cells, lambda c: {"acc": 0.9}, ckpt_dir, progress=progress_msgs.append
    )
    assert len(res1) == 2
    assert any("running" in m for m in progress_msgs)

    # Run 2: cached
    progress_msgs.clear()
    res2 = run_with_checkpoints(
        cells, lambda c: {"acc": 0.9}, ckpt_dir, progress=progress_msgs.append
    )
    assert len(res2) == 2
    assert any("cached" in m for m in progress_msgs)
    assert any("resumed 2 of 2" in m for m in progress_msgs)


def test_fairness_branches():
    from synthproof.evaluate.fairness import (
        SubgroupUtility,
        SubgroupUtilityEvaluator,
        SubgroupUtilityResult,
    )

    # 1. SubgroupUtility and SubgroupUtilityResult properties
    s1 = SubgroupUtility("g1", 0.45, 40, 2, 0.8, 0.85, 0.05)
    s2 = SubgroupUtility("g2", 0.45, 50, 2, 0.6, 0.85, 0.25)
    s_unreliable = SubgroupUtility("g3", 0.1, 10, 1, 0.0, 0.0, 0.0)
    assert s1.is_reliable is True
    assert s_unreliable.is_reliable is False

    eval_res = SubgroupUtilityResult("group", "target", [s1, s2, s_unreliable])
    assert eval_res.best_served == s1
    assert eval_res.worst_served == s2
    assert eval_res.gap_spread == pytest.approx(0.2)
    assert eval_res.baseline_spread == pytest.approx(0.0)
    d = eval_res.to_dict()
    assert d["attribute"] == "group"
    assert d["gap_spread"] == pytest.approx(0.2)
    assert d["num_reliable_subgroups"] == 2
    assert d["num_subgroups"] == 3

    # single reliable group -> gap_spread is None
    eval_single = SubgroupUtilityResult("group", "target", [s1, s_unreliable])
    assert eval_single.gap_spread is None
    assert eval_single.baseline_spread is None

    # test_size out of bounds
    with pytest.raises(ValueError, match="test_size must be in"):
        SubgroupUtilityEvaluator("target", "group", test_size=1.5)

    # target column missing from synthetic
    real_df = pd.DataFrame(
        {
            "feat": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            "group": [0, 1] * 5,
            "target": [0, 1] * 5,
        }
    )
    synth_df = pd.DataFrame({"feat": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], "group": [0, 1] * 5})
    evaluator = SubgroupUtilityEvaluator("target", "group")
    with pytest.raises(ValueError, match="target column 'target' missing"):
        evaluator.evaluate(real_df, synth_df)

    # no numeric feature columns
    real_no_num = pd.DataFrame(
        {"text": ["a"] * 10, "group": ["g0", "g1"] * 5, "target": [0, 1] * 5}
    )
    with pytest.raises(ValueError, match="no numeric feature columns"):
        evaluator.evaluate(real_no_num, real_no_num)

    # real_train_df provided
    synth_valid = pd.DataFrame(
        {
            "feat": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            "group": ["g0", "g1"] * 5,
            "target": [0, 1] * 5,
        }
    )
    real_valid = pd.DataFrame(
        {
            "feat": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            "group": ["g0", "g1"] * 5,
            "target": [0, 1] * 5,
        }
    )
    res_tr = evaluator.evaluate(real_valid, synth_valid, real_train_df=real_valid)
    assert res_tr.attribute == "group"

    # real_train_df missing cols
    with pytest.raises(ValueError, match="real_train_df is missing columns"):
        evaluator.evaluate(real_valid, synth_valid, real_train_df=pd.DataFrame({"feat": [1]}))

    # evaluate without real_train_df (carves split using train_test_split)
    # and with a group with only 1 sample placed in train split so n=0 in test split
    real_split = pd.DataFrame(
        {
            "feat": [float(i) for i in range(20)],
            "group": ["rare"] + ["g0"] * 9 + ["g1"] * 10,
            "target": [0, 1] * 10,
        }
    )
    synth_split = pd.DataFrame(
        {
            "feat": [float(i) for i in range(20)],
            "group": ["rare"] + ["g0"] * 9 + ["g1"] * 10,
            "target": [0, 1] * 10,
        }
    )
    ev_split = SubgroupUtilityEvaluator("target", "group", test_size=0.3, seed=42)
    res_sp = ev_split.evaluate(real_split, synth_split)
    assert res_sp.attribute == "group"

    # cover line 101: worst_served is None or best_served is None
    with patch.object(SubgroupUtilityResult, "worst_served", None):
        assert eval_res.gap_spread is None


def test_differential_accounting_branches():
    from collections import namedtuple

    from synthproof.accounting.differential import (
        AccountantDisagreement,
        _autodp_mechanism,
        cross_check,
        cross_check_spends,
        enforce,
    )

    # 1. unsupported mechanism in _autodp_mechanism
    with pytest.raises(ValueError, match="unsupported mechanism"):
        _autodp_mechanism("unknown_mech", 1.0, 1.0)

    # 2. cross_check with unsupported name (dp-sgd is in accountant but not differential)
    agr_unsupported = cross_check(1.0, 1e-5, name="dp-sgd")
    assert agr_unsupported.verdict == "unsupported"

    # 3. ImportError for Composition in cross_check
    with patch.dict("sys.modules", {"autodp.transformer_zoo": None}):
        agr_no_autodp = cross_check(1.0, 1e-5)
        assert agr_no_autodp.verdict == "unavailable"

    # 4. under_report condition and enforce()
    with patch("synthproof.accounting.differential.epsilon_for_noise_scale", return_value=0.1):
        agr_under = cross_check(1.0, 1e-5)
        assert agr_under.verdict == "under_report"
        assert agr_under.blocks_release is True
        with pytest.raises(AccountantDisagreement):
            enforce(agr_under)

    # 5. conservative condition (relative diff > tolerance, but ours > theirs)
    with patch("synthproof.accounting.differential.epsilon_for_noise_scale", return_value=10.0):
        agr_cons = cross_check(1.0, 1e-5, tolerance=0.01)
        assert agr_cons.verdict == "conservative"
        assert agr_cons.blocks_release is False
        assert enforce(agr_cons) == agr_cons

    # 6. cross_check_spends empty spends
    agr_empty = cross_check_spends([], 1e-5)
    assert agr_empty.verdict == "unavailable"
    assert agr_empty.primary_epsilon == 0.0

    # 7. cross_check_spends unsupported spend
    DummySpend = namedtuple("DummySpend", ["mechanism", "computed_eps"])
    DummyMech = namedtuple("DummyMech", ["name", "noise_scale", "sensitivity", "steps"])
    unsupported_spend = DummySpend(
        mechanism=DummyMech(name="custom_mech", noise_scale=1.0, sensitivity=1.0, steps=1),
        computed_eps=1.0,
    )
    agr_spend_unsupp = cross_check_spends([unsupported_spend], 1e-5)
    assert agr_spend_unsupp.verdict == "unsupported"

    # 8. cross_check_spends missing autodp
    valid_spend = DummySpend(
        mechanism=DummyMech(name="gaussian", noise_scale=1.0, sensitivity=1.0, steps=1),
        computed_eps=1.0,
    )
    with patch.dict("sys.modules", {"autodp.transformer_zoo": None}):
        agr_spend_no_autodp = cross_check_spends([valid_spend], 1e-5)
        assert agr_spend_no_autodp.verdict == "unavailable"


def test_allocator_branches():
    from synthproof.ledger.allocator import Allocator

    # allocate_uniform
    with pytest.raises(ValueError, match="Total epsilon must be positive"):
        Allocator.allocate_uniform(0.0, ["col1"])
    assert Allocator.allocate_uniform(1.0, []) == {}
    res_u = Allocator.allocate_uniform(1.0, ["a", "b"])
    assert res_u == {"a": 0.5, "b": 0.5}

    # allocate_weighted
    with pytest.raises(ValueError, match="Total epsilon must be positive"):
        Allocator.allocate_weighted(-1.0, {"a": 1.0})
    assert Allocator.allocate_weighted(1.0, {}) == {}
    # all zero weights -> fallback to uniform
    res_fallback = Allocator.allocate_weighted(1.0, {"a": 0.0, "b": -1.0})
    assert res_fallback == {"a": 0.5, "b": 0.5}
    # valid weights
    res_w = Allocator.allocate_weighted(3.0, {"a": 1.0, "b": 2.0})
    assert res_w["a"] == pytest.approx(1.0)
    assert res_w["b"] == pytest.approx(2.0)


def test_noise_branches():
    from synthproof.accounting.noise import (
        sample_discrete_gaussian,
        sample_discrete_laplace,
    )

    # laplace scale <= 0
    with pytest.raises(ValueError, match="Scale must be positive"):
        sample_discrete_laplace(0.0)

    lap_samples = sample_discrete_laplace(1.0, size=5, seed=42)
    assert len(lap_samples) == 5
    assert isinstance(lap_samples[0], (int, np.integer))

    # gaussian sigma <= 0
    with pytest.raises(ValueError, match="Sigma must be positive"):
        sample_discrete_gaussian(-0.5)

    gauss_samples = sample_discrete_gaussian(1.5, size=5, seed=42)
    assert len(gauss_samples) == 5
    assert isinstance(gauss_samples[0], (int, np.integer))


def test_descriptions_branches():
    from collections import namedtuple

    from synthproof.api.descriptions import _audit_payload, audit_ceiling

    # audit_ceiling below min
    c_low = audit_ceiling(5)
    assert c_low > 0

    # audit_ceiling above max
    c_high = audit_ceiling(100000)
    assert c_high > 0

    # audit_ceiling interpolation
    c_mid = audit_ceiling(50)
    assert c_mid > 0

    # _audit_payload with Steinke (one_run)
    SteinkeAudit = namedtuple(
        "SteinkeAudit",
        [
            "audited_eps",
            "p_value",
            "guesses",
            "ceiling",
            "saturated",
            "correct",
            "accuracy",
            "num_canaries",
            "num_included",
        ],
    )
    s_audit = SteinkeAudit(
        audited_eps=0.5,
        p_value=0.01,
        guesses=60,
        ceiling=2.97,
        saturated=False,
        correct=40,
        accuracy=0.667,
        num_canaries=60,
        num_included=30,
    )
    payload_s = _audit_payload(s_audit, 60)
    assert payload_s["auditor"] == "one_run"
    assert payload_s["audited_eps"] == 0.5

    # _audit_payload with paired Clopper-Pearson
    PairedAudit = namedtuple(
        "PairedAudit",
        [
            "audited_eps",
            "p_value",
            "tpr",
            "fpr",
            "tpr_lower",
            "fpr_upper",
            "num_members",
            "num_holdout",
            "confidence",
        ],
    )
    p_audit = PairedAudit(
        audited_eps=0.2,
        p_value=0.05,
        tpr=0.6,
        fpr=0.5,
        tpr_lower=0.52,
        fpr_upper=0.58,
        num_members=30,
        num_holdout=30,
        confidence=0.95,
    )
    payload_p = _audit_payload(p_audit, 60)
    assert payload_p["auditor"] == "paired"
    assert payload_p["audited_eps"] == 0.2


def test_accounting_types_validation():
    from synthproof.accounting.types import MechanismSpec, PrivacyParams

    with pytest.raises(ValueError, match="Epsilon must be non-negative"):
        PrivacyParams(epsilon=-0.1)

    with pytest.raises(ValueError, match="Delta must be in"):
        PrivacyParams(epsilon=1.0, delta=-0.01)

    with pytest.raises(ValueError, match="Delta must be in"):
        PrivacyParams(epsilon=1.0, delta=1.5)

    with pytest.raises(ValueError, match="Sensitivity must be positive"):
        MechanismSpec(name="test", sensitivity=0.0, noise_scale=1.0)

    with pytest.raises(ValueError, match="Noise scale must be non-negative"):
        MechanismSpec(name="test", sensitivity=1.0, noise_scale=-0.1)

    with pytest.raises(ValueError, match="Steps must be at least 1"):
        MechanismSpec(name="test", sensitivity=1.0, noise_scale=1.0, steps=0)

    with pytest.raises(ValueError, match="Sampling rate must be in"):
        MechanismSpec(name="test", sensitivity=1.0, noise_scale=1.0, sampling_rate=0.0)

    with pytest.raises(ValueError, match="Sampling rate must be in"):
        MechanismSpec(name="test", sensitivity=1.0, noise_scale=1.0, sampling_rate=1.5)


def test_generators_base_abstract():
    from synthproof.generators.base import BaseGenerator

    # 1. BaseGenerator cannot be instantiated directly because it is abstract
    with pytest.raises(TypeError, match="Can't instantiate abstract class BaseGenerator"):
        BaseGenerator()

    # 2. Subclass missing abstract methods also cannot be instantiated
    class MissingGenerate(BaseGenerator):
        def fit(self, dataset, profile, accountant, target_eps):
            pass

    with pytest.raises(TypeError, match="Can't instantiate abstract class MissingGenerate"):
        MissingGenerate()

    # 3. Concrete subclass inherits base attributes and methods
    class DummyGenerator(BaseGenerator):
        def fit(self, dataset, domain, budget, delta=1e-5):
            super().fit(dataset, domain, budget, delta)
            self.is_fitted = True
            return self

        def generate(self, num_samples: int):
            super().generate(num_samples)
            return None

    gen = DummyGenerator(seed=123)
    assert gen.seed == 123
    assert gen.is_fitted is False
    assert gen.fit(None, None, None) is gen
    assert gen.is_fitted is True
    assert gen.generate(5) is None


def test_cli_branches_extra(tmp_path):
    from click.testing import CliRunner

    from synthproof.cli import _load, main

    # 1. _load with toy
    ds, src = _load(None, None, rows=10, seed=42)
    assert ds.num_rows == 10
    assert src == "declared"

    # 2. _load with schema
    import pandas as pd

    from synthproof.data.schema import Schema

    csv_file = tmp_path / "data.csv"
    pd.DataFrame({"x": [1.0, 2.0], "y": ["a", "b"]}).to_csv(csv_file, index=False)
    schema_file = tmp_path / "schema.json"
    s = Schema.infer_nonprivate(pd.read_csv(csv_file))
    schema_file.write_text(s.to_json(), encoding="utf-8")

    ds2, src2 = _load(str(csv_file), str(schema_file), rows=2, seed=42)
    assert ds2.num_rows == 2
    assert src2 == "declared"

    runner = CliRunner()

    # 3. mechanisms command when aim is missing
    with patch("synthproof.cli.MECHANISMS", {"independent": None, "pairwise": None}):
        res = runner.invoke(main, ["mechanisms"])
        assert res.exit_code == 0
        assert "Unavailable: aim" in res.output

    # 4. prototype command import error
    with patch.dict("sys.modules", {"run_prototype": None}):
        res_proto = runner.invoke(main, ["prototype"])
        assert res_proto.exit_code != 0
        assert "needs the launcher script" in res_proto.output
