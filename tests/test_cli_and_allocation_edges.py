"""Edge and error paths that coverage analysis found untested.

Written for task 3.2 of docs/ROAD_TO_TEN.md. The selection is not arbitrary: these are the
branches where an untested failure is worst.

  The ALLOCATOR decides how much epsilon each query gets. Its five uncovered lines were all
  guards -- non-positive budgets, empty item lists, degenerate weights. A budget splitter that
  mishandles a zero or a negative does not crash loudly; it hands out a number, and every
  epsilon downstream of it is then a false statement.

  The CLI is what an examiner runs. Its uncovered lines were concentrated in the failure
  paths -- signing with no key, exporting a Croissant record from a sheet that cannot produce
  one. An error path that has never run is an error path that raises the wrong exception, or
  none, at the worst possible moment.
"""

import json

import numpy as np
import pandas as pd
import pytest
from click.testing import CliRunner

from synthproof.cli import main
from synthproof.ledger.allocator import Allocator

# --------------------------------------------------------------------------- the allocator


@pytest.mark.parametrize("bad", [0.0, -1.0, -1e-9])
def test_uniform_allocation_refuses_a_non_positive_budget(bad):
    """Zero is not "spend nothing", it is a caller error, and it must not pass silently."""
    with pytest.raises(ValueError, match="must be positive"):
        Allocator.allocate_uniform(bad, ["a", "b"])


@pytest.mark.parametrize("bad", [0.0, -1.0])
def test_weighted_allocation_refuses_a_non_positive_budget(bad):
    with pytest.raises(ValueError, match="must be positive"):
        Allocator.allocate_weighted(bad, {"a": 1.0})


def test_allocating_across_nothing_yields_nothing():
    """Not a division by zero, and not a silent 'everything to nobody'."""
    assert Allocator.allocate_uniform(1.0, []) == {}
    assert Allocator.allocate_weighted(1.0, {}) == {}


def test_degenerate_weights_fall_back_to_uniform_rather_than_dividing_by_zero():
    """All-zero or all-negative weights have no meaningful proportion.

    The fallback matters more than it looks: the alternative is a zero denominator, and the
    natural "fix" for that is to hand the whole budget to one item, which would silently
    concentrate the entire privacy loss on a single query.
    """
    out = Allocator.allocate_weighted(2.0, {"a": 0.0, "b": 0.0, "c": -5.0})
    assert set(out) == {"a", "b", "c"}
    assert all(abs(v - 2.0 / 3.0) < 1e-12 for v in out.values())
    assert abs(sum(out.values()) - 2.0) < 1e-12


def test_negative_weights_are_floored_not_subtracted():
    """A negative weight must not steal budget from its neighbours."""
    out = Allocator.allocate_weighted(3.0, {"a": 2.0, "b": -1.0})
    assert out["b"] == 0.0
    assert abs(out["a"] - 3.0) < 1e-12
    assert abs(sum(out.values()) - 3.0) < 1e-12


def test_uniform_allocation_never_overspends_the_total():
    """The invariant the whole ledger rests on."""
    for n in (1, 3, 7, 64):
        out = Allocator.allocate_uniform(1.0, [f"q{i}" for i in range(n)])
        assert len(out) == n
        assert sum(out.values()) <= 1.0 + 1e-12


# --------------------------------------------------------------------------- CLI failures


@pytest.fixture()
def small_csv(tmp_path):
    """A table above the 500-row pre-flight floor, so `run` reaches the code under test."""
    rng = np.random.default_rng(0)
    n = 600
    p = tmp_path / "in.csv"
    pd.DataFrame(
        {
            "age": rng.integers(18, 90, n),
            "hours": rng.integers(1, 80, n),
            "label": rng.choice(["yes", "no"], n),
        }
    ).to_csv(p, index=False)
    return p


def test_signing_without_a_key_fails_with_a_message_not_a_traceback(
    tmp_path, monkeypatch, small_csv
):
    """`--sign` against an empty key directory must explain itself.

    The failure mode this guards against is a stack trace at a viva: the user asks for a
    signature, no key exists, and the tool dies in `signing.py` instead of saying so.
    """
    monkeypatch.setenv("SYNTHPROOF_KEY_DIR", str(tmp_path / "no-keys-here"))
    r = CliRunner().invoke(
        main,
        ["run", "--input", str(small_csv), "--eps", "1.0", "--mechanism", "independent", "--sign"],
    )
    assert r.exit_code != 0
    assert "Traceback" not in r.output
    # The message must name the missing thing, not merely fail.
    assert "key" in r.output.lower()


def test_croissant_export_rejects_a_sheet_it_cannot_represent(tmp_path):
    """A sheet missing the fields Croissant requires must be refused, with the reason."""
    bad = tmp_path / "sheet.json"
    bad.write_text(json.dumps({"not": "a data sheet"}), encoding="utf-8")
    r = CliRunner().invoke(main, ["croissant", "--datasheet", str(bad)])
    assert r.exit_code != 0
    assert "Traceback" not in r.output


def test_croissant_export_writes_a_record_for_a_real_sheet(tmp_path, monkeypatch, small_csv):
    """The happy path, end to end through the CLI rather than the library."""
    monkeypatch.setenv("SYNTHPROOF_KEY_DIR", str(tmp_path / "keys"))
    assert CliRunner().invoke(main, ["keygen"]).exit_code == 0

    sheet = tmp_path / "sheet.json"
    r = CliRunner().invoke(
        main,
        [
            "run",
            "--input",
            str(small_csv),
            "--eps",
            "1.0",
            "--mechanism",
            "independent",
            "--sign",
            "--out",
            str(sheet),
        ],
    )
    assert r.exit_code == 0, r.output

    out = tmp_path / "release.croissant.json"
    r = CliRunner().invoke(main, ["croissant", "--datasheet", str(sheet), "--out", str(out)])
    assert r.exit_code == 0, r.output
    assert out.exists()

    record = json.loads(out.read_text(encoding="utf-8"))
    # The DP extension is the whole point of emitting Croissant at all.
    assert "@context" in record
    assert any("dp" in str(k).lower() for k in record.get("@context", {}))


def test_run_refuses_a_table_below_the_row_floor_and_says_why(tmp_path):
    """The refusal path is a FEATURE, and the console now demonstrates it deliberately.

    400 rows is below the 500-row floor. The command must exit non-zero, name the rule, and
    say what the user can do -- not merely decline.
    """
    rng = np.random.default_rng(0)
    p = tmp_path / "tiny.csv"
    pd.DataFrame({"age": rng.integers(18, 90, 400), "label": rng.choice(["a", "b"], 400)}).to_csv(
        p, index=False
    )

    r = CliRunner().invoke(main, ["run", "--input", str(p), "--eps", "1.0"])
    assert r.exit_code != 0
    assert "REFUSE" in r.output
    assert "500" in r.output
