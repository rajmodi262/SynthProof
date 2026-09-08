"""Tests for the Croissant emitter.

The interesting tests here are the negative controls. A signature over an embedded node is
easy to get right; what is easy to get WRONG is the layer above it, which the signature does
not cover. `test_tampered_mirror_is_refused_despite_valid_signature` is the test that earns
this module's place — it constructs a record that is internally honest, correctly signed, and
still tells a reader the wrong epsilon, and asserts we refuse it.

Per the project's standing rules every measurement here ships with a positive and a negative
control, and each negative control was verified by making it fail first.
"""

import json
import pathlib
import subprocess
import sys

import pytest

from synthproof.frontier import croissant as croissant_mod
from synthproof.frontier.certificate import PrivacyDataSheet
from synthproof.ledger import signing

# --------------------------------------------------------------------------- fixtures


def _sheet(**overrides) -> PrivacyDataSheet:
    """A data sheet with the shape a real release has."""
    kwargs = dict(
        dataset_name="adult",
        num_rows=6000,
        mechanism="aim",
        mechanism_available=True,
        delta=1e-5,
        seed=42,
        target_column="income",
        total_proved_eps=7.356,
        total_audited_eps=0.0,
        frontier_curve=[],
        ledger_hash="a" * 64,
        audit_ceiling=2.972,
        # The ceiling travels with the series that produced it: 2.972 is the ONE-RUN value at
        # m=60, not the paired Clopper-Pearson one. See synthproof/audit/ceiling.py.
        audit_estimator="one_run",
        audit_budget=60,
        audit_alpha=0.05,
        input_fingerprint="b" * 64,
        domain_source="declared",
        attacks_run=["singling_out", "linkability", "attribute_inference", "domias", "mia"],
        attacks_not_implemented=["LiRA"],
    )
    kwargs.update(overrides)
    return PrivacyDataSheet(**kwargs)


@pytest.fixture
def keys(tmp_path, monkeypatch):
    """A throwaway keypair, isolated from the repository's real `.keys/`."""
    monkeypatch.setenv("SYNTHPROOF_KEY_DIR", str(tmp_path / "keys"))
    priv, pub = signing.generate_keypair()
    return priv, pub


@pytest.fixture
def signed_record(keys):
    """A signed sheet already wrapped in a Croissant record."""
    sheet = _sheet()
    signing.sign_datasheet(sheet)
    return croissant_mod.to_croissant(sheet), keys[1]


# --------------------------------------------------------------------------- positive control


def test_signed_sheet_round_trips_and_verifies(signed_record):
    """POSITIVE CONTROL. An untampered record must verify."""
    record, pub = signed_record
    assert croissant_mod.verify_croissant(record, key_path=pub) is True


def test_record_survives_json_serialisation(signed_record):
    """The signature must survive being written to disk and read back.

    This is not ceremony: the signature covers a canonical serialisation of the embedded
    node, so any transformation that reorders or retypes its members breaks it. Emitting
    through `to_json` and parsing back is exactly what a third-party verifier does.
    """
    record, pub = signed_record
    reparsed = json.loads(croissant_mod.to_json(record))
    assert croissant_mod.verify_croissant(reparsed, key_path=pub) is True


def test_structure_validates(signed_record):
    """POSITIVE CONTROL for the structural checker."""
    record, _ = signed_record
    problems = [p for p in croissant_mod.validate_structure(record) if not p.startswith("NOTE:")]
    assert problems == [], problems


def test_conforms_to_croissant_1_1(signed_record):
    record, _ = signed_record
    assert record["conformsTo"] == "http://mlcommons.org/croissant/1.1"
    assert record["@type"] == "sc:Dataset"
    assert record["@context"]["dp"] == croissant_mod.DP_NAMESPACE
    assert "cr" in record["@context"]
    assert "prov" in record["@context"]


# --------------------------------------------------------------------------- negative controls


