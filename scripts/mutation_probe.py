"""A targeted mutation probe for the privacy-critical paths.

WHAT THIS IS, named accurately. It is NOT a general mutation tester. It applies a fixed,
hand-written list of semantically meaningful mutations to specific lines, runs the tests that
should notice, and reports how many were caught. `mutmut` refuses to run natively on Windows
and `cosmic-ray`'s runner fails to capture subprocess output here, so a general sweep was not
available — but a general sweep is also not obviously what this codebase needs.

WHY A HAND-WRITTEN LIST IS BETTER HERE. A generic AST mutator spends most of its budget on
mutations that are either trivially caught or semantically equivalent, and it has no notion of
which changes would be *dangerous*. The interesting question for a differential-privacy
implementation is narrower and sharper: if someone weakened a budget check, loosened a
suppression threshold, or made the calibration return the optimistic end of its bracket, would
anything fail? Every mutation below is a defect that would silently produce a release claiming
an epsilon it does not deliver. Several are near-misses of defects this project actually had.

WHAT THE SCORE MEANS AND DOES NOT MEAN. A caught mutation means at least one test fails when
that line is wrong. A survivor means the line can be wrong with the suite still green, which
is a gap worth naming. The denominator is a curated list, so the score is not comparable to a
published mutmut score on another project — it answers "are the dangerous paths defended",
not "what fraction of all possible mutants die".

Safety: the original file contents are held in memory and restored in a `finally`, so an
interrupted run cannot leave a mutated source behind. The probe refuses to start on a dirty
working tree for the files it touches, so a crash can always be recovered with `git checkout`.

Usage:
    python -m scripts.mutation_probe            # run every mutation
    python -m scripts.mutation_probe --list     # show them without running
"""

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

ACCOUNTING_TESTS = [
    "tests/test_accounting.py",
    "tests/test_accounting_properties.py",
    "tests/test_weighted_allocation.py",
]
PROFILER_TESTS = ["tests/test_profiler_soundness.py", "tests/test_data.py"]
PREFLIGHT_TESTS = ["tests/test_preflight.py"]
LEDGER_TESTS = ["tests/test_ledger_adversarial.py", "tests/test_ledger.py"]
AUDIT_TESTS = ["tests/test_steinke.py", "tests/test_subgroup_audit.py"]


@dataclass(frozen=True)
class Mutation:
    """One deliberate defect, and the tests that ought to notice it."""

    id: str
    path: str
    old: str
    new: str
    danger: str  # what a release would wrongly claim if this shipped
    tests: List[str] = field(default_factory=list)
    # Set when the mutation was investigated and found NOT to change observable behaviour in
    # the way its `danger` line describes. Equivalent mutants are excluded from the score's
    # denominator, which is standard practice — but only with a stated, checked reason, never
    # to make the number look better. Each string below records how it was verified.
    equivalent: str = ""


