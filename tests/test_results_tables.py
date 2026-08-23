"""Tests for the Chapter 7 table generator.

The generator exists so a thesis table cannot drift from `results/`. These tests exist because
its first version drifted in the worse direction: `.get(key, 0)` lookups against key names that
did not match produced a full table of `0.000` and `?` that read as a measured null result.

That is standing rule 2 -- never report a number that was not computed -- defeated by a silent
default. So the tests below check both that the numbers are right AND that a schema change
raises instead of publishing zeros.
"""

import json
from pathlib import Path

import pytest

from scripts.build_results_tables import RESULTS, load, table_calibration, table_h1, table_h2

pytestmark = pytest.mark.skipif(
    not (RESULTS / "h1_all_families.json").exists(), reason="committed results not present"
)


# ------------------------------------------------------- the numbers match the committed data


def test_h1_table_reproduces_committed_adult_values():
    """Spot-checks against results/H1_RESULTS.md, which was written independently."""
    md = table_h1(load("h1_all_families.json"), "UCI Adult")
    assert "0.0078" in md, "aim at eps=8 correlation error missing"
    assert "0.0947" in md, "independent at eps=8 correlation error missing"
    assert "0.660" in md, "TRTR baseline missing"


def test_h2_table_reproduces_committed_subgroup_values():
    """results/H2_RESULTS.md: 'Other' reaches 0.562 at eps=8; 'White' sits at 0.542."""
    md = table_h2(load("h2_subgroups.json"))
    assert "0.562" in md and "0.542" in md
    assert "Amer-Indian-Eskimo" in md, "subgroup names must be real, not '?'"
    assert "3.27" in md, "the per-subgroup ceiling must be stated beside the audited values"


def test_calibration_table_never_reports_an_overspend():
    """proved/target > 1 would mean we published a guarantee we cannot support."""
    md = table_calibration(load("h1_all_families.json"))
    assert "never exceeds 1.000" in md, md.splitlines()[-1]


# ------------------------------------------------------- the fabricated-zero bug cannot return


def test_h2_raises_on_an_unexpected_schema_rather_than_emitting_zeros():
    """The regression. Rename a key and the build must STOP, not publish 0.000."""
    data = json.loads(json.dumps(load("h2_subgroups.json")))  # deep copy
    for cell in data["cells"]:
        for g in cell["subgroups"]:
            g["renamed_accuracy"] = g.pop("mean_accuracy")
    with pytest.raises(KeyError):
        table_h2(data)


def test_the_generator_uses_no_numeric_fallbacks():
    """A `.get(key, default)` here can turn a schema change into a fake measurement.

    Parsed with `ast` rather than grepped, because the docstrings in that module quote the
    original buggy line in order to explain it -- a text search flags its own explanation.
    """
    import ast

    src = (Path(__file__).resolve().parents[1] / "scripts" / "build_results_tables.py").read_text(
        encoding="utf-8"
    )
    offenders = []
    for node in ast.walk(ast.parse(src)):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and len(node.args) == 2  # a default was supplied
        ):
            offenders.append(f"line {node.lineno}: .get(..., <default>)")
    assert not offenders, f"defaulted lookups reintroduced: {offenders}"


def test_every_table_carries_its_uncertainty():
    """Chapter discipline: no result appears without an uncertainty estimate."""
    md = table_h1(load("h1_all_families.json"), "UCI Adult")
    body = [ln for ln in md.split("\n") if ln.startswith("| `")]
    assert body, "no data rows generated"
    for row in body:
        assert row.count("[") >= 2, f"row lacks confidence intervals: {row}"
