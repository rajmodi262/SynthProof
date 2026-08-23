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
    assert set(m["experiments"]) == {"h1", "h2", "h3", "detection_floor"}
    assert "seeds" in m["experiments"]["h1"]
    assert "eps_grid" in m["experiments"]["h1"]
    # One runner drives both benchmarks; each records its own target and structure pair.
    assert {"adult", "acs"} <= set(m["experiments"]["h1"]["datasets"])


def test_manifest_hash_is_deterministic_for_unchanged_results():
    assert (
        reproduce.build_manifest()["manifest_hash"] == reproduce.build_manifest()["manifest_hash"]
    )


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
    assert "a.json" in diffs  # contents changed
    assert "MISSING" in diffs  # b.json disappeared
    assert "not in committed manifest" in diffs  # c.json is new
    assert "numpy" in diffs  # dependency moved


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


def test_the_manifest_hash_ignores_timing_but_not_results(tmp_path):
    """REGRESSION: the manifest hashed whole result files, including `elapsed_seconds`.

    Wall-clock timing differs on every run, so two byte-identical reproductions produced
    different manifest hashes and `make reproduce` reported DIVERGED even though no number
    had moved. Observed live: three consecutive clean re-runs, three different hashes, with
    `elapsed_seconds` the only differing field.

    The hash must ignore timing and nothing else — a manifest that cannot detect a changed
    result is worse than no manifest.
    """
    import json as _json

    from scripts.reproduce import _sha256

    p = tmp_path / "r.json"
    payload = {
        "dataset": "adult",
        "true_correlation": 0.1034,
        "elapsed_seconds": 12.3,
        "cells": [{"mechanism": "aim", "correlation_error": {"mean": 0.0078}}],
    }
    p.write_text(_json.dumps(payload, indent=2), encoding="utf-8")
    baseline = _sha256(p)

    payload["elapsed_seconds"] = 9999.9
    p.write_text(_json.dumps(payload, indent=2), encoding="utf-8")
    assert _sha256(p) == baseline, "timing must not change the manifest hash"

    payload["cells"][0]["correlation_error"]["mean"] = 0.0079
    p.write_text(_json.dumps(payload, indent=2), encoding="utf-8")
    assert _sha256(p) != baseline, "a changed metric MUST change the manifest hash"


def test_the_manifest_hash_survives_reformatting_but_not_reordering_of_values(tmp_path):
    """Re-serialising with different indentation is not a change to the result."""
    import json as _json

    from scripts.reproduce import _sha256

    a, b = tmp_path / "a.json", tmp_path / "b.json"
    payload = {"z": 1, "a": {"n": [1, 2, 3]}}
    a.write_text(_json.dumps(payload, indent=4), encoding="utf-8")
    b.write_text(_json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    assert _sha256(a) == _sha256(b)


def test_a_non_json_result_file_is_hashed_verbatim(tmp_path):
    """We do not normalise what we cannot parse."""
    from scripts.reproduce import _sha256

    p = tmp_path / "r.csv"
    p.write_text("a,b\n1,2\n", encoding="utf-8")
    first = _sha256(p)
    p.write_text("a,b\n1,3\n", encoding="utf-8")
    assert _sha256(p) != first


def test_no_manifest_config_section_silently_records_an_error():
    """REGRESSION: `_experiment_config` wraps each reader in a broad `except` and stores
    `{"error": ...}` on failure. When `run_h2`'s module-level ATTRIBUTES constant was removed
    during the --dataset parameterisation, the manifest quietly began pinning an AttributeError
    string in place of the H2 grid — the exact drift the manifest exists to detect, occurring
    inside the manifest itself.
    """
    from scripts.reproduce import _experiment_config

    cfg = _experiment_config()
    broken = {k: v["error"] for k, v in cfg.items() if isinstance(v, dict) and "error" in v}
    assert not broken, f"manifest config sections failed to build: {broken}"


def test_the_manifest_covers_every_hypothesis_and_the_floor():
    """A result file missing from RESULT_FILES is a published number nothing pins."""
    from scripts.reproduce import RESULT_FILES

    joined = " ".join(RESULT_FILES)
    for expected in ("h1_all_families", "h2_subgroups", "h3_allocation", "detection_floor"):
        assert expected in joined, f"{expected} is not pinned by the manifest"
    # Both datasets, for each hypothesis that has two.
    assert sum("acs/" in p for p in RESULT_FILES) >= 4


def test_every_manifest_result_file_has_a_producing_experiment():
    """A file with no runner cannot be regenerated, so `reproduce --run` would leave it stale."""
    from scripts.reproduce import EXPERIMENTS, RESULT_FILES

    cmds = " ".join(" ".join(c) for _, c in EXPERIMENTS)
    for path in RESULT_FILES:
        stem = path.split("/")[-1].replace(".json", "")
        key = {
            "h1_all_families": "run_h1",
            "h2_subgroups": "run_h2",
            "h2_analysis": "analyse_h2",
            "h3_allocation": "run_h3",
            "detection_floor": "run_detection_floor",
            "fairness": "run_fairness",
        }[stem]
        assert key in cmds, f"{path} has no experiment that produces it"
