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
    results, environment = reproduce.compare(current, committed)
    result_text = "\n".join(results)

    assert "manifest hash" in result_text
    assert "a.json" in result_text  # contents changed
    assert "MISSING" in result_text  # b.json disappeared
    assert "not in committed manifest" in result_text  # c.json is new

    # A dependency version is reported SEPARATELY and does not fail the gate. On 2026-09-12
    # CI reported four of these — numpy, scipy, scikit-learn, mbi — while every result hash
    # matched exactly, and the run was marked a failure. A reproduction on a different
    # dependency set is a stronger result than one on the same set, not a weaker one.
    assert "numpy" in "\n".join(environment)
    assert "numpy" not in result_text


def test_identical_manifests_report_no_divergence():
    m = reproduce.build_manifest()
    assert reproduce.compare(m, m) == ([], [])


def test_a_dependency_bump_alone_is_not_a_failed_reproduction():
    """The distinction the gate turns on, stated as its own test.

    Every result hash identical, one dependency moved. That is a reproduction with a caveat,
    and the caveat belongs in the output rather than in the exit code -- a gate that fails on
    every numpy patch release is one people learn to route around.
    """
    files = {"results/h1.json": "deadbeef", "results/h2.json": "cafebabe"}
    current = {"manifest_hash": "same", "files": files, "dependencies": {"numpy": "2.5.3"}}
    committed = {"manifest_hash": "same", "files": files, "dependencies": {"numpy": "2.4.6"}}

    results, environment = reproduce.compare(current, committed)
    assert results == [], "a dependency bump must not count as a changed result"
    assert len(environment) == 1 and "numpy" in environment[0]


def test_a_changed_result_still_fails_even_on_an_identical_environment():
    """The other half. Narrowing the gate must not blunt it."""
    deps = {"numpy": "2.5.3"}
    current = {"manifest_hash": "new", "files": {"results/h1.json": "0001"}, "dependencies": deps}
    committed = {"manifest_hash": "old", "files": {"results/h1.json": "9999"}, "dependencies": deps}

    results, environment = reproduce.compare(current, committed)
    assert environment == []
    assert any("h1.json" in d for d in results)
    assert any("manifest hash" in d for d in results)


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
        runners = {
            "h1_all_families": "run_h1",
            "h2_subgroups": "run_h2",
            "h2_analysis": "analyse_h2",
            "h3_allocation": "run_h3",
            "detection_floor": "run_detection_floor",
            "fairness": "run_fairness",
            "gdp_audit": "run_gdp_audit",
        }
        # A KeyError here means someone pinned a result file without teaching this test which
        # runner produces it -- which is the same omission the assertion below guards against,
        # so report it as that rather than as an opaque KeyError. (Hit on 2026-08-25 when
        # gdp_audit.json was pinned.)
        assert stem in runners, (
            f"{path} is pinned in RESULT_FILES but this test has no runner mapped for "
            f"{stem!r}. Add it here and to EXPERIMENTS, or the file cannot be regenerated."
        )
        assert runners[stem] in cmds, f"{path} has no experiment that produces it"
