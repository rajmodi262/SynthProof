"""Tests for the reproducibility manifest.

The manifest underwrites the thesis's strongest process claim — that every published number
can be regenerated from a named commit. A manifest that silently fails to notice a changed
result would be worse than no manifest, because it would license the claim without supporting
it. These tests check that it actually detects change.
"""

import json

import pytest

from scripts import reproduce


def test_manifest_has_everything_needed_to_reproduce_a_run():
    m = reproduce.build_manifest()

    assert m["manifest_version"] == 1
    assert m["git"]["commit"]
    assert isinstance(m["git"]["dirty"], bool)
    assert m["environment"]["python"]
    assert len(m["manifest_hash"]) == 64

    # Versions of every package whose value can change a number.
    for pkg in ("numpy", "pandas", "scipy", "scikit-learn", "dp-accounting"):
        assert pkg in m["dependencies"]

    # Each experiment's grid is read from the runner module, so it cannot drift from what
    # actually ran.
    assert set(m["experiments"]) == {"h1", "h2", "detection_floor"}
    assert "seeds" in m["experiments"]["h1"]
    assert "eps_grid" in m["experiments"]["h1"]


def test_manifest_hash_is_deterministic_for_unchanged_results():
    assert reproduce.build_manifest()["manifest_hash"] == \
        reproduce.build_manifest()["manifest_hash"]


def test_manifest_hash_changes_when_a_result_file_changes(tmp_path, monkeypatch):
    """The property the whole thing rests on: an edited result must not go unnoticed."""
    a = tmp_path / "one.json"
    a.write_text('{"value": 1}', encoding="utf-8")
    monkeypatch.setattr(reproduce, "RESULT_FILES", [str(a)])

    before = reproduce.build_manifest()["manifest_hash"]
    a.write_text('{"value": 2}', encoding="utf-8")
    after = reproduce.build_manifest()["manifest_hash"]

    assert before != after, "an edited result file did not change the manifest hash"


def test_a_missing_result_is_reported_rather_than_skipped(tmp_path, monkeypatch):
    """A missing file must not quietly produce the same hash as a present one."""
    missing = tmp_path / "absent.json"
    monkeypatch.setattr(reproduce, "RESULT_FILES", [str(missing)])

    m = reproduce.build_manifest()
    assert m["files"][str(missing)] is None

    missing.write_text("{}", encoding="utf-8")
    assert reproduce.build_manifest()["manifest_hash"] != m["manifest_hash"]


def test_comparison_reports_every_kind_of_divergence():
    current = {
        "manifest_hash": "new",
        "files": {"a.json": "aaa", "b.json": None, "c.json": "ccc"},
        "dependencies": {"numpy": "2.0.0"},
    }
    committed = {
        "manifest_hash": "old",
        "files": {"a.json": "zzz", "b.json": "bbb"},
        "dependencies": {"numpy": "1.26.0"},
    }
    diffs = "\n".join(reproduce.compare(current, committed))

    assert "manifest hash" in diffs
    assert "a.json" in diffs                    # contents changed
    assert "MISSING" in diffs                   # b.json disappeared
    assert "not in committed manifest" in diffs  # c.json is new
    assert "numpy" in diffs                     # dependency moved


def test_identical_manifests_report_no_divergence():
    m = reproduce.build_manifest()
    assert reproduce.compare(m, m) == []


def test_dataset_checksum_is_pinned_from_the_committed_file():
    """The manifest must record which bytes the experiments were run against."""
    digest = reproduce._read_checksum("adult.zip")
    assert digest is not None and len(digest) == 64
    assert reproduce._read_checksum("does-not-exist.zip") is None


def test_manifest_round_trips_through_json():
    """It is written to disk and read back by a verifier, so it must survive that."""
    m = reproduce.build_manifest()
    assert json.loads(json.dumps(m))["manifest_hash"] == m["manifest_hash"]


@pytest.mark.parametrize("experiment,cmd", reproduce.EXPERIMENTS)
def test_every_experiment_names_a_runnable_module(experiment, cmd):
    """Guards against a manifest that claims to cover an experiment it cannot run."""
    import importlib

    assert cmd[1] == "-m"
    module = importlib.import_module(cmd[2])
    assert hasattr(module, "main"), f"{experiment} runner has no main()"