def test_tampered_mirror_is_refused_despite_valid_signature(signed_record):
    """NEGATIVE CONTROL, and the reason this module cross-checks at all.

    The attack: leave the signed sheet untouched so the signature still verifies, and edit
    only the human-visible epsilon that every reader and every piece of general-purpose
    Croissant tooling will actually look at. Signature-only verification passes this record.
    """
    record, pub = signed_record
    record["dp:epsilonProved"] = 0.5  # the sheet still says 7.356

    # The signature alone is still perfectly valid -- that is what makes this dangerous.
    assert signing.verify_datasheet(record["dp:privacyDataSheet"], key_path=pub) is True

    with pytest.raises(croissant_mod.CroissantError) as exc:
        croissant_mod.verify_croissant(record, key_path=pub)

    assert "SIGNATURE VALID, RECORD UNTRUSTWORTHY" in str(exc.value)
    assert "dp:epsilonProved" in str(exc.value)


@pytest.mark.parametrize("field", sorted(croissant_mod.MIRRORED_FIELDS))
def test_every_mirrored_field_is_cross_checked(signed_record, field):
    """NEGATIVE CONTROL over the whole mirror, not just the field we thought of.

    Parametrised so that adding a field to `MIRRORED_FIELDS` without it being genuinely
    checked fails here rather than shipping as an unguarded surface.
    """
    record, pub = signed_record
    record[field] = "TAMPERED-SENTINEL"

    with pytest.raises(croissant_mod.CroissantError) as exc:
        croissant_mod.verify_croissant(record, key_path=pub)
    assert field in str(exc.value)


def test_tampered_sheet_fails_the_signature(signed_record):
    """NEGATIVE CONTROL. Editing the signed node must break the signature itself."""
    record, pub = signed_record
    record["dp:privacyDataSheet"]["total_proved_eps"] = 0.5

    with pytest.raises(signing.SignatureError):
        croissant_mod.verify_croissant(record, key_path=pub)


def test_unsigned_sheet_is_refused(tmp_path, monkeypatch):
    """An unsigned sheet must not be emitted under a vocabulary advertising attestation."""
    with pytest.raises(croissant_mod.CroissantError) as exc:
        croissant_mod.to_croissant(_sheet())
    assert "unsigned" in str(exc.value).lower()
    assert "--sign" in str(exc.value)


def test_record_without_sheet_is_refused(keys):
    """An ordinary Croissant record carries nothing to verify, and must say so."""
    with pytest.raises(croissant_mod.CroissantError) as exc:
        croissant_mod.verify_croissant({"@type": "sc:Dataset"}, key_path=keys[1])
    assert "no `dp:privacyDataSheet`" in str(exc.value)


def test_wrong_key_is_refused(signed_record, tmp_path, monkeypatch):
    """A record signed by one key must not verify against another."""
    record, _ = signed_record
    monkeypatch.setenv("SYNTHPROOF_KEY_DIR", str(tmp_path / "other"))
    _, other_pub = signing.generate_keypair()

    with pytest.raises(signing.SignatureError):
        croissant_mod.verify_croissant(record, key_path=other_pub)


# --------------------------------------------------------------------------- the audit ceiling

# S1 in the novelty verdict -- the surviving claim. These tests pin the behaviour that makes
# it a claim rather than a slogan: the record must say, in words, when its own audited
# epsilon could not have been anything else.


def test_uninformative_audit_is_labelled_uninformative(keys):
    """Ceiling 2.972 below proved 7.356 -- the real H1 configuration."""
    sheet = _sheet(audit_ceiling=2.972, total_proved_eps=7.356, total_audited_eps=0.0)
    signing.sign_datasheet(sheet)
    record = croissant_mod.to_croissant(sheet)

    assert record["dp:auditIsInformative"] is False
    note = record["dp:auditInterpretation"]
    assert note.startswith("UNINFORMATIVE")
    assert "2.972" in note and "7.356" in note
    assert "NOT evidence that the mechanism leaks less" in note
    assert "Steinke" in note  # the ceiling is their corollary and must be attributed


def test_informative_audit_is_labelled_informative(keys):
    """A ceiling above the proved epsilon means the number carries weight."""
    sheet = _sheet(audit_ceiling=5.5, total_proved_eps=1.0, total_audited_eps=0.8)
    signing.sign_datasheet(sheet)
    record = croissant_mod.to_croissant(sheet)

    assert record["dp:auditIsInformative"] is True
    assert record["dp:auditInterpretation"].startswith("INFORMATIVE")


