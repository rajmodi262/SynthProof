"""Fuzzing the two places that take untrusted input: the release-boundary auditor (it reads a
sheet someone else produced) and the API's request validation.

The contract under fuzzing is narrow and absolute: malformed input is REFUSED, never crashes.
A crash in the auditor would mean an adversarial sheet can stop the check that is meant to
catch it; a 500 from the API would mean a request shape the validators never anticipated
reached the pipeline.
"""

import json
import math

from fastapi.testclient import TestClient
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from synthproof.api.main import app
from synthproof.audit.boundary import BoundaryReport, audit_croissant, audit_sheet, render

client = TestClient(app)

# JSON-shaped values, including the awkward ones: NaN, infinities, huge and negative numbers,
# empty containers, wrong types where a number is expected.
scalars = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-(10**12), max_value=10**12),
    st.floats(allow_nan=True, allow_infinity=True),
    st.text(max_size=20),
)
json_values = st.recursive(
    scalars,
    lambda inner: st.one_of(
        st.lists(inner, max_size=4), st.dictionaries(st.text(max_size=12), inner, max_size=4)
    ),
    max_leaves=12,
)

# The fields the auditor actually reads, so the fuzzer reaches real code paths instead of
# spending every example on a dictionary of irrelevant keys.
SHEET_KEYS = [
    "total_proved_eps",
    "delta",
    "seed",
    "num_rows",
    "release_rows_source",
    "release_rows_eps",
    "input_fingerprint",
    "fingerprint_scheme",
    "fingerprint_key_id",
    "evaluation",
    "evaluation_privacy",
    "accountant_agreement",
    "mechanism",
    "mechanism_events",
    "domain_source",
    "contribution_bound",
    "audit_ceiling",
    "audit_budget",
    "audit_alpha",
    "audit_estimator",
    "total_audited_eps",
    "unit_of_privacy",
    "tables",
    "signature",
    "public_key",
]
sheets = st.dictionaries(st.sampled_from(SHEET_KEYS), json_values, max_size=len(SHEET_KEYS))


@settings(max_examples=300, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(sheet=sheets)
def test_the_boundary_auditor_never_crashes_on_a_hostile_sheet(sheet):
    report = audit_sheet(sheet)
    assert isinstance(report, BoundaryReport)
    render(report)  # the human-readable form must not crash either


@settings(max_examples=150, deadline=None)
@given(sheet=sheets, extra=st.dictionaries(st.text(max_size=12), json_values, max_size=3))
def test_the_croissant_auditor_never_crashes(sheet, extra):
    record = {"@type": "sc:Dataset", **extra, "dp:privacyDataSheet": sheet}
    assert isinstance(audit_croissant(record), BoundaryReport)


@settings(max_examples=80, deadline=None)
@given(sheet=sheets)
def test_a_sheet_the_auditor_cannot_read_is_never_reported_clean(sheet):
    """An epsilon that is missing, NaN or not a number must not pass as a valid release."""
    eps = sheet.get("total_proved_eps")
    readable = isinstance(eps, (int, float)) and not isinstance(eps, bool) and math.isfinite(eps)
    if not readable:
        report = audit_sheet(sheet)
        assert report.findings, "an unreadable epsilon produced no finding at all"


run_bodies = st.fixed_dictionaries(
    {},
    optional={
        "dataset": st.one_of(st.sampled_from(["toy", "adult", "nope", ""]), json_values),
        "mechanism": st.one_of(st.sampled_from(["independent", "aim", "x"]), json_values),
        "target_eps": st.one_of(st.floats(allow_nan=True, allow_infinity=True), json_values),
        "delta": st.one_of(st.floats(allow_nan=True, allow_infinity=True), json_values),
        "rows": st.one_of(st.integers(-5, 10**7), json_values),
        "num_canaries": st.one_of(st.integers(-5, 10**4), json_values),
        "seed": st.one_of(st.integers(-(2**70), 2**70), json_values),
        "target": json_values,
    },
)


def _never_runs_the_pipeline(body):
    """Keeps the fuzzer to validation: a body that would launch a real fit is made invalid."""
    return {**body, "rows": -1}


@settings(max_examples=150, deadline=None)
@given(body=run_bodies)
def test_the_run_endpoint_refuses_bad_requests_without_a_server_error(body):
    # Raw JSON with NaN/Infinity tokens: Python's parser on the server accepts them, so they are
    # exactly what a hostile client can send.
    raw = json.dumps(_never_runs_the_pipeline(body), allow_nan=True)
    res = client.post("/api/run", content=raw, headers={"Content-Type": "application/json"})
    assert res.status_code == 422, res.text[:300]


@settings(max_examples=60, deadline=None)
@given(raw=st.binary(max_size=200))
def test_non_json_bodies_are_refused(raw):
    res = client.post("/api/run", content=raw, headers={"Content-Type": "application/json"})
    assert res.status_code in (400, 422)


@settings(max_examples=60, deadline=None)
@given(body=json_values)
def test_the_verify_endpoints_refuse_garbage_without_a_server_error(body):
    for path in ("/api/certificate/verify", "/api/capsule/verify"):
        res = client.post(path, content=json.dumps(body, allow_nan=True))
        assert res.status_code < 500, (path, res.status_code, res.text[:300])


def test_infinity_in_a_request_is_a_422_not_a_500():
    """Found by the fuzzer above: the default handler echoed `inf` back, could not encode it,
    and answered 500. Pinned explicitly so it does not depend on Hypothesis rediscovering it."""
    for token in ("Infinity", "-Infinity", "NaN"):
        raw = '{"target_eps": %s, "rows": -1}' % token
        res = client.post("/api/run", content=raw, headers={"Content-Type": "application/json"})
        assert res.status_code == 422, (token, res.status_code)
        assert res.json()["detail"]  # and the body is valid JSON that says why
