"""Pre-flight refusal checks and the data sheet's disclosure fields.

These exist because two inputs that should never have produced a release did:

  * a table whose first column was a unique identifier per row ran to completion, and real
    identifiers appeared verbatim in the synthetic output;
  * a table with a free-text column ran to completion and selected that column as the machine
    learning target.

Both now refuse. The constraint the tests enforce alongside that is subtler and matters more:
the checks must reach their verdict from public metadata alone, because a check that reads the
data to decide whether the data is safe is the defect it exists to prevent.
"""

import numpy as np
import pandas as pd
import pytest

from synthproof.data.dataset import TabularDataset
from synthproof.data.preflight import (
    FREE_TEXT_LEVELS,
    MIN_ROWS,
    Finding,
    PreflightRefused,
    enforce,
    preflight,
)
from synthproof.data.schema import CATEGORICAL, NUMERICAL, ColumnSpec, Schema
from synthproof.frontier.certificate import FrontierEngine


def _schema(*specs):
    return Schema(list(specs))


def _healthy():
    return _schema(
        ColumnSpec("age", NUMERICAL, lower=0.0, upper=120.0),
        ColumnSpec("region", CATEGORICAL, categories=list("abcdefgh")),
        ColumnSpec("dx", CATEGORICAL, categories=["x", "y", "z"]),
    )


def _codes(f):
    return sorted({x.code for x in f if x.severity == "refuse"})


# ------------------------------------------------------------------ the two live defects


def test_a_unique_identifier_column_is_refused():
    """REGRESSION (critical): a 2,000-row table with a unique MRN per row previously ran to
    completion, and real identifiers reached the synthetic output — 6 of 2,000 at eps=1 and 13
    at eps=8 — because a value present in one record can clear the profiler's category
    threshold. Nothing declined the input.
    """
    s = _schema(
        ColumnSpec("mrn", CATEGORICAL, categories=[f"MRN{i:06d}" for i in range(2000)]),
        ColumnSpec("age", NUMERICAL, lower=0.0, upper=120.0),
        ColumnSpec("dx", CATEGORICAL, categories=["a", "b"]),
    )
    findings = preflight(s, num_rows=2000)
    assert "R2" in _codes(findings)
    r2 = next(f for f in findings if f.code == "R2")
    assert r2.column == "mrn"
    assert "identifier" in r2.reason.lower()
    assert r2.remedy, "a refusal without a remedy is an error message, not a decision"


def test_a_free_text_column_is_refused():
    """The other case that silently succeeded — and was then chosen as the ML target."""
    s = _schema(
        ColumnSpec("note", CATEGORICAL, categories=[f"n{i}" for i in range(FREE_TEXT_LEVELS + 50)]),
        ColumnSpec("dx", CATEGORICAL, categories=["a", "b"]),
    )
    findings = preflight(s, num_rows=100_000)  # large n, so R2 cannot be what fires
    assert "R3" in _codes(findings)


# ------------------------------------------------------------------ the design constraint


def test_the_checks_never_read_a_single_cell():
    """THE constraint. Counting distinct values to decide a column is an identifier is itself
    a query against sensitive records, and its answer is exactly what DP exists to bound.

    Enforced by giving `preflight` no data at all: it takes a schema and a row count. If a
    future change needs values, this test stops compiling rather than failing quietly.
    """
    import inspect

    params = set(inspect.signature(preflight).parameters)
    assert "schema" in params and "num_rows" in params
    for forbidden in ("df", "data", "dataset", "frame", "values"):
        assert forbidden not in params, f"preflight must not accept {forbidden!r}"


def test_two_tables_with_identical_schemas_get_identical_verdicts():
    """A corollary of the above: the verdict cannot depend on the contents."""
    rng = np.random.default_rng(0)
    s = _healthy()
    a = preflight(s, num_rows=3000)
    b = preflight(s, num_rows=3000)
    assert [f.to_dict() for f in a] == [f.to_dict() for f in b]
    # And the same schema over wildly different data is still the same verdict, by construction.
    _ = rng  # the data never enters; kept to make the point explicit