def test_absent_ceiling_is_named_not_omitted(keys):
    """A missing ceiling must be reported as missing, never left blank.

    Standing rule: where a capability does not exist, name it as absent rather than omitting
    it. An absent ceiling silently dropped would leave an audited epsilon looking like a
    measurement.

    NOTE: this covers a sheet that reports NO audited epsilon. A sheet that DOES report one
    and omits the ceiling is refused outright -- see the test below. The two rules do not
    conflict: name what is absent, but never publish a number whose reach is unknown.
    """
    sheet = _sheet(audit_ceiling=None, total_audited_eps=None)
    signing.sign_datasheet(sheet)
    record = croissant_mod.to_croissant(sheet)

    assert record["dp:auditIsInformative"] is False
    assert record["dp:auditInterpretation"].startswith("NOT REPORTED")
    assert "dp:auditCeiling" in " ".join(croissant_mod.validate_structure(record))


@pytest.mark.parametrize(
    "dropped", ["audit_ceiling", "audit_estimator", "audit_budget", "audit_alpha"]
)
def test_an_audited_epsilon_without_its_reach_is_refused(keys, dropped):
    """The enforceable half of the project's central claim.

    An audited 0.0 that means "nothing leaked" and an audited 0.0 that means "the instrument
    could not have seen anything" are indistinguishable to a reader. This project published
    exactly that confusion: eps_audited 0.000 against eps_proved 7.36, where 60 canaries capped
    the auditor at 2.97. The record is where the number would leave the project, so it is
    refused here rather than annotated.

    Parametrised over all four fields because the ceiling alone is not enough: three ceiling
    series live in this repo, in two units, and a reader who cannot tell which one produced the
    number cannot check it.
    """
    sheet = _sheet(**{dropped: None})
    signing.sign_datasheet(sheet)
    with pytest.raises(croissant_mod.CroissantError, match=dropped):
        croissant_mod.to_croissant(sheet)


# --------------------------------------------------------------------------- honesty of framing


def test_vocabulary_is_not_claimed_as_a_standard(signed_record):
    """The dp: namespace is ours. The record must not imply external authority."""
    record, _ = signed_record
    status = record["dp:vocabularyStatus"]
    assert "NOT A REGISTERED VOCABULARY" in status
    assert "carry no external authority" in status or "no external authority" in status


def test_signature_scope_is_stated(signed_record):
    """A reader must be able to learn what the signature does and does not cover."""
    record, _ = signed_record
    sig = record["dp:signature"]
    assert "does NOT cover the JSON-LD framing" in sig["dp:covers"]
    assert "does NOT prove the epsilon is correct" in sig["dp:proves"]
    assert sig["dp:algorithm"] == "Ed25519"


def test_unimplemented_attacks_are_carried(signed_record):
    """LiRA's absence is a recorded decision and must travel with the release."""
    record, _ = signed_record
    assert "LiRA" in record["dp:attacksNotImplemented"]
    assert "LiRA" not in record["dp:attacksRun"]


def test_illegal_dataset_name_is_refused(keys):
    """Croissant constrains `name`. A name with nothing legal in it is an error, not a guess."""
    sheet = _sheet(dataset_name="!!!")
    signing.sign_datasheet(sheet)
    with pytest.raises(croissant_mod.CroissantError):
        croissant_mod.to_croissant(sheet)


def test_name_is_slugified(keys):
    sheet = _sheet(dataset_name="UCI Adult (2026 release)")
    signing.sign_datasheet(sheet)
    record = croissant_mod.to_croissant(sheet)
    assert record["name"] == "UCI-Adult-2026-release"
    assert not croissant_mod._NAME_RE.search(record["name"])


