"""The release-boundary auditor: does it find every channel outside epsilon, and only real ones?

synthproof/audit/boundary.py reads a published artefact and reports what it discloses beyond the
headline epsilon. The tests are adversarial in both directions: a clean sheet must raise no leak,
and each defect the module names must be reintroduced and caught. A checker whose failure paths are
never exercised is one nobody has reason to trust.
"""

import json

import numpy as np
import pandas as pd
import pytest
from click.testing import CliRunner

from synthproof.audit import boundary
from synthproof.cli import main
from synthproof.data.dataset import TabularDataset
from synthproof.data.schema import CATEGORICAL, NUMERICAL, ColumnSpec, Schema
from synthproof.frontier import croissant as croissant_mod
from synthproof.frontier.certificate import FrontierEngine
from synthproof.ledger import signing


def _table(n=1200, seed=0):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(
        {
            "age": rng.integers(18, 90, n).astype(float),
            "region": rng.choice(list("abcdefgh"), n),
            "dx": rng.choice(["x", "y", "z"], n),
        }
    )
    schema = Schema(
        [
            ColumnSpec("age", NUMERICAL, lower=0.0, upper=120.0),
            ColumnSpec("region", CATEGORICAL, categories=list("abcdefgh")),
            ColumnSpec("dx", CATEGORICAL, categories=["x", "y", "z"]),
        ]
    )
    return TabularDataset(df, name="boundary", schema=schema)


@pytest.fixture
def keys(tmp_path, monkeypatch):
    monkeypatch.setenv("SYNTHPROOF_KEY_DIR", str(tmp_path / "keys"))
    signing.generate_keypair()
    return signing.load_fingerprint_key(create=True)


def _clean_sheet(keys):
    """A sheet from the current, fixed pipeline: declared size, keyed fingerprint, no seed."""
    sheet = FrontierEngine(seed=7).run_sweep(
        _table(),
        eps_grid=[1.0],
        mechanism="independent",
        num_canaries=10,
        release_rows=800,
        fingerprint_key=keys,
    )
    signing.sign_datasheet(sheet)
    return sheet


# ------------------------------------------------------------------ a clean release


def test_a_current_release_has_no_open_channel(keys):
    report = boundary.audit_sheet(_clean_sheet(keys).to_dict())
    assert report.passed, [f.to_dict() for f in report.leaks]
    # It still names what only the producer's honesty settles: a declared size cannot be checked.
    codes = {f.code: f.severity for f in report.findings}
    assert codes["RB2"] == boundary.UNVERIFIABLE  # declared size
    assert codes["RB1"] == boundary.NOTE  # seed withheld
    assert codes["RB4"] == boundary.NOTE  # evaluation labelled


def test_the_clean_croissant_record_also_passes(keys):
    record = croissant_mod.to_croissant(_clean_sheet(keys))
    report = boundary.audit_croissant(record)
    assert report.passed, [f.to_dict() for f in report.leaks]


# ------------------------------------------------------------------ each leak, reintroduced


def test_a_published_seed_is_a_leak(keys):
    sheet = _clean_sheet(keys).to_dict()
    sheet["seed"] = 1234567
    report = boundary.audit_sheet(sheet)
    assert not report.passed
    rb1 = next(f for f in report.leaks if f.code == "RB1")
    assert "1234567" in rb1.finding and "15 of 15" in rb1.consequence


def test_an_exact_row_count_with_no_basis_is_a_leak(keys):
    sheet = _clean_sheet(keys).to_dict()
    del sheet["release_rows_source"]
    report = boundary.audit_sheet(sheet)
    assert any(f.code == "RB2" and f.severity == boundary.LEAK for f in report.findings)


def test_a_dp_count_with_no_charge_is_a_leak(keys):
    sheet = _clean_sheet(keys).to_dict()
    sheet["release_rows_source"] = "dp_count"
    sheet["release_rows_eps"] = 0.0
    report = boundary.audit_sheet(sheet)
    rb2 = next(f for f in report.findings if f.code == "RB2")
    assert rb2.severity == boundary.LEAK and "uncharged" in rb2.consequence.lower()


def test_a_legacy_unkeyed_fingerprint_is_a_leak():
    """A 64-hex fingerprint on a sheet that predates release_rows_source is an unkeyed SHA-256."""
    legacy = {
        "num_rows": 6000,
        "input_fingerprint": "a" * 64,
        "total_proved_eps": 7.0,
    }
    report = boundary.audit_sheet(legacy)
    assert any(f.code == "RB3" and f.severity == boundary.LEAK for f in report.findings)


def test_unlabelled_evaluation_is_a_leak(keys):
    sheet = _clean_sheet(keys).to_dict()
    del sheet["evaluation_privacy"]
    report = boundary.audit_sheet(sheet)
    rb4 = next(f for f in report.findings if f.code == "RB4")
    assert rb4.severity == boundary.LEAK