MUTATIONS: List[Mutation] = [
    # ---------------------------------------------------------------- accountant
    Mutation(
        "budget-off-by-one",
        "synthproof/accounting/accountant.py",
        "if new_eps > self.budget.epsilon:",
        "if new_eps > self.budget.epsilon * 1.05:",
        "A release could exceed its declared budget by 5% and still be accepted.",
        ACCOUNTING_TESTS,
    ),
    Mutation(
        "zero-noise-is-finite",
        "synthproof/accounting/accountant.py",
        "if spec.noise_scale == 0:\n            return dp_event.NonPrivateDpEvent()",
        "if spec.noise_scale < 0:\n            return dp_event.NonPrivateDpEvent()",
        "Zero noise would compose to a FINITE epsilon instead of infinity — a release with no "
        "protection carrying a real-looking bound. This is defect #2 from the audit history.",
        ACCOUNTING_TESTS,
        equivalent=(
            "Verified: dp_accounting returns inf for GaussianDpEvent(0.0) regardless, so the "
            "explicit NonPrivateDpEvent branch is defence-in-depth rather than the only "
            "protection. Removing it cannot produce a finite epsilon."
        ),
    ),
    Mutation(
        "unknown-mechanism-silently-gaussian",
        "synthproof/accounting/accountant.py",
        'raise ValueError(\n                f"Unknown mechanism {spec.name!r}. Supported: "',
        "return dp_event.GaussianDpEvent(noise_multiplier)  # noqa\n"
        "            raise ValueError(\n"
        '                f"Unknown mechanism {spec.name!r}. Supported: "',
        "An unrecognised mechanism would be accounted as Gaussian. Defect #3 from the audit "
        "history.",
        ACCOUNTING_TESTS,
    ),
    # ---------------------------------------------------------------- calibration
    Mutation(
        "calibration-returns-optimistic-bracket",
        "synthproof/accounting/calibration.py",
        "        if eps_at(mid) > target_eps:\n            lo = mid  # too little noise\n"
        "        else:\n            hi = mid  # enough noise\n\n    return hi",
        "        if eps_at(mid) > target_eps:\n            lo = mid  # too little noise\n"
        "        else:\n            hi = mid  # enough noise\n\n    return lo",
        "Calibration would return the end of the bracket that OVERSPENDS, so every release "
        "would deliver a larger epsilon than it claims.",
        ACCOUNTING_TESTS,
    ),
    Mutation(
        "weighted-shape-exponent",
        "synthproof/accounting/calibration.py",
        "shape = [((total_w / (x * k)) ** 0.5) for x in w]",
        "shape = [((total_w / (x * k)) ** 1.0) for x in w]",
        "The weighted allocation would misprice the split, so the H3 weighted arm would not "
        "spend the same total as the uniform arm.",
        ACCOUNTING_TESTS,
        equivalent=(
            "Verified: the exponent sets only the SHAPE of the split. The bisection still "
            "solves for the total against the accountant, so the never-overspend property "
            "holds and both H3 arms still cost the same. The mutant changes which columns get "
            "how much noise, not how much is spent."
        ),
    ),
    # ---------------------------------------------------------------- noise
    Mutation(
        "sigma-zero-allowed",
        "synthproof/accounting/noise.py",
        "if sigma <= 0:",
        "if sigma < 0:",
        "A sigma of exactly zero would be accepted, producing an unnoised release while the "
        "accountant charges a finite epsilon.",
        ACCOUNTING_TESTS,
        equivalent=(
            "Verified: with sigma=0 the sampler reaches -(|y| - 0/t)^2 / (2*0) and raises "
            "ZeroDivisionError. It fails loudly rather than silently emitting an unnoised "
            "release, so the guard is redundant with an arithmetic impossibility."
        ),
    ),
    # ---------------------------------------------------------------- profiler
    Mutation(
        "category-threshold-weakened",
        "synthproof/data/profiler.py",
        "threshold = self.category_threshold_factor * noise_scale * np.sqrt(2.0)",
        "threshold = 0.1 * noise_scale * np.sqrt(2.0)",
        "Rare categories would survive suppression, leaking values held by very few people. "
        "This is the family the un-noised-mode defect belonged to.",
        PROFILER_TESTS,
    ),
    Mutation(
        "public-bounds-ignored",
        "synthproof/data/profiler.py",
        "if bounds is not None:",
        "if bounds is None and False:",
        "Declared PUBLIC bounds would be ignored and re-derived noisily from the data, "
        "spending budget to rediscover a published fact and widening ranges absurdly.",
        PROFILER_TESTS,
    ),
    Mutation(
        "empty-domain-guesses-again",
        "synthproof/data/profiler.py",
        "            public = self._public_categories(dataset, col)\n"
        "            if public is not None:",
        "            public = list(counts)[:1] if counts else None\n"
        "            if public is not None:",
        "The empty-domain fallback would again return a data-derived category rather than the "
        "public domain — the exact critical defect fixed earlier in this project.",
        PROFILER_TESTS,
    ),
    # ---------------------------------------------------------------- preflight
    Mutation(
        "identifier-check-never-fires",
        "synthproof/data/preflight.py",
        "NEAR_UNIQUE_FRACTION = 0.5",
        "NEAR_UNIQUE_FRACTION = 50.0",
        "A column with one distinct value per row would be accepted, so identifier tables "
        "would reach the generator again.",
        PREFLIGHT_TESTS,
    ),
    Mutation(
        "row-floor-removed",
        "synthproof/data/preflight.py",
        "MIN_ROWS = 500",
        "MIN_ROWS = 0",
        "Tiny tables would be released, where any usable epsilon destroys the data entirely.",
        PREFLIGHT_TESTS,
    ),
    # ---------------------------------------------------------------- ledger
    Mutation(
        "head-not-checked",
        "synthproof/ledger/ledger.py",
        "        if valid:\n"
        "            head_reason = self._verify_head(conn, len(rows), expected_prev)",
        "        if valid and False:\n"
        "            head_reason = self._verify_head(conn, len(rows), expected_prev)",
        "Truncation would go undetected again: an operator could delete the entries recording "
        "a budget overspend and still pass verification.",
        LEDGER_TESTS,
    ),
    Mutation(
        "head-count-not-compared",
        "synthproof/ledger/ledger.py",
        'if row["entry_count"] != entry_count:',
        'if row["entry_count"] != entry_count and False:',
        "The signed head would stop pinning the chain LENGTH, which is the specific property "
        "that detects truncation.",
        LEDGER_TESTS,
    ),
    # ---------------------------------------------------------------- audit
    Mutation(
        "ceiling-inflated",
        "synthproof/audit/steinke.py",
        "    a = alpha ** (1.0 / num_guesses)",
        "    a = alpha ** (1.0 / (num_guesses * 10))",
        "The reported audit ceiling would be far too high, so an uninformative audited "
        "epsilon of 0 would look like meaningful evidence of no leakage.",
        AUDIT_TESTS,
    ),
]