def test_record_set_is_built_when_columns_given(keys):
    sheet = _sheet()
    signing.sign_datasheet(sheet)
    record = croissant_mod.to_croissant(
        sheet,
        data_url="https://example.org/adult-synth.csv",
        data_sha256="ef" * 32,
        columns=[{"name": "age", "dataType": "sc:Integer"}, {"name": "income"}],
    )
    assert record["recordSet"][0]["field"][0]["name"] == "age"
    assert record["recordSet"][0]["field"][0]["dataType"] == "sc:Integer"
    assert record["distribution"][0]["encodingFormat"] == "text/csv"


def test_no_content_url_is_fabricated(signed_record):
    """Omitting `distribution` beats inventing a URL that resolves to nothing."""
    record, _ = signed_record
    assert "distribution" not in record


# --------------------------------------------------------------------------- record set

# The reference validator rejected our first record set: a Croissant field must declare where
# its values come from. These pin the fix so it cannot silently regress into an invalid record
# that only our own structural check accepts.


def test_record_set_fields_declare_a_source(keys):
    sheet = _sheet()
    signing.sign_datasheet(sheet)
    record = croissant_mod.to_croissant(
        sheet,
        data_url="adult-synth.csv",
        data_sha256="cd" * 32,
        columns=[{"name": "age", "dataType": "sc:Integer"}],
    )
    field = record["recordSet"][0]["field"][0]
    assert field["source"]["fileObject"]["@id"] == "adult-data"
    assert field["source"]["extract"]["column"] == "age"


def test_columns_without_data_url_omit_the_record_set_and_say_why(keys):
    """An invalid record set is worse than none, and a silent drop hides the reason."""
    sheet = _sheet()
    signing.sign_datasheet(sheet)
    record = croissant_mod.to_croissant(sheet, columns=[{"name": "age"}])

    assert "recordSet" not in record
    assert "must reference the file it comes from" in record["dp:recordSetOmitted"]


def test_data_checksum_is_carried_when_supplied(keys):
    sheet = _sheet()
    signing.sign_datasheet(sheet)
    record = croissant_mod.to_croissant(sheet, data_url="x.csv", data_sha256="ab" * 32)
    assert record["distribution"][0]["sha256"] == "ab" * 32


def test_context_carries_every_standard_croissant_key(signed_record):
    """A partial @context validates but makes the reference validator warn on every load.

    The key set is copied from `mlcroissant`'s own `make_context()`; this pins that we ship
    the whole thing plus our two extension prefixes, not a convenient subset.
    """
    record, _ = signed_record
    ctx = record["@context"]
    for key in ("citeAs", "dct", "rai", "jsonPath", "subField", "transform", "examples"):
        assert key in ctx, f"@context is missing the standard key {key!r}"
    assert ctx["conformsTo"] == "dct:conformsTo"
    assert ctx["prov"] == "http://www.w3.org/ns/prov#"


def test_date_published_is_never_invented(keys):
    """The emitter must not reach for a clock. A caller supplies the date or there is none."""
    sheet = _sheet()
    signing.sign_datasheet(sheet)

    assert "datePublished" not in croissant_mod.to_croissant(sheet)
    assert "datePublished" in " ".join(
        croissant_mod.validate_structure(croissant_mod.to_croissant(sheet))
    )

    dated = croissant_mod.to_croissant(sheet, date_published="2026-08-23")
    assert dated["datePublished"] == "2026-08-23"


def test_citation_and_cite_as_agree(signed_record):
    record, _ = signed_record
    assert record["citation"] == record["citeAs"]


# --------------------------------------------------------------------------- column helpers


def test_columns_from_schema_maps_kinds(keys):
    from synthproof.data.schema import CATEGORICAL, NUMERICAL, ColumnSpec, Schema

    schema = Schema(
        columns=[
            ColumnSpec(name="age", kind=NUMERICAL, lower=0, upper=100),
            ColumnSpec(name="city", kind=CATEGORICAL, categories=["a", "b"]),
        ]
    )
    cols = croissant_mod.columns_from_schema(schema)
    assert cols == [
        {"name": "age", "dataType": "sc:Float"},
        {"name": "city", "dataType": "sc:Text"},
    ]


