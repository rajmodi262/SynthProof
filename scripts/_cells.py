"""Seed aggregation shared by every report generator.

Two result formats exist: `run_h1` grids store one cell per (mechanism, eps) already averaged over
5 seeds (`n = 5`), while the full-dataset per-cell runner stores one cell per SEED (`n = 1`, 100
cells). Report code that did `by[mech][eps] = c` silently kept only the LAST seed of the latter --
it reported Adult at 92% of TRTR where the 5-seed mean is 84%. Every generator now reads cells
through `seed_mean_cells`, which makes the two formats equivalent.
"""

from typing import Dict, List, Tuple


def seed_mean_cells(cells: List[dict]) -> List[dict]:
    """One seed-weighted mean cell per (mechanism, eps); aggregated cells pass through unchanged.

    Every interval-shaped field ({"mean", ...}) is replaced by its seed-weighted mean, with `lo`
    / `hi` set to the min / max seed mean (a range, not a confidence interval) and `n` the seed
    count. NaN seeds are skipped, not averaged in.
    """
    groups: Dict[Tuple[str, float], List[dict]] = {}
    for c in cells:
        groups.setdefault((c["mechanism"], float(c["target_eps"])), []).append(c)
    out = []
    for cs in groups.values():
        if len(cs) == 1:
            out.append(cs[0])
            continue
        merged = dict(cs[0])
        merged["seeds"] = sum(int(c.get("seeds") or 1) for c in cs)
        for key, val in cs[0].items():
            if not (isinstance(val, dict) and "mean" in val):
                continue
            vals = [
                (c[key]["mean"], int(c[key].get("n") or 1))
                for c in cs
                if isinstance(c.get(key), dict)
                and isinstance(c[key].get("mean"), (int, float))
                and c[key]["mean"] == c[key]["mean"]
            ]
            if not vals:
                continue
            n = sum(w for _, w in vals)
            mean = sum(x * w for x, w in vals) / n
            sd = (sum(w * (x - mean) ** 2 for x, w in vals) / max(1, n - 1)) ** 0.5
            merged[key] = {
                "mean": mean,
                "lo": min(x for x, _ in vals),
                "hi": max(x for x, _ in vals),
                "sd": sd,
                "n": n,
            }
        out.append(merged)
    return out
