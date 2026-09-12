"""The two CLI commands no test invoked: `audit-power` and `export-capsule`.

Task 3.2 of docs/ROAD_TO_TEN.md. A census of `CliRunner().invoke(main, [...])` calls across
the three existing CLI test files found `keygen` invoked 8 times, `verify` 5, `run` 3 -- and
`audit-power` and `export-capsule` never.

`audit-power` is not a convenience command. It is the tool that exists so nobody repeats the
experiment that disqualified H1's privacy half: 60 canaries against a proved epsilon of 7.36,
where the instrument could not have reported above 2.97. A power-analysis tool whose verdict
branch is untested could print CAN where it should print CANNOT, and the whole point of it is
that verdict. So the verdict is tested in both directions, in both coordinate systems.

Expected values are computed from `audit.steinke` / `audit.gdp` rather than hardcoded, so these
tests pin the CLI's wiring to the functions rather than duplicating their arithmetic -- the
functions themselves are pinned bit-identical to the closed form in test_audit_power.py.
"""

import json

import numpy as np
import pandas as pd
import pytest
from click.testing import CliRunner

from synthproof.audit.gdp import max_provable_mu, runs_needed_for_mu
from synthproof.audit.steinke import canaries_needed_for, max_provable_epsilon
from synthproof.capsule.generator import extract_capsule_payload
from synthproof.cli import main


def _invoke(*args):
    return CliRunner().invoke(main, list(args))


def _json(*args):
    r = _invoke(*args, "--json")
    assert r.exit_code == 0, r.output
    return json.loads(r.output)


# ------------------------------------------------------------------ audit-power: epsilon


def test_the_h1_budget_is_reported_as_unable_to_certify_its_own_epsilon():
    """The experiment this command exists to prevent, reproduced as its verdict."""
    report = _json("audit-power", "--eps", "7.36", "--canaries", "60")

    assert report["ceiling"] == pytest.approx(max_provable_epsilon(60, 0.05))
    assert report["ceiling"] < 7.36
    assert report["can_certify_target"] is False
    assert report["canaries_required_total"] == canaries_needed_for(7.36, 0.05)


def test_a_sufficient_budget_is_reported_as_able_to_certify():
    """The other direction. A tool that only ever says CANNOT is not measuring anything."""
    needed = canaries_needed_for(1.0, 0.05)
    report = _json("audit-power", "--eps", "1.0", "--canaries", str(needed))

    assert report["can_certify_target"] is True
    assert report["ceiling"] >= 1.0


def test_the_human_readable_verdict_matches_the_json_verdict():
    """The text a person reads must say the same thing as the field a script reads."""
    cannot = _invoke("audit-power", "--eps", "7.36", "--canaries", "60")
    assert cannot.exit_code == 0, cannot.output
    assert "CANNOT certify" in cannot.output
    assert "uninformative, not evidence of no leakage" in cannot.output

    can = _invoke("audit-power", "--eps", "1.0", "--canaries", "1000")
    assert can.exit_code == 0, can.output
    assert "CAN certify" in can.output and "CANNOT" not in can.output


def test_without_a_budget_it_reports_the_requirement_and_asks_for_one():
    r = _invoke("audit-power", "--eps", "4.0")
    assert r.exit_code == 0, r.output
    assert f"{canaries_needed_for(4.0, 0.05):,}" in r.output
    assert "Pass --canaries" in r.output
    assert "VERDICT" not in r.output


def test_subgroups_split_the_budget_and_multiply_the_requirement():
    """H2 splits its canaries across subgroups; each subgroup gets the ceiling of its SHARE."""
    report = _json("audit-power", "--eps", "2.0", "--canaries", "600", "--subgroups", "5")

    per_group = canaries_needed_for(2.0, 0.05)
    assert report["canaries_required_per_subgroup"] == per_group
    assert report["canaries_required_total"] == per_group * 5
    assert report["canaries_per_subgroup"] == 120
    assert report["ceiling"] == pytest.approx(max_provable_epsilon(120, 0.05))

    text = _invoke("audit-power", "--eps", "2.0", "--canaries", "600", "--subgroups", "5")
    assert "budget split equally" in text.output and "per subgroup" in text.output


def test_more_subgroups_than_canaries_gives_a_zero_ceiling_rather_than_a_crash():
    report = _json("audit-power", "--eps", "1.0", "--canaries", "3", "--subgroups", "5")
    assert report["canaries_per_subgroup"] == 0
    assert report["ceiling"] == 0.0
    assert report["can_certify_target"] is False


# ------------------------------------------------------------------ audit-power: mu-GDP


def test_gdp_mode_reports_runs_per_world_not_canaries():
    """A GDP audit's budget is a different unit, and conflating the two is the error to avoid."""
    report = _json("audit-power", "--gdp", "--mu", "1.0")

    assert report["metric"] == "mu-GDP"
    assert report["target_mu"] == 1.0
    assert report["runs_required_per_world"] == runs_needed_for_mu(1.0, 0.05)
    assert "canaries_required_total" not in report
    assert report["target_mu_source"] == "given directly"


def test_gdp_mode_can_derive_mu_from_epsilon_and_says_that_comparator_is_loose():
    report = _json("audit-power", "--gdp", "--eps", "1.0", "--delta", "1e-5")
    assert report["target_mu"] > 0
    assert "LOOSE comparator" in report["target_mu_source"]