def test_columns_from_schema_carries_no_bounds_or_categories(keys):
    """A declared bound is public, but it has no business in the record set silently.

    The record set describes column NAMES and KINDS. If this ever starts emitting `lower`,
    `upper` or `categories`, a release built from an `inferred-nonprivate` schema would put
    data-derived values into the record without them being charged or flagged.
    """
    from synthproof.data.schema import NUMERICAL, ColumnSpec, Schema

    schema = Schema(columns=[ColumnSpec(name="age", kind=NUMERICAL, lower=17, upper=90)])
    emitted = json.dumps(croissant_mod.columns_from_schema(schema))
    assert "17" not in emitted and "90" not in emitted


def test_columns_from_dataframe_maps_dtypes():
    import pandas as pd

    df = pd.DataFrame({"i": [1], "f": [1.5], "s": ["x"], "b": [True]})
    got = {c["name"]: c["dataType"] for c in croissant_mod.columns_from_dataframe(df)}
    assert got == {
        "i": "sc:Integer",
        "f": "sc:Float",
        "s": "sc:Text",
        "b": "sc:Boolean",
    }


# --------------------------------------------------------------------------- the release itself

# `retain_release` decides WHICH table the CLI writes out. There are two candidates in every
# cell and one of them must never leave the building: `_audit_synth` is fitted on a split with
# canaries planted in it, so shipping it would release the canaries. This is the highest-stakes
# line in the whole feature and it is one dictionary key wide.


def test_retained_release_is_the_canary_free_one():
    """SAFETY-CRITICAL. `last_release` must be `_synth`, never `_audit_synth`.

    Compared against a real `run_cell` at the same seed rather than against a description of
    one, so a change to the key picks this up as a difference in the data itself.
    """
    import pandas as pd

    from synthproof.data.dataset import TabularDataset
    from synthproof.frontier.certificate import FrontierEngine
    from synthproof.frontier.experiment import run_cell

    ds = TabularDataset.create_synthetic_toy(num_rows=600, seed=7)

    engine = FrontierEngine(seed=7)
    engine.run_sweep(
        ds, eps_grid=[1.0], mechanism="independent", num_canaries=10, retain_release=True
    )

    res = run_cell(
        ds, "independent", 1.0, seed=7, delta=1e-5, num_canaries=10, return_artifacts=True
    )

    assert engine.last_release is not None
    pd.testing.assert_frame_equal(
        engine.last_release.reset_index(drop=True),
        res["_synth"].reset_index(drop=True),
        obj="last_release must equal the canary-free utility release",
    )

    # And it must NOT be the audit release. If these two ever coincide the test above stops
    # discriminating, so assert the premise rather than assuming it.
    audit = res["_audit_synth"].reset_index(drop=True)
    same = engine.last_release.reset_index(drop=True).equals(audit)
    assert not same, "the audit and utility releases are identical; this test proves nothing"


def test_release_is_not_retained_by_default():
    """Off by default. A grid sweeping many epsilons has no use for held releases."""
    from synthproof.data.dataset import TabularDataset
    from synthproof.frontier.certificate import FrontierEngine

    ds = TabularDataset.create_synthetic_toy(num_rows=600, seed=7)
    engine = FrontierEngine(seed=7)
    engine.run_sweep(ds, eps_grid=[1.0], mechanism="independent", num_canaries=10)
    assert engine.last_release is None


# --------------------------------------------------------------------------- reference validator

# The real MLCommons validator cannot run in this environment (see the module docstring), so
# this test SKIPS rather than passes when the isolated env has not been built. A skip is
# visible in the report; a silent pass would be a check that never ran.

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
_VALIDATOR = _REPO_ROOT / ".venv-croissant"
_VALIDATOR_PY = _VALIDATOR / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


@pytest.mark.skipif(
    not _VALIDATOR_PY.exists(),
    reason="isolated mlcroissant env absent; run `python scripts/validate_croissant.py --setup`",
)
def test_emitted_record_passes_the_official_validator(keys, tmp_path):
    """The record we emit must satisfy the reference implementation, not just our own checker."""
    sheet = _sheet()
    signing.sign_datasheet(sheet)
    record = croissant_mod.to_croissant(
        sheet,
        data_url="adult-synth.csv",
        data_sha256="cd" * 32,
        columns=[{"name": "age", "dataType": "sc:Integer"}, {"name": "income"}],
        date_published="2026-08-23",
    )
    path = tmp_path / "record.json"
    path.write_text(croissant_mod.to_json(record), encoding="utf-8")

    proc = subprocess.run(
        [sys.executable, str(_REPO_ROOT / "scripts" / "validate_croissant.py"), str(path)],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
    )
    assert proc.returncode == 0, f"validator rejected the record:\n{proc.stdout}\n{proc.stderr}"
    assert "VALIDATED" in proc.stdout
    assert "warnings    0" in proc.stdout