def test_an_under_reporting_accountant_is_a_leak(keys):
    sheet = _clean_sheet(keys).to_dict()
    sheet["accountant_agreement"] = {"verdict": "under_report"}
    report = boundary.audit_sheet(sheet)
    assert any(f.code == "RB5" and f.severity == boundary.LEAK for f in report.findings)


def test_an_inferred_domain_is_a_leak(keys):
    sheet = _clean_sheet(keys).to_dict()
    sheet["domain_source"] = "inferred-nonprivate"
    report = boundary.audit_sheet(sheet)
    assert any(f.code == "RB6" and f.severity == boundary.LEAK for f in report.findings)


# ------------------------------------------------------------------ Croissant-only channels


def test_a_seed_in_croissant_provenance_is_caught_even_if_the_sheet_hid_it(keys):
    """The provenance layer is outside the signature, so a seed there is a real, separate leak."""
    record = croissant_mod.to_croissant(_clean_sheet(keys))
    record.setdefault("prov:wasGeneratedBy", {})["dp:seed"] = 99
    report = boundary.audit_croissant(record)
    rb1 = next(f for f in report.leaks if f.code == "RB1")
    assert "provenance" in rb1.finding.lower() and "99" in rb1.finding


def test_a_sha256_labelled_fingerprint_in_provenance_is_a_leak(keys):
    record = croissant_mod.to_croissant(_clean_sheet(keys))
    prov = record.setdefault("prov:wasGeneratedBy", {})
    prov.setdefault("prov:used", {})["dp:inputFingerprintSha256"] = "b" * 64
    report = boundary.audit_croissant(record)
    assert any(f.code == "RB3" and f.severity == boundary.LEAK for f in report.leaks)


# ------------------------------------------------------------------ the CLI


def test_the_cli_passes_a_clean_sheet_and_fails_a_leaky_one(keys, tmp_path):
    clean = tmp_path / "clean.json"
    clean.write_text(_clean_sheet(keys).to_json(), encoding="utf-8")
    r = CliRunner().invoke(main, ["boundary-audit", str(clean)])
    assert r.exit_code == 0, r.output
    assert "PASSED" in r.output

    leaky = json.loads(clean.read_text(encoding="utf-8"))
    leaky["seed"] = 42
    leaky_path = tmp_path / "leaky.json"
    leaky_path.write_text(json.dumps(leaky), encoding="utf-8")
    r = CliRunner().invoke(main, ["boundary-audit", str(leaky_path)])
    assert r.exit_code == 1
    assert "FAILED" in r.output and "RB1" in r.output


def test_the_cli_emits_json(keys, tmp_path):
    p = tmp_path / "s.json"
    p.write_text(_clean_sheet(keys).to_json(), encoding="utf-8")
    r = CliRunner().invoke(main, ["boundary-audit", str(p), "--json"])
    assert r.exit_code == 0, r.output
    payload = json.loads(r.output)
    assert payload["passed"] is True
    assert payload["artefact"] == "privacy-data-sheet"


def _codes(sheet):
    return {f.code: f for f in boundary.audit_sheet(sheet).findings}


def test_rb8_public_invariants_declared_vs_undeclared():
    """RB8: an invariant declared outside epsilon WITH a basis is a sound label (note); WITHOUT a
    basis it cannot be told from an uncharged private statistic (unverifiable)."""
    ok = _codes({"public_invariants": [{"name": "state_total", "basis": "statutory"}]})
    assert "RB8" in ok and ok["RB8"].severity == boundary.NOTE
    # reintroduce the defect: drop the basis
    bad = _codes({"public_invariants": ["state_total", "structural_zero"]})
    assert bad["RB8"].severity == boundary.UNVERIFIABLE
    # absent -> no RB8 finding at all
    assert "RB8" not in _codes({"num_rows": 1})


def test_rb9_discretization_source():
    """RB9: bins read from the data (uncharged) are a leak; public/charged bins are sound."""
    assert "RB9" not in _codes({"discretization_source": "uniform-public"})
    assert "RB9" not in _codes({"discretization_source": "dp-charged"})
    leak = _codes({"discretization_source": "data-derived"})
    assert leak["RB9"].severity == boundary.LEAK
    unknown = _codes({"discretization_source": "quantile-magic"})
    assert unknown["RB9"].severity == boundary.UNVERIFIABLE
    assert "RB9" not in _codes({})  # not stated / not applicable


def test_rb10_amplification_disclosure():
    """RB10: a claimed amplification with no stated basis is a leak; with a basis it is a note."""
    leak = _codes({"privacy_amplification": {"factor": 0.3}})
    assert leak["RB10"].severity == boundary.LEAK
    ok = _codes({"privacy_amplification": {"factor": 0.3, "basis": "poisson-subsampling q=0.01"}})
    assert ok["RB10"].severity == boundary.NOTE
    assert "RB10" not in _codes({})


