"""Pieces shared by every imputation arm."""

import numpy as np

MISSING_CATEGORY_LABEL = "__MISSING__"


def bounded_shifted_sum(values: np.ndarray, lo: float, hi: float) -> float:
    """Sum of (clip(v, lo, hi) - lo): each record contributes [0, hi - lo].

    Its add/remove-one sensitivity is therefore exactly hi - lo, the sensitivity the DP sum in
    arm A3 is charged at. A raw sum of clipped values has sensitivity max(|lo|, |hi|) instead.
    """
    return float(np.sum(np.clip(np.asarray(values, dtype=float), lo, hi) - lo))
