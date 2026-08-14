"""Measures the canary auditor's detection floor.

THE PROBLEM THIS SOLVES. Every experiment this project has run reports
``eps_audited = 0.000``. That is either "the mechanisms leak very little" or "this auditor
cannot see anything at this canary count", and nothing in the result distinguishes them. A
proved-versus-audited gap of "7.36 versus 0.00" is therefore not a finding about differential
privacy — it is an instrument reading its own noise floor, with the floor unmeasured.

THE MEASUREMENT. Run the auditor against `LeakyGenerator`, whose leakage is known and tunable
by construction, over a grid of canary counts `m` and leak fractions `f`. For each cell,
record whether the audit fires (`audited_eps > 0` and `p < alpha`). The **detection floor** at
a given leak fraction is the smallest `m` at which it fires reliably across seeds.

WHAT THAT BUYS. Afterwards, ``eps_audited = 0 at m = 60`` stops being an absence and becomes a
bounded statement: *leakage, if present, is below what this instrument resolves at 60
canaries*. That is a scientific claim. It is also the honest way to report a null.

The floor is a property of the auditor, not of any DP mechanism, which is why this module
takes a generator factory rather than a mechanism name.
"""

from dataclasses import asdict, dataclass, field
from typing import Callable, Dict, List, Optional, Sequence

import numpy as np

from synthproof.audit.canary import CanaryAuditor
from synthproof.data.dataset import TabularDataset

DEFAULT_CANARY_COUNTS: Sequence[int] = (10, 25, 50, 100, 200, 400)
DEFAULT_LEAK_FRACTIONS: Sequence[float] = (0.0, 0.01, 0.05, 0.25, 1.0)
DEFAULT_ALPHA = 0.05


@dataclass
class FloorCell:
    """One (leak_fraction, num_canaries) cell, aggregated across seeds."""

    leak_fraction: float
    num_canaries: int
    seeds: int
    detection_rate: float          # fraction of seeds where the audit fired
    mean_audited_eps: float
    max_audited_eps: float
    mean_p_value: float
    mean_tpr: float
    mean_fpr: float

    @property
    def detected(self) -> bool:
        """Fired on a strict majority of seeds — one lucky seed is not detection."""
        return self.detection_rate > 0.5


@dataclass
class FloorResult:
    """The full sweep, plus the floor read off it."""

    cells: List[FloorCell] = field(default_factory=list)
    alpha: float = DEFAULT_ALPHA
    dataset: str = ""
    rows: int = 0

    def floor_for(self, leak_fraction: float) -> Optional[int]:
        """Smallest canary count that reliably detects this leak level, or None."""
        candidates = sorted(
            (c for c in self.cells
             if c.leak_fraction == leak_fraction and c.detected),
            key=lambda c: c.num_canaries,
        )
        return candidates[0].num_canaries if candidates else None

    def floors(self) -> Dict[float, Optional[int]]:
        return {f: self.floor_for(f)
                for f in sorted({c.leak_fraction for c in self.cells})}

    def to_dict(self) -> dict:
        return {
            "dataset": self.dataset,
            "rows": self.rows,
            "alpha": self.alpha,
            "floors": {str(k): v for k, v in self.floors().items()},
            "cells": [asdict(c) for c in self.cells],
        }


def measure_detection_floor(
    dataset: TabularDataset,
    generator_factory: Callable[[float, int], object],
    canary_counts: Sequence[int] = DEFAULT_CANARY_COUNTS,
    leak_fractions: Sequence[float] = DEFAULT_LEAK_FRACTIONS,
    seeds: Sequence[int] = (0, 1, 2),
    alpha: float = DEFAULT_ALPHA,
    progress: Optional[Callable[[str], None]] = None,
) -> FloorResult:
    """Sweeps canary count against known leakage and reports where detection begins.

    Args:
        dataset: Table to plant canaries into.
        generator_factory: `(leak_fraction, seed) -> generator`. Must expose `fit` and
            `generate`; no privacy is required or expected of it.
        canary_counts: Canary counts to try, ascending.
        leak_fractions: Known leakage levels, ascending.
        seeds: Repetitions per cell. Detection is judged on a majority across these, so a
            single lucky seed cannot manufacture a floor.
        alpha: Significance threshold for the audit's Fisher exact test.

    Returns:
        A `FloorResult`. Note that the audit is NOT charged to any accountant here — this
        measures the instrument, not a release.
    """
    result = FloorResult(alpha=alpha, dataset=dataset.name, rows=dataset.num_rows)

    for leak in leak_fractions:
        for m in canary_counts:
            fired, eps_vals, p_vals, tprs, fprs = 0, [], [], [], []

            for seed in seeds:
                if progress:
                    progress(f"  leak={leak:<5} m={m:<4} seed={seed}")

                auditor = CanaryAuditor(num_canaries=m, seed=seed)
                aug_ds, canaries = auditor.plant_canaries(dataset)

                gen = generator_factory(leak, seed)
                # Controls take no budget, so the accountant and profile are irrelevant.
                gen.fit(aug_ds, None, None, 0.0)
                synth = gen.generate(num_samples=aug_ds.num_rows)

                res = auditor.audit(synth, canaries)
                if res.audited_eps > 0.0 and res.p_value < alpha:
                    fired += 1
                eps_vals.append(res.audited_eps)
                p_vals.append(res.p_value)
                tprs.append(res.tpr)
                fprs.append(res.fpr)

            result.cells.append(FloorCell(
                leak_fraction=float(leak),
                num_canaries=int(m),
                seeds=len(seeds),
                detection_rate=fired / max(1, len(seeds)),
                mean_audited_eps=float(np.mean(eps_vals)),
                max_audited_eps=float(np.max(eps_vals)),
                mean_p_value=float(np.mean(p_vals)),
                mean_tpr=float(np.mean(tprs)),
                mean_fpr=float(np.mean(fprs)),
            ))

    return result


def format_floor_table(result: FloorResult) -> str:
    """Renders the sweep as a detection-rate grid, for a terminal or a thesis figure."""
    counts = sorted({c.num_canaries for c in result.cells})
    fractions = sorted({c.leak_fraction for c in result.cells})
    by_key = {(c.leak_fraction, c.num_canaries): c for c in result.cells}

    lines = ["detection rate (fraction of seeds where the audit fired, p < "
             f"{result.alpha})", ""]
    lines.append("leak\\m   " + "".join(f"{m:>8}" for m in counts))
    for f in fractions:
        row = f"{f:<8.2f}" + "".join(
            f"{by_key[(f, m)].detection_rate:>8.2f}" if (f, m) in by_key else f"{'-':>8}"
            for m in counts
        )
        lines.append(row)

    lines.append("")
    lines.append("detection floor (smallest m that fires on a majority of seeds)")
    for f, floor in result.floors().items():
        lines.append(f"  leak {f:<6.2f} -> {floor if floor is not None else 'not detected'}")
    return "\n".join(lines)