# ------------------------------------------------------------------ the rest of the taxonomy


def test_a_table_below_the_row_floor_is_refused():
    findings = preflight(_healthy(), num_rows=MIN_ROWS - 1)
    assert "R1" in _codes(findings)


def test_a_table_at_the_row_floor_is_allowed():
    """Boundary check: the floor must be inclusive, or the message is a lie."""
    assert "R1" not in _codes(preflight(_healthy(), num_rows=MIN_ROWS))


def test_no_categorical_column_is_refused_up_front():
    """Previously a ValueError from certificate.py:120, after the work had been done."""
    s = _schema(ColumnSpec("a", NUMERICAL, lower=0.0, upper=1.0))
    assert "R4" in _codes(preflight(s, num_rows=3000))


def test_a_domain_blow_up_is_refused():
    """The ACS lesson: OCCP x POBP alone would have been 115,851 cells."""
    s = _schema(
        ColumnSpec("occ", CATEGORICAL, categories=[f"o{i}" for i in range(529)]),
        ColumnSpec("pob", CATEGORICAL, categories=[f"p{i}" for i in range(219)]),
    )
    findings = preflight(s, num_rows=200_000)
    assert "R5" in _codes(findings)
    assert "115" in next(f for f in findings if f.code == "R5").reason.replace(",", "")


def test_a_categorical_column_with_no_declared_domain_is_refused():
    s = _schema(
        ColumnSpec("dx", CATEGORICAL, categories=None),
        ColumnSpec("ok", CATEGORICAL, categories=["a", "b"]),
    )
    assert "R3" in _codes(preflight(s, num_rows=3000))


def test_a_missing_schema_is_refused():
    assert "R0" in _codes(preflight(None, num_rows=3000))


def test_a_contribution_bound_above_one_warns_and_says_by_how_much():
    findings = preflight(_healthy(), num_rows=3000, contribution_bound=5)
    r9 = next(f for f in findings if f.code == "R9")
    assert r9.severity == "warn"
    assert "5" in r9.reason


def test_an_inferred_schema_warns_but_does_not_block():
    """Inference is unsafe, not impossible. It must be recorded, not forbidden — the CLI has
    always supported exploring a table you already own."""
    findings = preflight(_healthy(), num_rows=3000, schema_declared=False)
    assert _codes(findings) == []
    assert any(f.code == "R8" and f.severity == "warn" for f in findings)


def test_a_healthy_table_passes_cleanly():
    assert enforce(_healthy(), num_rows=3000) == []


def test_findings_are_ordered_worst_first():
    findings = preflight(_healthy(), num_rows=10, schema_declared=False)
    sevs = [f.severity for f in findings]
    assert sevs == sorted(sevs, key=lambda s: {"refuse": 0, "warn": 1}[s])


def test_enforce_raises_with_every_blocking_reason_listed():
    s = _schema(ColumnSpec("mrn", CATEGORICAL, categories=[f"m{i}" for i in range(600)]))
    with pytest.raises(PreflightRefused) as e:
        enforce(s, num_rows=600)
    assert len(e.value.findings) >= 1
    assert "R2" in str(e.value) or "R4" in str(e.value)


def test_a_finding_renders_readably():
    f = Finding("R2", "refuse", "mrn", "looks like an identifier", "drop it")
    assert "R2" in str(f) and "mrn" in str(f) and "drop it" in str(f)


# ------------------------------------------------------------------ end to end


def _toy(n=3000, seed=0):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(
        {
            "age": rng.integers(18, 90, n).astype(float),
            "region": rng.choice(list("abcdefgh"), n),
            "dx": rng.choice(["x", "y", "z"], n),
        }
    )
    return TabularDataset(df, name="toy", schema=_healthy())


