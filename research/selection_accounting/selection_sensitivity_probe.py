"""Probe: how far does one record move AIM's selection scores, holding released noise fixed?

The DP analysis of a selection step treats the measurements already released as FIXED outputs.
So the right sensitivity is: with the noisy measurement vectors held constant, how much can adding
or removing one record change each candidate's score?

AIM's score (synthproof/generators/aim.py) is L1(true_marginal - model_marginal), where the model
is fitted to the noisy measurements with `known_total=n`. Two data paths:
  * true_marginal   -- changes by exactly 1 in one cell  -> contributes at most 1
  * model_marginal  -- changes only through known_total=n -> should contribute 0 if the total is
                       estimated from the noisy measurements (private-pgm's default)

Reports, per configuration, the max |delta score| over candidates and trials, and whether the
shifts are ever of mixed sign across candidates (non-monotone).
"""

import itertools
import json
import sys

import numpy as np

sys.path.insert(0, ".")
from synthproof.generators import aim as aimmod  # noqa: E402

Domain, Dataset, LinearMeasurement, estimation, _hms = aimmod._require_mbi()

ITERS = 150  # what aim.py uses inside the selection rounds


def marginal(data, cl):
    return np.asarray(data.project(cl).datavector(), dtype=float)


def fit(domain, meas, total):
    return estimation.MirrorDescent().estimate(domain, meas, known_total=total, iters=ITERS)


def scores(data, model, cands):
    return np.array([np.abs(marginal(data, cl) - np.asarray(model.project(cl).datavector(), dtype=float)).sum() for cl in cands])


def run(n, shapes, sigma, trials, seed):
    rng = np.random.default_rng(seed)
    cols = tuple(f"c{i}" for i in range(len(shapes)))
    domain = Domain(cols, tuple(shapes))
    cands = list(itertools.combinations(cols, 2))
    out = {"n": n, "shapes": list(shapes), "sigma": sigma, "trials": trials, "variants": {}}
    for variant in ("known_total=n (current code)", "known_total=None (private-pgm default)"):
        max_abs, mixed, deltas = 0.0, 0, []
        for _ in range(trials):
            import pandas as pd

            base = pd.DataFrame(rng.integers(0, np.array(shapes), size=(n, len(shapes))), columns=cols)
            extra = pd.DataFrame(rng.integers(0, np.array(shapes), size=(1, len(shapes))), columns=cols)
            nb = pd.concat([base, extra], ignore_index=True)  # add-one neighbour
            D, Dp = Dataset(base, domain), Dataset(nb, domain)
            # released 1-way measurements: computed ONCE on D, held fixed for both worlds
            meas = []
            for c in cols:
                y = marginal(D, (c,))
                meas.append(LinearMeasurement(y + rng.normal(0, sigma, y.size), (c,), stddev=sigma))
            if variant.startswith("known_total=n"):
                mD, mDp = fit(domain, meas, float(n)), fit(domain, meas, float(n + 1))
            else:
                mD = fit(domain, meas, None)
                mDp = mD  # same released inputs -> same model
            d = scores(Dp, mDp, cands) - scores(D, mD, cands)
            deltas.append(d.tolist())
            max_abs = max(max_abs, float(np.max(np.abs(d))))
            if (d > 1e-9).any() and (d < -1e-9).any():
                mixed += 1
        out["variants"][variant] = {
            "max_abs_delta_score": round(max_abs, 6),
            "trials_with_mixed_sign_shifts": mixed,
            "p99_abs_delta": round(float(np.percentile(np.abs(np.array(deltas)), 99)), 6),
        }
    return out


if __name__ == "__main__":
    results = []
    for n, shapes, sigma in [(10, (2, 2, 2, 2), 1.0), (50, (2, 3, 2, 3), 2.0), (200, (3, 3, 3, 2), 4.0)]:
        r = run(n, shapes, sigma, trials=40, seed=7 + n)
        results.append(r)
        print(json.dumps(r), flush=True)
    json.dump(results, open(sys.argv[1] if len(sys.argv) > 1 else "selection_sensitivity_probe.json", "w"), indent=2)
