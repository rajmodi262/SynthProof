"""Measures the canary auditor's detection floor on UCI Adult.

This is the experiment that makes every `eps_audited = 0` in this repository interpretable.
Until it exists, a null audit result cannot be distinguished from a broken instrument.

Usage:
    .venv311/Scripts/python.exe -m scripts.run_detection_floor
"""

import json

from synthproof.audit.detection_floor import (
    format_floor_table,
    measure_detection_floor,
)
from synthproof.data.datasets import load_adult
from synthproof.generators.leaky import LeakyGenerator

N_ROWS = 3000
# The grid extends well past the 60 canaries the H1 experiments use, because a smoke test on
# the toy table already showed 5% leakage undetected at m=200. If the floor for realistic
# leakage sits above the count we actually run with, that is the finding.
CANARY_COUNTS = (10, 25, 50, 100, 200, 400, 800)
LEAK_FRACTIONS = (0.0, 0.01, 0.05, 0.25, 1.0)
SEEDS = (0, 1, 2, 3, 4)


def main():
    ds = load_adult()
    ds.df = ds.df.sample(n=N_ROWS, random_state=0).reset_index(drop=True)

    print(f"dataset: UCI Adult n={ds.num_rows} x {ds.num_cols}")
    print(f"canary counts: {CANARY_COUNTS}")
    print(f"leak fractions: {LEAK_FRACTIONS}")
    print(f"seeds: {SEEDS}\n")

    result = measure_detection_floor(
        ds,
        generator_factory=lambda leak, seed: LeakyGenerator(seed=seed, leak_fraction=leak),
        canary_counts=CANARY_COUNTS,
        leak_fractions=LEAK_FRACTIONS,
        seeds=SEEDS,
        progress=lambda m: print(m, flush=True),
    )

    print("\n" + format_floor_table(result))

    with open("results/detection_floor.json", "w", encoding="utf-8") as f:
        json.dump(result.to_dict(), f, indent=2)
    print("\nwrote results/detection_floor.json")

    # The sanity checks that make the sweep trustworthy. A floor study whose own controls
    # fail says nothing about the auditor.
    full = result.floor_for(1.0)
    clean = result.floor_for(0.0)

    positive = "OK" if full is not None else (
        "FAILED - the auditor cannot see the worst possible release")
    negative = "OK - no false positive" if clean is None else (
        "FAILED - fired on a release containing no real records")

    print("\nsanity checks")
    print(f"  verbatim release (leak=1.0): floor m={full}   {positive}")
    print(f"  shuffled release (leak=0.0): floor m={clean}   {negative}")

    if full is None or clean is not None:
        raise SystemExit(
            "\nThe floor study's own controls failed, so nothing in the table above can be "
            "trusted. Fix the auditor before reporting any null result."
        )


if __name__ == "__main__":
    main()
