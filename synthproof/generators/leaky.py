"""Deliberately non-private generators, used as POSITIVE CONTROLS for the auditor.

Every measuring instrument needs a known standard. Without one, "our audit found no leakage"
is indistinguishable from "our audit does not work" — and this project's first self-audit
found exactly that failure: an auditor that returned 0.00 in every cell for three structural
reasons, which nobody noticed because 0.00 was also the expected answer.

`LeakyGenerator` copies a controlled fraction of its training rows verbatim into the output.
That gives leakage which is:

  * **known** — we chose it,
  * **tunable** — `leak_fraction` moves it continuously from "none" to "the training set",
  * **monotone** — more leakage must be easier to detect.

An auditor that cannot recover a signal from this has no business reporting a null on a real
mechanism. Sweeping `leak_fraction` against canary count is what produces the detection floor
in `scripts/run_detection_floor.py`.

> [!WARNING]
> **These classes provide NO privacy whatsoever and must never be used to release data.**
> They are not registered in `frontier.experiment.MECHANISMS`, they charge no budget, and
> they raise if anyone asks them for an epsilon. The name is deliberately alarming.
"""

from typing import Optional

import numpy as np
import pandas as pd

from synthproof.accounting.accountant import Accountant
from synthproof.data.dataset import TabularDataset
from synthproof.data.profiler import DomainProfile
from synthproof.generators.base import BaseGenerator


class NotPrivateError(RuntimeError):
    """Raised when a control generator is asked to behave as if it were private."""


class LeakyGenerator(BaseGenerator):
    """Copies `leak_fraction` of the training rows verbatim; shuffles the rest.

    At `leak_fraction=1.0` the "synthetic" table IS the training table — the worst possible
    release, and the auditor's easiest case. At `0.0` every column is independently permuted
    across rows, which preserves each marginal exactly while destroying every joint
    relationship and every individual record. That lower end is the interesting control: the
    marginals still look perfect, so a fidelity metric is satisfied, and yet no row
    corresponds to a real person. A privacy metric that confuses the two would pass it.
    """

    def __init__(self, seed: int = 42, leak_fraction: float = 1.0):
        super().__init__(seed=seed)
        if not (0.0 <= leak_fraction <= 1.0):
            raise ValueError(f"leak_fraction must be in [0, 1], got {leak_fraction}")
        self.leak_fraction = leak_fraction
        self._train: Optional[pd.DataFrame] = None

    def fit(self, dataset: TabularDataset, profile: DomainProfile,
            accountant: Accountant, target_eps: float) -> None:
        """Memorises the training table. Charges NOTHING, because it applies no mechanism.

        Charging here would be worse than not charging: the accountant would report a finite
        epsilon for a release that satisfies no differential privacy guarantee at all. The
        project's standing rule is that a mechanism which is charged must be applied; the
        converse holds too.
        """
        self._train = dataset.df.copy()
        self.columns = dataset.columns
        self.numerical_cols = dataset.numerical_cols
        self.categorical_cols = dataset.categorical_cols
        self.is_fitted = True

    def generate(self, num_samples: int) -> pd.DataFrame:
        if not self.is_fitted or self._train is None:
            raise RuntimeError("Generator must be fitted before calling generate().")

        rng = np.random.default_rng(self.seed)
        n_leak = int(round(num_samples * self.leak_fraction))
        n_shuffle = num_samples - n_leak
        parts = []

        if n_leak > 0:
            idx = rng.choice(len(self._train), size=n_leak,
                             replace=n_leak > len(self._train))
            parts.append(self._train.iloc[idx].reset_index(drop=True))

        if n_shuffle > 0:
            # Independently permute each column. Marginals are preserved exactly; the joint
            # distribution and every real record are destroyed.
            base = self._train.sample(n=n_shuffle, replace=True,
                                      random_state=self.seed).reset_index(drop=True)
            shuffled = {c: rng.permutation(base[c].to_numpy()) for c in base.columns}
            parts.append(pd.DataFrame(shuffled))

        out = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(
            columns=self.columns)
        # Shuffle rows so leaked records are not all at the top, which would let a naive
        # attack succeed on position alone.
        return out.sample(frac=1.0, random_state=self.seed).reset_index(drop=True)

    @property
    def epsilon(self) -> float:
        raise NotPrivateError(
            "LeakyGenerator provides no privacy guarantee. It exists to validate the "
            "auditor against a known standard, and has no epsilon to report."
        )


# Registry of control mechanisms, kept SEPARATE from `frontier.experiment.MECHANISMS` so a
# non-private generator can never be selected by the CLI, the API or a real sweep.
CONTROLS = {
    "leaky_full": lambda seed=42: LeakyGenerator(seed=seed, leak_fraction=1.0),
    "leaky_half": lambda seed=42: LeakyGenerator(seed=seed, leak_fraction=0.5),
    "leaky_tenth": lambda seed=42: LeakyGenerator(seed=seed, leak_fraction=0.1),
    "shuffled": lambda seed=42: LeakyGenerator(seed=seed, leak_fraction=0.0),
}