def test_data_url_without_checksum_is_refused(keys):
    """NEGATIVE CONTROL. A named data file with no checksum can be swapped underneath a
    signature that still verifies, so the emitter refuses rather than producing it."""
    sheet = _sheet()
    signing.sign_datasheet(sheet)
    with pytest.raises(croissant_mod.CroissantError) as exc:
        croissant_mod.to_croissant(sheet, data_url="adult-synth.csv")
    assert "data_sha256" in str(exc.value)


# --------------------------------------------------------------------------- validate_structure

# A validator whose failure paths are never exercised is a validator nobody has reason to
# trust. These drive each branch by breaking a known-good record one property at a time.


@pytest.mark.parametrize(
    "mutate, expected",
    [
        (lambda r: r.pop("name"), "missing required property `name`"),
        (lambda r: r.pop("description"), "missing required property `description`"),
        (lambda r: r.pop("conformsTo"), "missing required property `conformsTo`"),
        (lambda r: r.update({"@type": "sc:Thing"}), "must be `sc:Dataset`"),
        (lambda r: r.update({"conformsTo": "croissant/0.9"}), "`conformsTo` must be"),
        (lambda r: r.update({"name": "not a token!"}), "characters Croissant does not allow"),
        (lambda r: r["@context"].pop("dp"), "does not bind the `dp:` prefix"),
        (lambda r: r["@context"].pop("cr"), "does not bind the `cr:` (Croissant) prefix"),
        (lambda r: r.update({"@context": "https://schema.org"}), "`@context` must be an object"),
        (lambda r: r.pop("dp:privacyDataSheet"), "not a SynthProof release record"),
        (lambda r: r.update({"dp:signature": {}}), "carries no signature"),
        (lambda r: r.update({"dp:auditCeiling": None}), "`dp:auditCeiling` is absent"),
    ],
)
def test_validate_structure_reports_each_defect(signed_record, mutate, expected):
    record, _ = signed_record
    mutate(record)
    assert any(
        expected in p for p in croissant_mod.validate_structure(record)
    ), f"validate_structure did not report {expected!r}"


def test_validate_structure_reports_several_at_once(signed_record):
    """Problems are collected, not raised on the first one -- a caller wants the whole list."""
    record, _ = signed_record
    record.pop("name")
    record.pop("description")
    record["@type"] = "sc:Thing"
    assert len(croissant_mod.validate_structure(record)) >= 3


# --------------------------------------------------------------------------- input handling


def test_accepts_a_parsed_sheet_dict(keys):
    """`to_croissant` takes a dataclass or a sheet already loaded from JSON."""
    sheet = _sheet()
    signing.sign_datasheet(sheet)
    from_obj = croissant_mod.to_croissant(sheet)
    from_dict = croissant_mod.to_croissant(json.loads(sheet.to_json()))
    assert from_dict["dp:privacyDataSheet"] == from_obj["dp:privacyDataSheet"]


def test_rejects_something_that_is_not_a_sheet():
    with pytest.raises(croissant_mod.CroissantError) as exc:
        croissant_mod.to_croissant("a string is not a data sheet")
    assert "Expected a PrivacyDataSheet" in str(exc.value)


def test_mirror_check_skips_fields_the_record_does_not_carry(signed_record):
    """A record that omits a mirrored field is inconsistent, not tampered.

    `verify_croissant` compares only fields that are present. Dropping one entirely is a
    different failure from altering it, and must not be reported as tampering.
    """
    record, pub = signed_record
    del record["dp:mechanism"]
    assert croissant_mod.verify_croissant(record, key_path=pub) is True