def run_tests(tests: List[str]) -> bool:
    """True when the suite passes. Uses this interpreter, not whatever `python` resolves to."""
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-x",
            "-q",
            "--no-header",
            "--no-cov",
            "-p",
            "no:cacheprovider",
            *tests,
        ],
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--list", action="store_true", help="Show the mutations without running.")
    ap.add_argument("--out", default="results/mutation_probe.json")
    args = ap.parse_args()

    if args.list:
        for m in MUTATIONS:
            print(f"{m.id:<36} {m.path}")
            print(f"    {m.danger}")
        print(f"\n{len(MUTATIONS)} mutations")
        return

    dirty = subprocess.run(
        ["git", "status", "--porcelain", *{m.path for m in MUTATIONS}],
        capture_output=True,
        text=True,
    ).stdout.strip()
    if dirty:
        raise SystemExit(
            "Refusing to run: the files this probe mutates have uncommitted changes.\n"
            f"{dirty}\n"
            "Commit or stash first, so an interrupted run can be recovered with git checkout."
        )

    print(f"Running {len(MUTATIONS)} targeted mutations.\n")
    t0 = time.time()
    results = []

    for m in MUTATIONS:
        path = Path(m.path)
        # Byte-level round trip. Reading as text and writing back with an explicit newline
        # translation rewrote CRLF files as LF, so a completed probe run left the tree dirty
        # with a diff that was pure line endings -- and the next run then refused to start on
        # its own residue. Bytes in, bytes out.
        original_bytes = path.read_bytes()
        original = original_bytes.decode("utf-8")
        if m.old not in original:
            results.append({"id": m.id, "status": "NOT APPLIED", "danger": m.danger})
            print(f"  {m.id:<36} SKIPPED - anchor text not found (code moved?)")
            continue
        try:
            path.write_bytes(original.replace(m.old, m.new, 1).encode("utf-8"))
            caught = not run_tests(m.tests)
        finally:
            path.write_bytes(original_bytes)

        if caught:
            status = "caught"
        elif m.equivalent:
            status = "equivalent"
        else:
            status = "SURVIVED"
        results.append(
            {
                "id": m.id,
                "status": status,
                "path": m.path,
                "danger": m.danger,
                "tests": m.tests,
                "equivalent": m.equivalent,
            }
        )
        label = {"caught": "caught", "equivalent": "equivalent (verified)"}.get(
            status, "*** SURVIVED ***"
        )
        print(f"  {m.id:<36} {label}")

    caught = [r for r in results if r["status"] == "caught"]
    equivalent = [r for r in results if r["status"] == "equivalent"]
    survivors = [r for r in results if r["status"] == "SURVIVED"]
    # Equivalent mutants are excluded from the denominator — standard practice, and here every
    # exclusion carries a justification that was checked by hand. Note the ordering above: a
    # mutation marked equivalent that turns out to be CAUGHT is still reported as caught, so
    # the marking can only remove a mutant from the denominator, never inflate the numerator.
    denom = len(caught) + len(survivors)
    score = len(caught) / denom if denom else 0.0

    print("\n" + "=" * 70)
    print(f"MUTATION SCORE: {len(caught)}/{denom} = {score:.0%}")
    print(f"  ({len(equivalent)} verified-equivalent mutants excluded from the denominator)")
    print("=" * 70)
    if survivors:
        print("\nSurvivors — each is a line that can be wrong with the suite still green:\n")
        for r in survivors:
            print(f"  {r['id']}  ({r['path']})")
            print(f"     {r['danger']}\n")
    else:
        print("\nEvery non-equivalent mutation was caught.")
    if equivalent:
        print("Excluded as equivalent, with how each was checked:\n")
        for r in equivalent:
            print(f"  {r['id']}\n     {r['equivalent']}\n")

    payload = {
        "kind": "targeted mutation probe (curated list, not a general sweep)",
        "score": score,
        "caught": len(caught),
        "survived": len(survivors),
        "equivalent_excluded": len(equivalent),
        "denominator": denom,
        "elapsed_seconds": round(time.time() - t0, 1),
        "results": results,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