def test_rb3_declared_keyed_scheme_is_verifiable_not_unverifiable():
    """RB3 improvement (2026-09-17): a declared keyed scheme WITH a named key is checkable
    accountability (note), not the old blanket 'unverifiable'. This is the whole point -- it
    moves the common honest case out of unverifiable."""
    keyed = _codes(
        {
            "input_fingerprint": "a" * 64,
            "fingerprint_scheme": "hmac-sha256",
            "fingerprint_key_id": "curator-key-2026",
            "release_rows_source": "declared",
        }
    )
    assert keyed["RB3"].severity == boundary.NOTE


def test_rb3_declared_keyed_scheme_without_a_key_is_not_bound():
    """A keyed scheme with no named key binds nothing -> still unverifiable, never a note."""
    unbound = _codes(
        {
            "input_fingerprint": "a" * 64,
            "fingerprint_scheme": "hmac-sha256",
            "release_rows_source": "declared",
        }
    )
    assert unbound["RB3"].severity == boundary.UNVERIFIABLE


def test_rb3_self_declared_unkeyed_hash_is_a_leak_regardless_of_legacy():
    """REINTRODUCE the leak by declaration: a sheet that says its fingerprint is plain sha256 is
    a self-declared membership test, caught even on a modern (non-legacy) sheet."""
    declared = _codes(
        {
            "input_fingerprint": "a" * 64,
            "fingerprint_scheme": "sha256",
            "release_rows_source": "declared",  # NOT legacy; the old heuristic would miss it
        }
    )
    assert declared["RB3"].severity == boundary.LEAK


def test_rb3_unrecognised_scheme_is_unverifiable():
    bad = _codes({"input_fingerprint": "a" * 64, "fingerprint_scheme": "rot13-magic"})
    assert bad["RB3"].severity == boundary.UNVERIFIABLE


# --------------------------------------------------------------------------- multi-table RB11-14


def test_single_table_sheet_has_no_relational_findings():
    """RB11-14 must stay silent on an ordinary single-table sheet (no relational fields set)."""
    codes = _codes({"num_rows": 6000, "total_proved_eps": 7.0})
    for c in ("RB11", "RB12", "RB13", "RB14"):
        assert c not in codes


def test_rb11_relational_unit_row_and_missing_are_leaks_entity_is_clean():
    """RB11: a multi-table release must declare an entity-level unit; 'row' or none is a leak."""
    missing = _codes({"tables": ["patients", "admissions"]})
    assert missing["RB11"].severity == boundary.LEAK
    row = _codes({"tables": ["patients", "admissions"], "relational_unit": "row"})
    assert row["RB11"].severity == boundary.LEAK
    ok = _codes({"tables": ["patients", "admissions"], "relational_unit": "entity"})
    assert "RB11" not in ok  # entity is sound -> no finding
    weird = _codes({"tables": ["patients"], "relational_unit": "household-ish"})
    assert weird["RB11"].severity == boundary.UNVERIFIABLE


def test_rb12_fk_degree_source():
    """RB12: a foreign-key degree distribution read off the data (uncharged) is a leak."""
    leak = _codes({"fk_degree_source": "data-derived"})
    assert leak["RB12"].severity == boundary.LEAK
    assert "RB12" not in _codes({"fk_degree_source": "dp-charged"})
    assert "RB12" not in _codes({"fk_degree_source": "uniform-public"})
    assert _codes({"fk_degree_source": "mystery"})["RB12"].severity == boundary.UNVERIFIABLE
    assert "RB12" not in _codes({})


def test_rb13_join_cardinality_source():
    """RB13: exact join/per-table counts read off the data are private under an entity neighbour."""
    leak = _codes({"join_cardinality_source": "data-derived"})
    assert leak["RB13"].severity == boundary.LEAK
    assert "RB13" not in _codes({"join_cardinality_source": "declared"})
    assert "RB13" not in _codes({"join_cardinality_source": "dp-charged"})
    assert _codes({"join_cardinality_source": "guess"})["RB13"].severity == boundary.UNVERIFIABLE
    assert "RB13" not in _codes({})


def test_rb14_cross_table_fingerprint_mirrors_rb3():
    """RB14: a cross-table linkage hash -- keyed+named is bound (note), unkeyed is a leak."""
    keyed = _codes(
        {
            "cross_table_fingerprint": "b" * 64,
            "cross_table_fingerprint_scheme": "hmac-sha256",
            "cross_table_fingerprint_key_id": "curator-key-2026",
        }
    )
    assert keyed["RB14"].severity == boundary.NOTE
    unkeyed = _codes(
        {"cross_table_fingerprint": "b" * 64, "cross_table_fingerprint_scheme": "sha256"}
    )
    assert unkeyed["RB14"].severity == boundary.LEAK
    no_scheme = _codes({"cross_table_fingerprint": "b" * 64})
    assert no_scheme["RB14"].severity == boundary.UNVERIFIABLE
    assert "RB14" not in _codes({})