def test_the_engine_refuses_an_identifier_table_before_synthesising():
    """End to end: the refusal must happen in `run_sweep`, not only in the CLI, or the library
    and API paths stay exposed."""
    n = 1000
    rng = np.random.default_rng(0)
    df = pd.DataFrame(
        {
            "mrn": [f"MRN{i:06d}" for i in range(n)],
            "age": rng.integers(18, 90, n).astype(float),
            "dx": rng.choice(["a", "b"], n),
        }
    )
    ds = TabularDataset(df, name="clinic", schema=Schema.infer_nonprivate(df))
    with pytest.raises(PreflightRefused):
        FrontierEngine(seed=0).run_sweep(
            ds, eps_grid=[1.0], mechanism="independent", domain_source="inferred-nonprivate"
        )


def test_the_sheet_records_how_the_domain_was_obtained():
    """The single most important disclosure: a reader cannot otherwise tell a release with a
    public domain from one whose bounds were read out of the sensitive table."""
    sheet = FrontierEngine(seed=0).run_sweep(
        _toy(), eps_grid=[1.0], mechanism="independent", num_canaries=10, domain_source="declared"
    )
    assert sheet.domain_source == "declared"
    assert sheet.unit_of_privacy == "add/remove-one-record"
    assert sheet.contribution_bound == 1
    assert sheet.input_fingerprint and len(sheet.input_fingerprint) == 64
    assert sheet.residual_risk, "the sheet must say what DP does not cover"


def test_the_fingerprint_distinguishes_different_inputs():
    """Without it, two releases of different data look interchangeable, and a repeat release of
    the SAME data cannot be detected — the first thing a budget filter would need."""
    a = FrontierEngine(seed=0).run_sweep(
        _toy(seed=1), eps_grid=[1.0], mechanism="independent", num_canaries=10
    )
    b = FrontierEngine(seed=0).run_sweep(
        _toy(seed=2), eps_grid=[1.0], mechanism="independent", num_canaries=10
    )
    same = FrontierEngine(seed=0).run_sweep(
        _toy(seed=1), eps_grid=[1.0], mechanism="independent", num_canaries=10
    )
    assert a.input_fingerprint != b.input_fingerprint
    assert a.input_fingerprint == same.input_fingerprint


# ------------------------------------------------------------------ interpretability


def test_the_odds_statement_is_the_arithmetic_it_claims_to_be():
    """e^eps / (1 + e^eps). Reported because epsilon alone is not interpretable to a
    non-specialist (Nanayakkara et al., USENIX Security 2023)."""
    import math

    sheet = FrontierEngine(seed=0).run_sweep(
        _toy(), eps_grid=[1.0], mechanism="independent", num_canaries=10
    )
    eps = sheet.total_proved_eps
    assert sheet.membership_odds() == pytest.approx(math.exp(eps) / (1 + math.exp(eps)))
    assert 0.5 <= sheet.membership_odds() < 1.0
    assert "50 in 100" in sheet.plain_statement()


def test_the_sheet_flags_an_audit_that_could_not_have_seen_the_budget():
    """An audited eps of 0 beside a ceiling below the proved eps means the instrument was too
    weak, not that nothing leaked. At 10 canaries the ceiling is ~1.3, so a proved eps of 8
    is undetectable by construction."""
    sheet = FrontierEngine(seed=0).run_sweep(
        _toy(), eps_grid=[8.0], mechanism="independent", num_canaries=10
    )
    assert sheet.audit_ceiling is not None
    assert sheet.audit_ceiling < sheet.total_proved_eps
    assert sheet.audit_is_informative() is False


def test_a_modest_budget_is_within_the_auditors_reach():
    """The flag must not fire on every release, or it becomes noise."""
    sheet = FrontierEngine(seed=0).run_sweep(
        _toy(), eps_grid=[0.5], mechanism="independent", num_canaries=200
    )
    assert sheet.audit_is_informative() is True


def test_the_disclosure_fields_are_covered_by_the_signature():
    """A disclosure a holder could strip without invalidating the signature is not a
    disclosure. `domain_source` in particular must be inside the signed payload."""
    sheet = FrontierEngine(seed=0).run_sweep(
        _toy(), eps_grid=[1.0], mechanism="independent", num_canaries=10
    )
    payload = sheet.signing_payload().decode("utf-8")
    for f in ("domain_source", "input_fingerprint", "audit_ceiling", "unit_of_privacy"):
        assert f in payload, f"{f} is not covered by the signature"
