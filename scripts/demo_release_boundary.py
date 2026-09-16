"""A membership-inference attack that a signed DP release used to allow, and the fix that stops it.

Run:  python scripts/demo_release_boundary.py

The attacker is the standard differential-privacy adversary: they know every record in the table
except one, and want to learn whether one target person is in it. They never see the raw data --
only the released synthetic table and its signed Privacy Data Sheet.

The sheet used to record the run `seed`. Every noise draw in the pipeline derives from it, so the
release is a deterministic function of (table, seed). The attacker rebuilds the release for the
two tables they are deciding between -- "target present" and "target absent" -- using the published
seed, and sees which one reproduces the release they were given. That decides membership with
certainty, whatever epsilon claims.

This script runs that attack against a release built the OLD way (seed in the sheet) and the FIXED
way (seed withheld), and runs `synthproof boundary-audit` on each sheet. No epsilon changes between
the two: the whole difference is what the artefact discloses.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from synthproof.accounting.accountant import Accountant  # noqa: E402
from synthproof.audit import boundary  # noqa: E402
from synthproof.data.dataset import TabularDataset  # noqa: E402
from synthproof.data.profiler import DPDomainProfiler  # noqa: E402
from synthproof.data.schema import CATEGORICAL, ColumnSpec, Schema  # noqa: E402
from synthproof.frontier.experiment import MECHANISMS  # noqa: E402

EPS = 1.0
DELTA = 1e-5
N = 800
RELEASE_ROWS = 700
TRIALS = 12
MECHANISM = "independent"  # fast and fully deterministic; the attack is mechanism-agnostic


def _bar(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def _world(rng: np.random.Generator) -> tuple[TabularDataset, TabularDataset, pd.Series]:
    """A table, the same table with one target record removed, and the target row itself."""
    schema = Schema(
        [
            ColumnSpec("dept", CATEGORICAL, categories=[f"d{i}" for i in range(6)]),
            ColumnSpec("band", CATEGORICAL, categories=[f"b{i}" for i in range(5)]),
            ColumnSpec("flag", CATEGORICAL, categories=["yes", "no"]),
        ]
    )
    df = pd.DataFrame(
        {
            "dept": rng.choice([f"d{i}" for i in range(6)], N),
            "band": rng.choice([f"b{i}" for i in range(5)], N),
            "flag": rng.choice(["yes", "no"], N),
        }
    )
    present = TabularDataset(df, name="staff", schema=schema)
    absent = TabularDataset(df.iloc[:-1].reset_index(drop=True), name="staff", schema=schema)
    return present, absent, df.iloc[-1]


def _release(ds: TabularDataset, seed: int) -> pd.DataFrame:
    """One synthetic release. Deterministic in (ds, seed): this is the whole point."""
    acc = Accountant(budget_eps=EPS * 1.02, budget_delta=DELTA)
    prof = DPDomainProfiler(accountant=acc, eps_budget=0.1 * EPS).profile(ds, seed=seed)
    gen = MECHANISMS[MECHANISM](seed=seed)
    gen.fit(ds, prof, acc, target_eps=0.9 * EPS)
    return gen.generate(num_samples=RELEASE_ROWS).reset_index(drop=True)


def _attacker_guess(
    released: pd.DataFrame,
    present: TabularDataset,
    absent: TabularDataset,
    seed_known_to_attacker: int | None,
    rng: np.random.Generator,
) -> str:
    """Return the attacker's verdict: 'present', 'absent', or 'cannot tell'.

    With the seed, the attacker replays both candidate worlds and matches exactly. Without it, the
    best they can do is replay with a seed of their own -- which reproduces neither.
    """
    if seed_known_to_attacker is None:
        guess_seed = int(rng.integers(0, 2**31 - 1))
        rep_present = _release(present, guess_seed)
        rep_absent = _release(absent, guess_seed)
    else:
        rep_present = _release(present, seed_known_to_attacker)
        rep_absent = _release(absent, seed_known_to_attacker)

    match_present = rep_present.equals(released)
    match_absent = rep_absent.equals(released)
    if match_present and not match_absent:
        return "present"
    if match_absent and not match_present:
        return "absent"
    return "cannot tell"


def _run(seed_in_sheet: bool) -> dict:
    """Play the attack `TRIALS` times. The truth is always 'present'."""
    correct = wrong = undecided = 0
    for t in range(TRIALS):
        rng = np.random.default_rng(1000 + t)
        present, absent, _ = _world(rng)
        run_seed = int(rng.integers(0, 2**31 - 1))  # the curator's seed for this release
        released = _release(present, run_seed)  # truth: the target IS in the data

        seed_the_attacker_has = run_seed if seed_in_sheet else None
        guess = _attacker_guess(released, present, absent, seed_the_attacker_has, rng)
        if guess == "present":
            correct += 1
        elif guess == "absent":
            wrong += 1
        else:
            undecided += 1
    return {"correct": correct, "wrong": wrong, "undecided": undecided, "trials": TRIALS}


def _sheet(seed_in_sheet: bool) -> dict:
    """A minimal sheet in each style, for boundary-audit to read."""
    common = {
        "dataset_name": "staff",
        "mechanism": MECHANISM,
        "total_proved_eps": EPS,
        "total_audited_eps": 0.0,
        "evaluation": {"tstr_f1": 0.61},
        "domain_source": "declared",
    }
    if seed_in_sheet:
        # The old artefact: seed published, exact row count, unkeyed hash, unlabelled metrics.
        return {**common, "seed": 1234567, "num_rows": N, "input_fingerprint": "a" * 64}
    # The fixed artefact: seed withheld, declared public size, evaluation labelled.
    return {
        **common,
        "seed": None,
        "num_rows": RELEASE_ROWS,
        "release_rows_source": "declared",
        "evaluation_privacy": "measured on the real table; not covered by epsilon",
    }


def main() -> None:
    _bar("SynthProof -- the seed that turned a signed DP release into a membership test")
    print(
        f"Mechanism {MECHANISM!r}, epsilon {EPS}, {N}-row table, {RELEASE_ROWS}-row release, "
        f"{TRIALS} trials.\nThe target person is ALWAYS in the data. A correct attacker says "
        "'present' every time."
    )

    for seed_in_sheet in (True, False):
        style = (
            "OLD  (seed printed on the signed sheet)"
            if seed_in_sheet
            else "FIXED (seed withheld; drawn from the OS)"
        )
        _bar(f"Release style: {style}")

        result = _run(seed_in_sheet)
        print(
            f"  attacker correct : {result['correct']:>2}/{result['trials']}\n"
            f"  attacker wrong   : {result['wrong']:>2}/{result['trials']}\n"
            f"  cannot decide    : {result['undecided']:>2}/{result['trials']}"
        )
        if seed_in_sheet:
            print("  -> the attacker reads membership straight off the artefact.")
        else:
            print(
                "  -> the attacker is reduced to a coin they cannot even flip: no replay matches."
            )

        report = boundary.audit_sheet(_sheet(seed_in_sheet))
        verdict = "FAILED -- discloses beyond epsilon" if not report.passed else "PASSED"
        print(f"\n  boundary-audit: {verdict}")
        for f in report.leaks:
            print(f"    LEAK {f.code} {f.field}: {f.finding}")

    _bar("Bottom line")
    print(
        "Same mechanism, same epsilon. The only change is what the signed sheet reveals.\n"
        "Found and fixed in SynthProof on 2026-09-14 (docs/design/PUBLIC_RELEASE_BOUNDARY.md).\n"
        "Run the auditor yourself on any release:  synthproof boundary-audit <sheet.json>"
    )


if __name__ == "__main__":
    main()
