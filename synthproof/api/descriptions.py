"""What a mechanism IS, and what the auditor CAN SEE.

Reference data and the two functions that read it. No routes, no state, no I/O -- which is
why it can sit below both the run pipeline and the dataset routes without either importing
the other. It used to live inside the run module, and `/api/mechanisms` reaching back for
MECHANISM_INFO while the pipeline reached forward for `_load_dataset` was a genuine cycle.

The audit ceiling here is not decoration. An `eps_audited` of 0 reported WITHOUT the maximum
the instrument could have certified reads as "no leakage" when what it means is "below
resolution", and those are different claims.
"""

from synthproof.frontier.experiment import MECHANISMS  # noqa: F401  (re-exported)

MECHANISM_INFO = {
    "independent": {
        "label": "Independent marginals",
        "family": "baseline",
        "blurb": "One noisy 1-D marginal per column, sampled independently. Destroys all "
        "cross-column structure by construction — the ablation baseline.",
        "implemented": True,
    },
    "moments": {
        "label": "Per-column Gaussian",
        "family": "baseline",
        "blurb": "DP-noised per-column moments: a mean and standard deviation per numeric "
        "column, a histogram per categorical one, every column sampled independently. No "
        "covariance and no rank transform, so no cross-column correlation survives. Kept as "
        "a second independent-marginal control.",
        "implemented": True,
    },
    "pairwise": {
        "label": "Pairwise tree",
        "family": "structured",
        "blurb": "Measures 2-way marginals along a fixed public spanning tree and samples "
        "ancestrally, so pairwise dependence survives. Not MST — structure is not "
        "selected from the data.",
        "implemented": True,
    },
    "aim": {
        "label": "AIM (private-PGM)",
        "family": "structured",
        "blurb": "Adaptive marginal selection by report-noisy-max plus graphical-model "
        "inference. Selection is charged to the accountant. Requires private-pgm.",
        "implemented": True,
    },
}

# Measured by scripts/run_detection_floor.py on UCI Adult, n=3000, 5 seeds, alpha=0.05.
# See results/DETECTION_FLOOR.md. These are the auditor's WORKING RANGE, and without them a
# reported `eps_audited = 0` is indistinguishable from a broken instrument.
#
# The ceiling matters more than the floor: eps_audited = log(TPR_lo / FPR_hi) from
# Clopper-Pearson intervals is bounded by the canary count alone, so there is a maximum value
# the audit can report even against a release that is 100% verbatim training data.
AUDIT_CEILING_BY_CANARIES = {
    10: 0.81,
    25: 1.84,
    50: 2.57,
    100: 3.28,
    200: 3.98,
    400: 4.68,
    800: 5.38,
}

# Smallest canary count that reliably detected each known leak fraction.
AUDIT_DETECTION_FLOOR = {1.0: 10, 0.25: 400, 0.05: None, 0.01: None}


def audit_ceiling(num_canaries: int) -> float:
    """Largest epsilon the auditor could report at this canary count.

    Interpolated between measured points; extrapolated conservatively past the ends. A
    reported `eps_audited` at or near this value means the instrument is saturated, not that
    the mechanism leaks exactly that much.
    """
    points = sorted(AUDIT_CEILING_BY_CANARIES.items())
    if num_canaries <= points[0][0]:
        return points[0][1] * num_canaries / points[0][0]
    if num_canaries >= points[-1][0]:
        return points[-1][1]
    # Deliberately unequal lengths — this is a pairwise sliding window over `points`, so
    # strict=True would raise on every call.
    for (m0, c0), (m1, c1) in zip(points, points[1:], strict=False):
        if m0 <= num_canaries <= m1:
            t = (num_canaries - m0) / (m1 - m0)
            return round(c0 + t * (c1 - c0), 3)
    return points[-1][1]


def _audit_payload(audit, num_canaries: int) -> dict:
    """Normalises either auditor's result into one shape the console can render.

    The two estimators expose genuinely different quantities — the paired auditor has TPR and
    FPR with Clopper-Pearson intervals, the one-run construction has a guess count and a
    binomial tail — so the union is reported rather than forcing one into the other's shape.
    What both MUST carry is the ceiling: a reported epsilon of 0 without the maximum the
    instrument could have certified reads as "no leakage" when it means "below resolution".
    """
    common = {
        "audited_eps": float(audit.audited_eps),
        "p_value": float(audit.p_value),
    }

    if hasattr(audit, "guesses"):  # one-run (Steinke)
        # This ceiling is exact rather than interpolated: it is a closed form in the number
        # of guesses actually made.
        return {
            **common,
            "auditor": "one_run",
            "ceiling": float(audit.ceiling),
            "saturated": bool(audit.saturated),
            "correct": int(audit.correct),
            "guesses": int(audit.guesses),
            "accuracy": float(audit.accuracy),
            "tpr": float(audit.accuracy),
            "fpr": 0.5,
            "tpr_lower": float(audit.accuracy),
            "fpr_upper": 0.5,
            "num_members": int(audit.num_included),
            "num_holdout": int(audit.num_canaries - audit.num_included),
            "num_canaries": int(audit.num_canaries),
            "num_included": int(audit.num_included),
            "detects_leak_above": next(
                (
                    f
                    for f, m in sorted(AUDIT_DETECTION_FLOOR.items())
                    if m is not None and m <= num_canaries
                ),
                None,
            ),
            "range_note": (
                f"With {audit.guesses} guesses this audit could certify at most "
                f"eps={audit.ceiling:.2f}, even against a release that is 100% verbatim "
                "training data. A value of 0 means 'below this instrument's resolution', "
                "not 'no leakage'. Certifying an epsilon costs roughly ln(1/alpha)*e^eps "
                "canaries. See results/AUDITOR_COMPARISON.md."
            ),
        }

    # paired Clopper-Pearson
    return {
        **common,
        "auditor": "paired",
        "tpr": float(audit.tpr),
        "fpr": float(audit.fpr),
        "tpr_lower": float(audit.tpr_lower),
        "fpr_upper": float(audit.fpr_upper),
        "num_members": int(audit.num_members),
        "num_holdout": int(audit.num_holdout),
        "confidence": float(audit.confidence),
        "ceiling": audit_ceiling(num_canaries),
        "detects_leak_above": next(
            (
                f
                for f, m in sorted(AUDIT_DETECTION_FLOOR.items())
                if m is not None and m <= num_canaries
            ),
            None,
        ),
        "range_note": (
            f"At {num_canaries} canaries this auditor cannot report an epsilon above "
            f"~{audit_ceiling(num_canaries):.2f}, even against a release that is 100% "
            "verbatim training data. A value of 0 means 'below this instrument's "
            "resolution', not 'no leakage'. See results/DETECTION_FLOOR.md."
        ),
    }


# DOMIAS and attribute inference were listed here as unimplemented long after both shipped,
# and `run_cell` was running DOMIAS the whole time. Only LiRA is genuinely absent, and that is
# a decision rather than a gap.
NOT_IMPLEMENTED_ATTACKS = [
    {
        "name": "LiRA",
        "reason": (
            "Deliberately not implemented: ~21h of compute for a likely wide-CI null, and "
            "naming a cheaper attack 'LiRA' would misreport what ran (audit finding F7)."
        ),
    },
]
