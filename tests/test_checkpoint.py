"""Tests for per-cell grid checkpointing.

The 75-cell H1 grid has been lost twice — once to a MemoryError at cell 59, once to a session
teardown at cell 64 — because results were only written at the end. These tests pin the three
properties that make a restart safe: atomic writes, configuration-matched reuse, and refusing
to treat a partial grid as complete.
"""

import json
from pathlib import Path

import pytest

from synthproof.frontier.checkpoint import (
    CellRecord,
    GridCheckpoint,
    config_hash,
    run_with_checkpoints,
)


def _cells(n=6):
    return [{"mechanism": "independent", "target_eps": 1.0, "seed": i} for i in range(n)]


# ------------------------------------------------------------------ hashing

def test_config_hash_is_order_independent():
    """Dict ordering must not change the hash, or every restart recomputes everything."""
    assert config_hash({"a": 1, "b": 2}) == config_hash({"b": 2, "a": 1})


def test_config_hash_treats_equal_numbers_as_equal():
    """1.0 and 1 are the same epsilon; a hash that disagrees invalidates good cache."""
    assert config_hash({"eps": 1.0}) == config_hash({"eps": 1})


def test_config_hash_changes_when_configuration_changes():
    """The property that stops a stale cell being reused under new settings."""
    base = {"mechanism": "aim", "target_eps": 1.0, "seed": 0}
    for k, v in (("mechanism", "pairwise"), ("target_eps", 2.0), ("seed", 1)):
        assert config_hash({**base, k: v}) != config_hash(base)


# ------------------------------------------------------------------ resume

def test_a_completed_cell_is_reused_and_not_recomputed(tmp_path):
    calls = []

    def compute(cfg):
        calls.append(cfg["seed"])
        return {"metric": float(cfg["seed"])}

    cells = _cells(3)
    first = run_with_checkpoints(cells, compute, tmp_path)
    assert calls == [0, 1, 2]

    second = run_with_checkpoints(cells, compute, tmp_path)
    assert calls == [0, 1, 2], "a cached cell was recomputed"
    assert first == second


def test_a_teardown_mid_grid_loses_at_most_one_cell(tmp_path):
    """THE regression test. Simulates the exact failure that cost two full grid runs."""
    class Teardown(Exception):
        pass

    def dies_at_cell_4(cfg):
        if cfg["seed"] == 4:
            raise Teardown("simulated session teardown")
        return {"metric": float(cfg["seed"])}

    cells = _cells(6)
    with pytest.raises(Teardown):
        run_with_checkpoints(cells, dies_at_cell_4, tmp_path)

    # Cells 0-3 survived; 4 was in flight and is lost; 5 never started.
    assert GridCheckpoint(tmp_path).completed_indices() == [0, 1, 2, 3]

    # Restarting recomputes only cell 4 onward.
    recomputed = []

    def compute(cfg):
        recomputed.append(cfg["seed"])
        return {"metric": float(cfg["seed"])}

    out = run_with_checkpoints(cells, compute, tmp_path)
    assert recomputed == [4, 5], f"recomputed more than the lost cell: {recomputed}"
    assert [o["metric"] for o in out] == [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]


def test_a_changed_configuration_invalidates_the_cache(tmp_path):
    """Silently reusing a cell computed under different settings would publish numbers that
    never came from the code claiming them."""
    def compute(cfg):
        return {"metric": cfg["target_eps"]}

    run_with_checkpoints(_cells(2), compute, tmp_path)

    changed = [{**c, "target_eps": 8.0} for c in _cells(2)]
    recomputed = []

    def compute2(cfg):
        recomputed.append(cfg["seed"])
        return {"metric": cfg["target_eps"]}

    out = run_with_checkpoints(changed, compute2, tmp_path)
    assert recomputed == [0, 1], "stale cells were reused under a new configuration"
    assert all(o["metric"] == 8.0 for o in out)


# ------------------------------------------------------------------ robustness

def test_a_truncated_cell_file_is_recomputed_not_trusted(tmp_path):
    """A half-written JSON must never be read as a completed cell."""
    ckpt = GridCheckpoint(tmp_path)
    ckpt.save(CellRecord(index=0, config={"a": 1}, config_hash="abc", metrics={"m": 1.0}))
    ckpt.path_for(0).write_text('{"index": 0, "metrics": {"m": 1.0', encoding="utf-8")

    assert ckpt.load(0, "abc") is None
    assert ckpt.completed_indices() == []


def test_an_incomplete_cell_is_not_reused(tmp_path):
    ckpt = GridCheckpoint(tmp_path)
    rec = CellRecord(index=0, config={"a": 1}, config_hash="abc", metrics={"m": 1.0})
    rec.completed = False
    ckpt.save(rec)
    assert ckpt.load(0, "abc") is None


def test_writes_leave_no_temp_files_behind(tmp_path):
    """A stray temp file could be picked up by a later glob."""
    ckpt = GridCheckpoint(tmp_path)
    for i in range(4):
        ckpt.save(CellRecord(index=i, config={"i": i}, config_hash="h", metrics={"m": 1.0}))
    assert not list(Path(tmp_path).glob(".tmp_cell_*"))
    assert len(list(Path(tmp_path).glob("cell_*.json"))) == 4


def test_saved_cell_records_its_configuration_and_seed(tmp_path):
    """A result file that cannot say what produced it is not traceable to an experiment."""
    ckpt = GridCheckpoint(tmp_path)
    cfg = {"mechanism": "aim", "target_eps": 8.0, "seed": 3}
    ckpt.save(CellRecord(index=7, config=cfg, config_hash=config_hash(cfg),
                         metrics={"proved_eps": 6.5}))

    data = json.loads(ckpt.path_for(7).read_text(encoding="utf-8"))
    assert data["config"] == cfg
    assert data["completed"] is True
    assert data["metrics"]["proved_eps"] == 6.5
    assert data["version"] == 1
