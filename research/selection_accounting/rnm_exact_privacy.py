"""Exact privacy of AIM's report-noisy-max selection, versus what the accountant charges.

aim.py selects with argmax(scores + discrete_Laplace(scale=b)) and charges each round as
LaplaceDpEvent(noise_multiplier = b / 2), i.e. a Laplace MECHANISM with sensitivity 2.

This computes, exactly (no sampling), the output distribution of that selection for
neighbouring score vectors whose per-coordinate shift is at most DELTA_TRUE, and reports:
  * the pure-DP epsilon actually realised by one round  -> compare with the charged 2 / b
  * Renyi divergences at the accountant's orders       -> compare with LaplaceDpEvent's RDP
Worst cases searched: winner's score moves by -DELTA_TRUE while every other candidate moves by
+DELTA_TRUE (the non-monotone pattern), over a grid of starting gaps.

Tie-breaking follows np.argmax: the lowest index wins a tie.
"""

import json
import sys

import numpy as np
from dp_accounting import dp_event
from dp_accounting.rdp import rdp_privacy_accountant

sys.path.insert(0, ".")
from synthproof.accounting.calibration import calibrate_noise_scale  # noqa: E402

ORDERS = [1.25, 1.5, 2, 3, 4, 6, 8, 12, 16, 32, 64]


def dlaplace_pmf(b, L):
    x = np.arange(-L, L + 1)
    w = np.exp(-np.abs(x) / b)
    return x, w / w.sum()


def argmax_dist(s, b):
    """Exact P(argmax(s + X) = i), X_j iid discrete Laplace(b), ties -> lowest index."""
    L = int(np.ceil(b * 40)) + int(np.ceil(np.ptp(s))) + 5
    x, p = dlaplace_pmf(b, L)
    cdf = np.cumsum(p)
    k = len(s)
    out = np.zeros(k)
    for i in range(k):
        # value of i's noisy score for each noise draw
        vi = s[i] + x
        prob = p.copy()
        for j in range(k):
            if j == i:
                continue
            # j must be strictly below (j < i index: strictly below; j > i: below or equal)
            thr = vi - s[j]  # need x_j < thr (strict) or <= thr
            if j < i:
                idx = np.searchsorted(x, thr, side="left") - 1  # x_j < thr
            else:
                idx = np.searchsorted(x, thr, side="right") - 1  # x_j <= thr
            cj = np.where(idx >= 0, cdf[np.clip(idx, 0, len(x) - 1)], 0.0)
            prob = prob * cj
        out[i] = prob.sum()
    return out / out.sum()


def renyi(P, Q, a):
    m = (P > 0) & (Q > 0)
    return float(np.log(np.sum(P[m] ** a * Q[m] ** (1 - a))) / (a - 1))


def laplace_event_rdp(mult):
    acct = rdp_privacy_accountant.RdpAccountant(ORDERS)
    acct.compose(dp_event.LaplaceDpEvent(mult), 1)
    rdp = getattr(acct, "_rdp", None)
    return [float(v) for v in rdp] if rdp is not None else None


def worst_case(b, k, delta_true):
    best = {"eps": 0.0}
    rdp_worst = np.zeros(len(ORDERS))
    for gap in np.linspace(-6 * b, 6 * b, 49):
        s = np.zeros(k)
        s[0] = gap
        sp = s + delta_true
        sp[0] = s[0] - delta_true
        for P, Q in ((argmax_dist(s, b), argmax_dist(sp, b)), (argmax_dist(sp, b), argmax_dist(s, b))):
            eps = float(np.max(np.abs(np.log(P) - np.log(Q))))
            if eps > best["eps"]:
                best = {"eps": eps, "gap": float(gap)}
            rdp_worst = np.maximum(rdp_worst, [renyi(P, Q, a) for a in ORDERS])
    return best, rdp_worst.tolist()


if __name__ == "__main__":
    rows = []
    for target_eps in (1.0, 8.0):
        rounds = 6
        sel_eps = 0.25 * target_eps  # aim.py DEFAULT_SELECTION_FRAC
        b = calibrate_noise_scale(target_eps=sel_eps, target_delta=1e-5, name="laplace", sensitivity=2.0, steps=rounds)
        charged_mult = b / 2.0
        charged_rdp = laplace_event_rdp(charged_mult)
        for k in (2, 3, 6):
            for delta_true in (1.0, 2.0):
                best, rdp = worst_case(b, k, delta_true)
                row = {
                    "target_eps": target_eps, "selection_eps_total": sel_eps, "rounds": rounds,
                    "laplace_scale_b": round(b, 4), "charged_pure_eps_per_round": round(2.0 / b, 4),
                    "k_candidates": k, "delta_true": delta_true,
                    "realised_pure_eps_per_round": round(best["eps"], 4), "worst_gap": best.get("gap"),
                    "ratio_realised_over_charged": round(best["eps"] / (2.0 / b), 4),
                    "rdp_orders": ORDERS, "rdp_realised": [round(v, 5) for v in rdp],
                    "rdp_charged_laplace_event": [round(v, 5) for v in charged_rdp] if charged_rdp else None,
                    "rdp_exceeds_charged_at_any_order": bool(charged_rdp and any(r > c + 1e-9 for r, c in zip(rdp, charged_rdp))),
                }
                rows.append(row)
                print(json.dumps({k2: row[k2] for k2 in ("target_eps", "k_candidates", "delta_true", "laplace_scale_b", "charged_pure_eps_per_round", "realised_pure_eps_per_round", "ratio_realised_over_charged", "rdp_exceeds_charged_at_any_order")}), flush=True)
    json.dump(rows, open(sys.argv[1] if len(sys.argv) > 1 else "rnm_exact_privacy.json", "w"), indent=2)
