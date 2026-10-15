"""Meaning tests: every number a release reports must agree with every other place it appears,
with an independent recomputation, and with what was signed.

WHY THIS FILE EXISTS. 1,082 tests passed while the console drew a correlation matrix from a
sin() formula, two figures were hard-coded, and a curve labelled "empirical" was never fitted
(fixed in v1.3.1). Each layer was tested on its own and every layer was "correct"; the defect
was that the number shown was not the number measured. A unit test cannot see that. These tests
run real releases through the API and cross-check the payload against itself, the ledger, the
closed-form audit ceiling, and the Ed25519 signature -- so a displayed value that drifts from
the measured one fails here, whichever layer drifted.
"""

import json

import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519
from fastapi.testclient import TestClient

from synthproof.api.main import app
from synthproof.audit.steinke import max_provable_epsilon
from synthproof.frontier.experiment import MECHANISMS
from synthproof.ledger.signing import SignatureError, verify_datasheet

client = TestClient(app)

RUNS = [
    ("independent", 1.0),
    ("pairwise", 2.0),
    pytest.param(
        ("aim", 1.0),
        marks=pytest.mark.skipif("aim" not in MECHANISMS, reason="private-PGM not installed"),
    ),
]


def _events(text: str):
    out = []
    for frame in text.split("\n\n"):
        event, data = None, []
        for line in frame.split("\n"):
            if line.startswith("event: "):
                event = line[7:].strip()
            elif line.startswith("data: "):
                data.append(line[6:])
        if event and data:
            out.append((event, json.loads("\n".join(data))))
    return out


@pytest.fixture(scope="module", params=RUNS, ids=lambda p: f"{p[0]}-eps{p[1]:g}")
def release(request):
    """One real release per mechanism, plus the ledger as it stood just after it."""
    mechanism, eps = request.param
    client.post("/api/ledger/reset")
    before = client.get("/api/ledger").json()
    body = {"dataset": "toy", "mechanism": mechanism, "target_eps": eps, "rows": 400, "seed": 3}
    res = client.post("/api/run", json=body)
    assert res.status_code == 200
    events = _events(res.text)
    errors = [p for e, p in events if e == "error"]
    assert not errors, errors
    done = next(p for e, p in events if e == "done")
    after = client.get("/api/ledger").json()
    yield {"body": body, "done": done, "before": before, "after": after}
    client.post("/api/ledger/reset")


# ---------------------------------------------------------------- epsilon, three ways


def test_proved_epsilon_is_the_same_in_the_sheet_the_measurements_and_the_ledger(release):
    done, after = release["done"], release["after"]
    sheet_eps = done["sheet"]["total_proved_eps"]
    assert done["measurements"]["proved_eps"] == sheet_eps
    assert after["entries"][-1]["eps_spent"] == sheet_eps


def test_the_ledger_grew_by_exactly_this_release(release):
    before, after = release["before"], release["after"]
    assert after["count"] == before["count"] + 1
    assert after["total_eps_spent"] == pytest.approx(
        before["total_eps_spent"] + release["done"]["sheet"]["total_proved_eps"], abs=1e-4
    )
    assert after["verified"] is True


def test_the_sheet_names_the_ledger_head_it_was_charged_to(release):
    assert release["done"]["sheet"]["ledger_hash"] == release["after"]["head"]
    assert release["after"]["entries"][-1]["hash"] == release["after"]["head"]


def test_proved_epsilon_never_exceeds_the_request(release):
    assert 0 < release["done"]["sheet"]["total_proved_eps"] <= release["body"]["target_eps"]


# ---------------------------------------------------------------- the audit


def test_the_ceiling_is_the_closed_form_for_the_declared_audit(release):
    sheet, audit = release["done"]["sheet"], release["done"]["audit"]
    expected = max_provable_epsilon(sheet["audit_budget"], sheet["audit_alpha"])
    assert sheet["audit_ceiling"] == pytest.approx(expected, rel=1e-12)
    assert audit["ceiling"] == sheet["audit_ceiling"]
    assert release["done"]["measurements"]["audit_ceiling"] == sheet["audit_ceiling"]


def test_audited_epsilon_agrees_everywhere_and_sits_inside_the_instrument_range(release):
    done = release["done"]
    audited = done["sheet"]["total_audited_eps"]
    assert done["audit"]["audited_eps"] == audited
    assert done["measurements"]["audited_eps"] == audited
    assert 0.0 <= audited <= done["sheet"]["audit_ceiling"] + 1e-12


def test_the_audit_counts_add_up(release):
    a = release["done"]["audit"]
    assert a["guesses"] == release["done"]["sheet"]["audit_budget"] == a["num_canaries"]
    assert 0 <= a["correct"] <= a["guesses"]
    assert a["accuracy"] == pytest.approx(a["correct"] / a["guesses"])
    assert a["num_members"] + a["num_holdout"] == a["num_canaries"]


def test_the_range_note_quotes_the_ceiling_it_sits_beside(release):
    a = release["done"]["audit"]
    # The console shows this sentence next to the number; it must not describe another audit.
    assert f"{a['ceiling']:.2f}" in a["range_note"]
    assert f"With {a['guesses']} guesses" in a["range_note"]


# ---------------------------------------------------------------- evaluation


def test_signed_evaluation_equals_the_measured_evaluation(release):
    done = release["done"]
    for key, value in done["sheet"]["evaluation"].items():
        assert done["measurements"][key] == value, key


def test_reported_probabilities_are_probabilities(release):
    m = release["done"]["measurements"]
    for key in ("tstr_f1", "trtr_f1", "mia_auc", "audit_p"):
        assert 0.0 <= m[key] <= 1.0, key


# ---------------------------------------------------------------- the signature binds them


def _key(sheet):
    return ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(sheet["public_key"]))


def test_the_signature_covers_exactly_what_is_reported(release):
    sheet = release["done"]["sheet"]
    assert verify_datasheet(sheet, public_key=_key(sheet)) is True


@pytest.mark.parametrize(
    "field,path",
    [
        ("proved epsilon", ("total_proved_eps",)),
        ("audit ceiling", ("audit_ceiling",)),
        ("audited epsilon", ("total_audited_eps",)),
        ("utility", ("evaluation", "tstr_f1")),
    ],
)
def test_changing_any_reported_number_breaks_the_signature(release, field, path):
    sheet = json.loads(json.dumps(release["done"]["sheet"]))
    target = sheet
    for p in path[:-1]:
        target = target[p]
    target[path[-1]] = target[path[-1]] + 0.001
    with pytest.raises(SignatureError):
        verify_datasheet(sheet, public_key=_key(release["done"]["sheet"]))
