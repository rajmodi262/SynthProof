"""Re-analyses the committed H2 results with multiplicity control, equivalence and power.

Reads results/h2_subgroups.json — it does NOT re-run any experiment, so the numbers here are
the same ones already committed, viewed through a stricter lens.

Usage:
    python -m scripts.analyse_h2
"""

import json
from pathlib import Path

import numpy as np

from synthproof.audit.equivalence import (
    H2_BOUND_JUSTIFICATION,
    H2_EQUIVALENCE_BOUND_ACCURACY,
    H2Analysis,
    correct_multiplicity,
    describe_detectability,
    format_h2_table,
    test_equivalence,
)

SRC = Path("results/h2_subgroups.json")
OUT = Path("results/h2_analysis.json")


def main():
    if not SRC.exists():
        raise SystemExit(f"{SRC} not found. Run `make h2` first.")
    data = json.loads(SRC.read_text(encoding="utf-8"))

    labels, pvals, epsilons, accuracies = [], [], [], []
    canary_counts = set()

    for cell in data["cells"]:
        for g in cell["subgroups"]:
            labels.append(f"{cell['attribute']}={g['subgroup']} eps={cell['target_eps']}")
            pvals.append(float(g["mean_p_value"]))
            epsilons.append(float(g["mean_audited_eps"]))
            accuracies.append(float(g["mean_accuracy"]))
            canary_counts.add(int(g["num_canaries"]))

    multiplicity = correct_multiplicity(labels, pvals)

    # Equivalence: is each subgroup's adversary accuracy within the pre-specified margin of
    # chance? The reference is a chance sample of the same size — the null being tested
    # against is "an adversary that guesses at random".
    #
    # LIMITATION, stated because it affects how much weight this carries. The per-canary
    # correct/incorrect outcomes are NOT stored in h2_subgroups.json; only the mean accuracy
    # is. The Bernoulli draws below therefore RECONSTRUCT a sample consistent with the
    # recorded sufficient statistic (correct = accuracy x m) rather than replaying the actual
    # outcomes. The seed is fixed so the result is reproducible, but a different seed would
    # move each TOST p-value slightly. Storing the raw outcome vectors in the H2 runner would
    # remove this reconstruction entirely and is the correct fix; it is recorded as a
    # limitation rather than silently accepted.
    rng = np.random.default_rng(0)
    equivalence = []
    for cell in data["cells"]:
        for g in cell["subgroups"]:
            m = int(g["num_canaries"])
            # Bernoulli(0.5) draws are the exact null for a guess-counting adversary.
            observed = rng.binomial(1, g["mean_accuracy"], size=m).astype(float)
            chance = rng.binomial(1, 0.5, size=m).astype(float)
            equivalence.append(test_equivalence(
                label=f"{cell['attribute']}={g['subgroup']} eps={cell['target_eps']}",
                sample=observed, reference=chance,
                bound=H2_EQUIVALENCE_BOUND_ACCURACY,
                justification=H2_BOUND_JUSTIFICATION,
            ))

    detectability = describe_detectability(
        num_canaries=min(canary_counts), observed_epsilons=epsilons,
        observed_accuracies=accuracies,
    )

    analysis = H2Analysis(multiplicity=multiplicity, equivalence=equivalence,
                          detectability=detectability)

    print(format_h2_table(analysis))
    print("\n" + "=" * 78)
    print("VERDICT")
    print("=" * 78)
    print(analysis.verdict())

    payload = analysis.to_dict()
    payload["source"] = str(SRC)
    payload["source_n_rows"] = data.get("n_rows")
    payload["source_seeds"] = data.get("seeds")
    OUT.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
