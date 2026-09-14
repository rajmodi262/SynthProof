"""The public size of a release.

Under the add/remove-one-record relation this project's accountant composes under
(`docs/thesis/ch03-threat-model.md`), two neighbouring tables differ in length by one, so the
exact row count is itself private. It used to leave the curator three ways: the signed sheet's
`num_rows`, the synthetic table's length, and the pre-run refusal check, which compared the exact
count with a threshold. See `docs/design/PUBLIC_RELEASE_BOUNDARY.md` (D2).

Every size that reaches an artefact now comes from one of three sources, recorded in the sheet as
`release_rows_source` so a reader can see which applied:

  protocol  -- fixed before any data is read: the research grids' subsample size and split;
  declared  -- stated by the operator: API `rows`, CLI `--release-rows`;
  dp_count  -- one discrete-Laplace counting query, charged.

The exact count is never used for any of them.
"""

from dataclasses import dataclass

import numpy as np

from synthproof.accounting.noise import sample_discrete_laplace

RELEASE_ROWS_SOURCES = ("protocol", "declared", "dp_count")

# Share of the smallest requested epsilon spent on the noisy count. At eps = 1 the count's noise
# scale is 50 rows: coarse, but a release size needs no more, and the other 98% goes to the data.
DP_COUNT_FRAC = 0.02

# Keeps the count's noise stream apart from every other stream derived from the same seed. Two
# mechanisms drawing identical noise are not independent, and composition assumes they are.
_COUNT_STREAM = 0x5EED_C0DE


@dataclass(frozen=True)
class ReleaseSize:
    """How many rows a release has, and why that number is public."""

    rows: int
    source: str
    # Epsilon spent to obtain `rows`. Non-zero exactly when the size was a charged count.
    eps: float = 0.0

    def __post_init__(self):
        if self.source not in RELEASE_ROWS_SOURCES:
            raise ValueError(
                f"Unknown release size source {self.source!r}. Use one of {RELEASE_ROWS_SOURCES}."
            )
        if self.rows < 1:
            raise ValueError(f"A release needs at least one row, got {self.rows}.")
        if (self.source == "dp_count") != (self.eps > 0):
            raise ValueError(
                "A charged count must record the epsilon it cost, and nothing else may: "
                f"source={self.source!r}, eps={self.eps}."
            )


def declared(rows: int) -> ReleaseSize:
    """A size the operator states before the data is read."""
    if int(rows) != rows or rows < 1:
        raise ValueError(f"A declared release size must be a positive integer, got {rows!r}.")
    return ReleaseSize(rows=int(rows), source="declared")


def dp_count(exact_rows: int, eps: float, seed: int) -> ReleaseSize:
    """One counting query under add/remove-one: sensitivity 1, noise DLap(1 / eps).

    The discrete Laplace mechanism with scale b = 1 / eps on a sensitivity-1 query is eps-DP:
    moving the count by one changes the probability of any output by at most e^(1/b). Flooring
    at 1 is post-processing. The result is pure eps-DP, so it adds to a release's (eps, delta)
    by basic composition, which is how `FrontierEngine.run_sweep` charges it.

    `seed` must be the curator's secret run seed, never a published one: a replayable noise draw
    makes this count exact for anyone holding the seed.
    """
    if eps <= 0:
        raise ValueError(f"The count needs a positive epsilon, got {eps}.")
    stream = int(np.random.SeedSequence([int(seed), _COUNT_STREAM]).generate_state(1)[0])
    noisy = int(exact_rows) + int(sample_discrete_laplace(1.0 / eps, size=1, seed=stream)[0])
    return ReleaseSize(rows=max(1, noisy), source="dp_count", eps=float(eps))
