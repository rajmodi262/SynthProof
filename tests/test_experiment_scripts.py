"""Guards on the experiment runners' dataset configuration.

These are cheap static checks on the DATASETS tables in scripts/run_h1.py and
scripts/run_h2.py. They exist because a runner that writes to the wrong path destroys a
committed result, and the loss is only visible after the re-run that would have caught it.
"""

from pathlib import Path

import pytest

from scripts import run_h1, run_h2

RUNNERS = [pytest.param(run_h1, id="run_h1"), pytest.param(run_h2, id="run_h2")]


@pytest.mark.parametrize("mod", RUNNERS)
def test_each_dataset_writes_to_its_own_file(mod):
    """REGRESSION: parameterising run_h2 by dataset once left the output path hard-coded at
    the Adult file, so `--dataset acs` would have silently overwritten the committed Adult
    H2 result with ACS numbers. Standing rule: never overwrite a committed result file.
    """
    outs = [cfg["out"] for cfg in mod.DATASETS.values()]
    assert len(set(outs)) == len(outs), f"{mod.__name__} shares an output path: {outs}"


@pytest.mark.parametrize("mod", RUNNERS)
def test_no_output_path_is_a_bare_literal_shared_with_another_dataset(mod):
    """Every dataset's results live under a directory that names it, except Adult, which
    keeps the historical top-level path the committed manifest already references."""
    for name, cfg in mod.DATASETS.items():
        out = Path(cfg["out"])
        assert out.suffix == ".json"
        if name != "adult":
            assert name in out.parts, f"{name} writes to {out}, which does not name it"


@pytest.mark.parametrize("mod", RUNNERS)
def test_adult_paths_are_unchanged_so_the_committed_manifest_still_resolves(mod):
    """Moving Adult's output would orphan every number already cited from it."""
    expected = {"run_h1": "results/h1_all_families.json", "run_h2": "results/h2_subgroups.json"}
    assert mod.DATASETS["adult"]["out"] == expected[mod.__name__.rsplit(".", 1)[-1]]


@pytest.mark.parametrize("mod", RUNNERS)
def test_an_unknown_dataset_name_is_rejected_rather_than_defaulting(mod):
    with pytest.raises(SystemExit):
        mod._load("nhanes")


def test_h1_checkpoint_directories_are_also_per_dataset():
    """Shared checkpoints would let an Adult cell be reused as an ACS cell. The config hash
    would normally catch that, but the directories are separated so it cannot arise."""
    dirs = [cfg["checkpoints"] for cfg in run_h1.DATASETS.values()]
    assert len(set(dirs)) == len(dirs)


def test_both_runners_cover_the_same_datasets():
    """A dataset with an H1 grid but no H2 study would leave the comparison half-done."""
    assert set(run_h1.DATASETS) == set(run_h2.DATASETS)


def test_the_two_datasets_share_the_protocol_that_makes_them_comparable():
    """Same n, same seeds, same epsilon grid. If these drift, a difference between the
    datasets is no longer attributable to the data."""
    assert run_h1.N_ROWS == run_h2.N_ROWS
    assert set(run_h2.EPS_GRID) <= set(run_h1.EPS_GRID)
    assert set(run_h2.SEEDS) <= set(run_h1.SEEDS)


def test_h2_measures_the_analogous_attributes_on_both_datasets():
    """sex/race on Adult, SEX/RAC1P on ACS — same count, so the tables line up."""
    assert len(run_h2.DATASETS["adult"]["attributes"]) == len(run_h2.DATASETS["acs"]["attributes"])