@pytest.mark.parametrize(
    "runs, certifies",
    [(1000, True), (5, False)],
    ids=["budget-sufficient", "budget-insufficient"],
)
def test_gdp_verdict_in_both_directions(runs, certifies):
    report = _json("audit-power", "--gdp", "--mu", "1.0", "--runs", str(runs))
    assert report["ceiling_mu"] == pytest.approx(max_provable_mu(runs, runs, 0.05))
    assert report["can_certify_target"] is certifies

    text = _invoke("audit-power", "--gdp", "--mu", "1.0", "--runs", str(runs)).output
    assert ("CANNOT certify" in text) is (not certifies)


def test_gdp_text_mode_without_runs_prints_the_requirement():
    r = _invoke("audit-power", "--gdp", "--mu", "0.5")
    assert r.exit_code == 0, r.output
    assert "runs required per world" in r.output
    assert "VERDICT" not in r.output


# ------------------------------------------------------------------ audit-power: bad input


@pytest.mark.parametrize(
    "args, message",
    [
        (["--eps", "1.0", "--subgroups", "0"], "--subgroups must be at least 1"),
        (["--eps", "1.0", "--mu", "1.0"], "--mu requires --gdp"),
        ([], "--eps is required"),
        (["--eps", "1.0", "--runs", "10"], "--runs requires --gdp"),
        (["--eps", "1.0", "--canaries", "0"], "--canaries must be at least 1"),
        (["--gdp", "--mu", "1.0", "--runs", "0"], "--runs must be at least 1"),
    ],
    ids=[
        "zero-subgroups",
        "mu-without-gdp",
        "no-target",
        "runs-without-gdp",
        "zero-canaries",
        "zero-runs",
    ],
)
def test_incoherent_requests_are_refused_with_the_reason(args, message):
    """Each refusal is a question that has no answer, not a question with answer zero."""
    r = _invoke("audit-power", *args)
    assert r.exit_code != 0
    assert message in r.output


# ------------------------------------------------------------------ export-capsule


@pytest.fixture()
def sheet_and_data(tmp_path, monkeypatch):
    """A real sheet produced through `run`, and the synthetic table it describes."""
    monkeypatch.setenv("SYNTHPROOF_KEY_DIR", str(tmp_path / "keys"))
    assert _invoke("keygen", "--key-dir", str(tmp_path / "keys")).exit_code == 0

    rng = np.random.default_rng(0)
    n = 600
    src = tmp_path / "in.csv"
    pd.DataFrame(
        {
            "age": rng.integers(18, 90, n),
            "hours": rng.integers(1, 60, n),
            "grp": rng.choice(list("abc"), n),
            "label": rng.choice(["yes", "no"], n),
        }
    ).to_csv(src, index=False)

    sheet, synth = tmp_path / "sheet.json", tmp_path / "synth.csv"
    r = _invoke(
        "run",
        "--input", str(src),
        "--out", str(sheet),
        "--eps", "1.0",
        "--sign",
        "--synthetic-out", str(synth),
    )  # fmt: skip
    assert r.exit_code == 0, r.output
    return sheet, synth


def test_export_capsule_writes_a_single_self_contained_html_file(tmp_path, sheet_and_data):
    sheet, synth = sheet_and_data
    out = tmp_path / "release.html"

    r = _invoke(
        "export-capsule", "--sheet", str(sheet), "--data", str(synth), "--out", str(out),
        "--curator", "Test Curator",
    )  # fmt: skip
    assert r.exit_code == 0, r.output
    assert "SUCCESS" in r.output

    html = out.read_text(encoding="utf-8")
    assert html.lstrip().lower().startswith("<!doctype html")
    assert "Test Curator" in html

    # The sheet must travel into the capsule EXACTLY, or the capsule verifies nothing. It is
    # embedded base64-encoded, so the check decodes it the way a verifier would rather than
    # searching the page text. (A first draft searched for a 6-character prefix of the float
    # and failed: the page DISPLAYS the value rounded to 3 decimals and carries the exact one
    # only inside the encoded payload. The capsule was right; the test was not.)
    proved = json.loads(sheet.read_text(encoding="utf-8"))["total_proved_eps"]
    payload = extract_capsule_payload(out)
    assert payload["sheet"]["total_proved_eps"] == proved
    assert f"{proved:.3f}" in html  # and the rounded headline a person reads agrees with it

    # The retired green-tick bypass must not come back through this entry point.
    assert "Proof Format Verified" not in html


def test_export_capsule_reads_parquet_as_well_as_csv(tmp_path, sheet_and_data):
    pytest.importorskip("pyarrow")
    sheet, synth = sheet_and_data
    pq = tmp_path / "synth.parquet"
    pd.read_csv(synth).to_parquet(pq)

    out = tmp_path / "from_parquet.html"
    r = _invoke("export-capsule", "--sheet", str(sheet), "--data", str(pq), "--out", str(out))
    assert r.exit_code == 0, r.output
    assert out.exists() and out.stat().st_size > 0


def test_export_capsule_refuses_a_missing_sheet(tmp_path):
    csv = tmp_path / "x.csv"
    csv.write_text("a\n1\n", encoding="utf-8")
    r = _invoke("export-capsule", "--sheet", str(tmp_path / "nope.json"), "--data", str(csv))
    assert r.exit_code != 0
