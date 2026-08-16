"""CLI input validation.

The CLI is the only surface a non-expert touches, so a privacy parameter that is silently
accepted here becomes a false claim in a Privacy Data Sheet someone else reads.
"""

import pytest
from click.testing import CliRunner

from synthproof.cli import EPS_REFUSE_ABOVE, EPS_WARN_ABOVE, main


@pytest.fixture()
def csv(tmp_path):
    import numpy as np
    import pandas as pd

    # Above the pre-flight row floor. These tests are about epsilon validation, not admission
    # control; a table below the floor is refused before epsilon is ever used, which would make
    # them test the wrong thing. Admission control has its own tests in tests/test_preflight.py.
    rng = np.random.default_rng(0)
    n = 800
    p = tmp_path / "t.csv"
    pd.DataFrame(
        {
            "age": rng.integers(18, 90, n),
            "hours": rng.integers(1, 60, n),
            "grp": rng.choice(["a", "b", "c"], n),
            "label": rng.choice(["yes", "no"], n),
        }
    ).to_csv(p, index=False)
    return str(p)


def run(csv, tmp_path, *extra):
    return CliRunner().invoke(
        main, ["run", "--input", csv, "--out", str(tmp_path / "o.json"), *extra]
    )


# ------------------------------------------------------------------ epsilon


@pytest.mark.parametrize("bad", ["0", "-1", "-0.5"])
def test_non_positive_epsilon_is_rejected_with_a_usage_error(csv, tmp_path, bad):
    """REGRESSION: `--eps 0` and `--eps -1` used to surface as a raw Python traceback from
    `BudgetPlan.split` deep in the call stack, not as a usage error."""
    r = run(csv, tmp_path, "--eps", bad)
    assert r.exit_code != 0
    assert "epsilon must be positive" in r.output
    assert "Traceback" not in r.output, "validation must happen before the pipeline starts"


def test_an_absurd_epsilon_is_refused_rather_than_certified(csv, tmp_path):
    """REGRESSION: `--eps 1000000000` was accepted in silence and produced a Privacy Data
    Sheet reporting `proved eps=999986985.822`. Printing that number without comment lends
    credibility to something that is not privacy."""
    r = run(csv, tmp_path, "--eps", str(EPS_REFUSE_ABOVE * 10))
    assert r.exit_code != 0
    assert "not a privacy parameter" in r.output


def test_the_refusal_points_at_the_honest_alternative(csv, tmp_path):
    """Someone who wants an unprotected baseline should be sent to the labelled controls,
    not left to fake one by inflating epsilon."""
    r = run(csv, tmp_path, "--eps", str(EPS_REFUSE_ABOVE * 10))
    assert "leaky" in r.output


def test_a_large_but_legal_epsilon_warns_and_still_runs(csv, tmp_path):
    """A warning, not a block: sweeping to high epsilon is a legitimate research move, and
    refusing it would break the frontier experiments."""
    r = run(csv, tmp_path, "--eps", str(EPS_WARN_ABOVE * 5))
    assert r.exit_code == 0, r.output
    assert "WARNING" in r.output
    assert "does not mean much" in r.output


def test_a_normal_epsilon_produces_no_warning(csv, tmp_path):
    """A warning that fires on ordinary use is a warning users learn to ignore."""
    r = run(csv, tmp_path, "--eps", "1.0")
    assert r.exit_code == 0, r.output
    assert "far above the range" not in r.output


# ------------------------------------------------------------------ delta


@pytest.mark.parametrize("bad", ["0", "1", "5", "-0.1"])
def test_delta_outside_the_unit_interval_is_rejected(csv, tmp_path, bad):
    """Delta is a probability. A value outside (0, 1) is not a loose setting, it is nonsense."""
    r = run(csv, tmp_path, "--eps", "1.0", "--delta", bad)
    assert r.exit_code != 0
    assert "delta must be in (0, 1)" in r.output


def test_a_large_delta_warns(csv, tmp_path):
    r = run(csv, tmp_path, "--eps", "1.0", "--delta", "0.05")
    assert "WARNING" in r.output
    assert "delta" in r.output.lower()


# ------------------------------------------------------------------ other surfaces


def test_an_unknown_mechanism_is_rejected_by_click_choice(csv, tmp_path):
    r = run(csv, tmp_path, "--eps", "1.0", "--mechanism", "bogus")
    assert r.exit_code != 0
    assert "bogus" in r.output


def test_a_missing_input_file_is_a_usage_error_not_a_traceback(tmp_path):
    r = CliRunner().invoke(main, ["run", "--input", "nope.csv", "--eps", "1.0"])
    assert r.exit_code != 0
    assert "does not exist" in r.output
    assert "Traceback" not in r.output


def test_the_demo_command_validates_epsilon_too(tmp_path):
    """The demo is the first thing anyone runs, so it must not be the lax path."""
    r = CliRunner().invoke(main, ["demo", "--rows", "50", "--eps", "0"])
    assert r.exit_code != 0
    assert "epsilon must be positive" in r.output


def test_help_lists_every_command_a_user_needs(tmp_path):
    r = CliRunner().invoke(main, ["--help"])
    assert r.exit_code == 0
    for cmd in ("run", "verify", "keygen", "demo", "mechanisms", "infer-schema"):
        assert cmd in r.output


# ------------------------------------------------------------------ admission control


def test_a_table_below_the_row_floor_is_refused_by_the_cli(tmp_path):
    """The refusal must reach the user as an actionable message, not a traceback.

    Epsilon validation fires in a click callback and so precedes this; a table that clears
    epsilon must still be declined if it cannot be released honestly.
    """
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(0)
    p = tmp_path / "small.csv"
    pd.DataFrame({"age": rng.integers(18, 90, 50), "grp": rng.choice(["a", "b"], 50)}).to_csv(
        p, index=False
    )

    r = CliRunner().invoke(
        main, ["run", "--input", str(p), "--out", str(tmp_path / "o.json"), "--eps", "1.0"]
    )
    assert r.exit_code != 0
    assert "R1" in r.output
    assert "500-row floor" in r.output
    assert "Traceback" not in r.output


def test_the_run_output_states_what_epsilon_means(csv, tmp_path):
    """Epsilon alone is not interpretable; the odds statement is what a reader can act on."""
    r = run(csv, tmp_path, "--eps", "1.0")
    assert r.exit_code == 0, r.output
    assert "50 in 100" in r.output


def test_an_inferred_schema_is_disclosed_in_the_run_output(csv, tmp_path):
    """Without --schema the bounds were read from the data. The user must be told, every time."""
    r = run(csv, tmp_path, "--eps", "1.0")
    assert "inferred-nonprivate" in r.output
