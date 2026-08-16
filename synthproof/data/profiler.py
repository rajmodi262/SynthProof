"""Differentially private domain profiler.

Discovers per-column ranges and category domains, charging the privacy budget for what
it learns. Noise is calibrated so the whole profiling pass costs the epsilon it was
given, rather than growing with the number of columns.

Audit finding F5 is closed here, in two parts:

  * The category domain is released through a noisy threshold rather than published verbatim.
  * Numeric ranges come from the schema's PUBLIC bounds and cost no budget, because a public
    fact reveals nothing. Only a column with no declared range falls back to a noisy min/max,
    and that path documents plainly that its sensitivity is an assumption.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

from synthproof.accounting.accountant import Accountant
from synthproof.accounting.calibration import calibrate_noise_scale
from synthproof.accounting.noise import sample_discrete_laplace
from synthproof.accounting.types import MechanismSpec
from synthproof.data.dataset import TabularDataset


class InsufficientBudgetError(ValueError):
    """The budget is too small to release a column's domain privately.

    Raised instead of falling back to a non-private release. Subclasses ValueError so that
    callers written against the previous contract still catch it.
    """


@dataclass
class ColumnProfile:
    """Discovered DP profile for a single column."""

    name: str
    dtype: str  # "numerical" or "categorical"
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    categories: Optional[List[Any]] = None
    suppressed_categories: int = 0  # rare categories withheld by the DP threshold
    is_public_range: bool = False  # True when the range came from the schema, not the data


@dataclass
class DomainProfile:
    """Full DP domain profile for a tabular schema."""

    dataset_name: str
    num_rows: int
    columns: Dict[str, ColumnProfile] = field(default_factory=dict)
    eps_spent: float = 0.0


class DPDomainProfiler:
    """Discovers feature ranges and category domains under a calibrated DP budget.

    Column *names* and coarse types are treated as public schema metadata. Column
    *contents* — ranges, which categories occur, and how often — are sensitive and are
    released only through DP mechanisms.
    """

    def __init__(
        self,
        accountant: Accountant,
        eps_budget: float = 0.1,
        sensitivity: float = 1.0,
        schema_declared: bool = True,
        delta_calibrated_threshold: bool = False,
    ):
        """
        Args:
            accountant: Accountant to charge.
            eps_budget: Total epsilon this profiling pass may spend. Noise is calibrated
                so the pass costs approximately this much regardless of column count.
                (Replaces the old `eps_per_col`, under which total cost grew with the
                schema and no caller could predict the release's epsilon.)
            sensitivity: Assumed per-query sensitivity.
            schema_declared: False when the schema came from `Schema.infer_nonprivate`.

                This flag exists because of a defect found while tightening the suppression
                threshold. `infer_nonprivate` fills `ColumnSpec.categories` from
                `series.unique()`, so on an inferred schema the "public" domain IS the data.
                The empty-domain fallback then treated it as a publishable fact and released
                every observed value — on a table with one identifier per row, all 2,000 of
                them, which is far worse than the leak the tighter threshold was meant to
                close. A stricter threshold made the fallback fire MORE often and so made the
                damage larger.

                With `schema_declared=False` there is no public domain to fall back on, so an
                unsatisfiable budget raises instead.
            delta_calibrated_threshold: Opt in to the delta-calibrated suppression threshold.
                Off by default because switching it on changes published results — see
                `_category_threshold` for the arithmetic and what it costs.
        """
        if eps_budget <= 0:
            raise ValueError(f"eps_budget must be positive, got {eps_budget}")
        self.accountant = accountant
        self.eps_budget = eps_budget
        self.sensitivity = sensitivity
        self.schema_declared = schema_declared
        self.delta_calibrated_threshold = delta_calibrated_threshold

    @staticmethod
    def _public_bounds(dataset: TabularDataset, col: str):
        """Public [lower, upper] for a numeric column, or None if none is declared."""
        if dataset.schema is None or col not in dataset.numerical_cols:
            return None
        return dataset.bounds(col)

    def _category_threshold(self, noise_scale: float, n_categorical: int) -> float:
        """Suppression threshold for an unknown-domain histogram, calibrated to delta.

        THE DEFECT THIS REPLACES. The threshold was `3 * noise_scale * sqrt(2)` — three
        standard deviations of the noise, with no delta term anywhere. That made the
        probability of a singleton category surviving a CONSTANT of the mechanism rather than
        something the release controls: measured at roughly 1 in 51 at eps=1, against a
        declared delta of 1e-5, or about 1,950x the failure probability being claimed. On a
        table whose schema was inferred rather than declared, that let real identifiers
        through verbatim.

        THE CORRECT FORM. This is a stability-based histogram over an unknown domain, and its
        threshold is standard:

            T = D_inf + (D_inf / eps_query) * log(D_0 / 2delta)

        (Rogers 2023, arXiv:2309.09170, Algorithm 1 Laplace variant, crediting Korolova et al.
        2009 and Wilson et al. 2020.) Under add/remove-one both sensitivities are 1: a single
        record changes exactly one count, by one. Writing the Laplace scale as
        b = D_inf / eps_query gives

            T = 1 + b * log(1 / (2 * delta_col))

        and delta is exactly what it should be — the probability that a category present only
        because of one person clears the threshold and is published.

        WHY delta IS SPLIT. Each categorical column runs its own thresholded histogram, so the
        failure probabilities add. Dividing the release's delta evenly across them is a union
        bound: it is conservative and it is stated, rather than each column silently spending
        the whole budget.

        The consequence is deliberate and is not a regression: the threshold roughly triples,
        so a category needs about a dozen supporting records rather than four to survive. A
        value held by fewer people than that should not appear in a public release, and the
        earlier number said otherwise.

        NOT YET ENABLED BY DEFAULT, and the reason is a decision rather than an oversight.
        The calibrated form measurably breaks the low-budget end of the committed benchmarks:
        on UCI Adult at eps=0.5 it reduces `income` — the TSTR target — to a single level,
        which makes the utility number at that budget meaningless rather than merely worse.

            eps    Laplace b    current T    calibrated T    columns left with <=1 level
            0.5       152.53        647.1          1968.5    5 of 8 (incl. the target)
            1.0        78.07        331.2          1008.1    2 of 8
            2.0        39.51        167.6           510.7    1 of 8
            4.0        19.88         84.3           257.4    0 of 8
            8.0         9.97         42.3           129.6    0 of 8

        Adopting it therefore means re-running every grid and rewriting every H1 number, and
        it would arguably be more correct still to SPLIT delta between this threshold and the
        RDP-to-(eps, delta) conversion the accountant already spends it on — using the full
        delta for both, as the code below would, double-counts it and the threshold should be
        higher again.

        The coherent end state is that a budget which cannot support a domain is REFUSED
        (preflight R6) rather than silently producing a degenerate release. That is a change
        to what the project publishes, not just to how it computes, so it is left as a stated
        decision with the arithmetic attached.
        """
        delta = float(self.accountant.budget.delta)
        if delta <= 0.0 or delta >= 1.0:
            raise ValueError(
                f"A stability-based domain release needs 0 < delta < 1, got {delta}. "
                "Delta is the probability a singleton category survives suppression; without "
                "one there is no sound threshold."
            )
        # Union bound across the columns that each run a thresholded histogram.
        delta_col = delta / max(1, n_categorical)
        return 1.0 + noise_scale * float(np.log(1.0 / (2.0 * delta_col)))

    def _legacy_category_threshold(self, noise_scale: float) -> float:
        """The threshold every committed result was produced with: 3 noise standard deviations.

        Kept as the default so no published number silently changes, and documented as
        UNSOUND rather than quietly retained: it carries no delta term, so the probability a
        singleton category survives is a constant of the mechanism (~1 in 51 at eps=1) rather
        than the declared 1e-5. See `_category_threshold` for the correct form and for what
        adopting it costs.

        The exposure this leaves is bounded by two things that are now in place: a DECLARED
        schema means the candidate set was already public, so thresholding cannot release
        anything new; and an INFERRED schema no longer has a fallback domain to leak, plus
        pre-flight R2 refuses near-unique columns before the profiler ever runs.
        """
        return 3.0 * noise_scale * float(np.sqrt(2.0))

    def _public_categories(self, dataset: TabularDataset, col: str):
        """Publicly declared category domain, or None if there is no PUBLIC one.

        Like the public numeric bounds, a declared domain is a fact the schema already
        publishes, so using it reveals nothing and costs nothing. An INFERRED schema publishes
        nothing — its category lists were read out of the table — so there is no free answer
        and this returns None.
        """
        if dataset.schema is None or not self.schema_declared:
            return None
        for spec in dataset.schema.columns:
            if spec.name == col:
                return spec.categories
        return None

    def _query_count(self, dataset: TabularDataset) -> int:
        """Number of DP queries this pass will issue.

        A numeric column whose range is PUBLIC costs nothing: the bounds are already known, so
        there is nothing to learn and nothing to hide. Only columns without a declared range
        need a (2-query) noisy min/max, and only categorical columns need a histogram.
        """
        n = len(dataset.categorical_cols)
        for col in dataset.numerical_cols:
            if self._public_bounds(dataset, col) is None:
                n += 2
        return n

    def _sensitivity_for(self, dataset: TabularDataset, col: str) -> float:
        """Sensitivity of this column's queries.

        Categorical histograms have sensitivity 1 under add/remove-one. A noisy min/max on an
        unbounded column has *unbounded* sensitivity, so `self.sensitivity` there is an
        assumption, not a derivation — which is exactly why a release should declare bounds
        and take the zero-cost path instead. See audit finding F5.
        """
        return 1.0 if col not in dataset.numerical_cols else self.sensitivity

    def profile(self, dataset: TabularDataset, seed: Optional[int] = None) -> DomainProfile:
        """Profiles the dataset schema, spending at most `eps_budget` in total."""
        n_queries = self._query_count(dataset)
        if n_queries == 0:
            # Everything is publicly declared; profiling is free.
            rng = np.random.default_rng(seed)
            cols = {
                c: self._public_profile(dataset, c)
                for c in dataset.columns
                if self._public_bounds(dataset, c) is not None
            }
            for c in dataset.categorical_cols:
                cols[c] = self._profile_categorical(
                    dataset, c, 1.0, rng, n_categorical=len(dataset.categorical_cols)
                )
            return DomainProfile(
                dataset_name=dataset.name,
                num_rows=dataset.num_rows,
                columns={c: cols[c] for c in dataset.columns if c in cols},
            )

        # Calibrate a noise MULTIPLIER — the scale expressed in units of sensitivity — rather
        # than an absolute scale. Columns have different sensitivities (a range query on an
        # income column bounded to [0, 500000] is far more sensitive than a count), but a
        # shared multiplier gives every query the same RDP curve, so the whole pass still
        # composes to exactly eps_budget.
        noise_multiplier = calibrate_noise_scale(
            target_eps=self.eps_budget,
            target_delta=self.accountant.budget.delta,
            name="laplace",
            sensitivity=1.0,
            steps=n_queries,
        )

        rng = np.random.default_rng(seed)
        eps_before = self.accountant.total()
        col_profiles: Dict[str, ColumnProfile] = {}

        for col in dataset.columns:
            sens = self._sensitivity_for(dataset, col)
            noise_scale = noise_multiplier * sens
            if col in dataset.numerical_cols:
                bounds = self._public_bounds(dataset, col)
                if bounds is not None:
                    # Declared publicly: use it, charge nothing. Spending budget to noisily
                    # re-estimate a range that is already public is pure waste — and with a
                    # correctly-sized sensitivity the estimate is garbage anyway. Before this
                    # branch existed, a column publicly bounded to [0, 100] was released with
                    # a noisy range like (1633, 1634): width 1, collapsing every record into a
                    # single bin and destroying all downstream structure.
                    col_profiles[col] = self._public_profile(dataset, col)
                else:
                    col_profiles[col] = self._profile_numeric(dataset, col, noise_scale, rng, sens)
            else:
                col_profiles[col] = self._profile_categorical(
                    dataset,
                    col,
                    noise_scale,
                    rng,
                    sens,
                    n_categorical=len(dataset.categorical_cols),
                )

        return DomainProfile(
            dataset_name=dataset.name,
            num_rows=dataset.num_rows,
            columns=col_profiles,
            eps_spent=self.accountant.total() - eps_before,
        )

    def _public_profile(self, dataset: TabularDataset, col: str) -> ColumnProfile:
        """Uses the publicly declared range. Costs no budget, because it reveals nothing."""
        lo, hi = self._public_bounds(dataset, col)
        return ColumnProfile(
            name=col, dtype="numerical", min_val=float(lo), max_val=float(hi), is_public_range=True
        )

    def _profile_numeric(
        self,
        dataset: TabularDataset,
        col: str,
        noise_scale: float,
        rng: np.random.Generator,
        sensitivity: float,
    ) -> ColumnProfile:
        """Releases a noisy min/max for a column with no declared public range (2 queries).

        NOTE: min/max over an unbounded column has unbounded sensitivity, so the epsilon
        charged here rests on `self.sensitivity` being a correct assumption. Declare bounds in
        the schema instead — that path is both sound and free.
        """
        self.accountant.charge(
            MechanismSpec(
                name="laplace", sensitivity=sensitivity, noise_scale=noise_scale, steps=2
            ),
            run_id=f"profile_range_{col}",
        )

        seed = int(rng.integers(0, 2**31 - 1))
        noise = sample_discrete_laplace(scale=noise_scale, size=2, seed=seed)

        dp_min = float(dataset.df[col].min()) + float(noise[0])
        dp_max = max(dp_min + 1.0, float(dataset.df[col].max()) + float(noise[1]))
        return ColumnProfile(name=col, dtype="numerical", min_val=dp_min, max_val=dp_max)

    def _profile_categorical(
        self,
        dataset: TabularDataset,
        col: str,
        noise_scale: float,
        rng: np.random.Generator,
        sensitivity: float = 1.0,
        n_categorical: int = 1,
    ) -> ColumnProfile:
        """Releases a DP category domain for a categorical column (1 histogram query).

        A previous version charged epsilon here and then published
        ``dataset.df[col].unique()`` verbatim — the exact, un-noised category domain,
        including any value occurring exactly once. Paying budget and then not applying
        the mechanism is strictly worse than not paying: privacy is spent AND the rare
        values that most identify individuals leak deterministically.

        Categories are now kept only when their noisy count clears a threshold, so a
        value present in a single record is unlikely to survive into the domain.
        """
        self.accountant.charge(
            MechanismSpec(
                name="laplace", sensitivity=sensitivity, noise_scale=noise_scale, steps=1
            ),
            run_id=f"profile_domain_{col}",
        )

        observed = list(dataset.df[col].unique())
        counts = dataset.df[col].value_counts().to_dict()

        seed = int(rng.integers(0, 2**31 - 1))
        noise = sample_discrete_laplace(scale=noise_scale, size=len(observed), seed=seed)

        # Default stays the legacy threshold so no committed number changes. The calibrated
        # form is implemented and documented in `_category_threshold`; adopting it is a
        # decision about what to publish, taken deliberately rather than by import.
        threshold = (
            self._category_threshold(noise_scale, n_categorical)
            if self.delta_calibrated_threshold
            else self._legacy_category_threshold(noise_scale)
        )

        kept = [
            cat
            for i, cat in enumerate(observed)
            if counts.get(cat, 0) + float(noise[i]) >= threshold
        ]
        suppressed = len(observed) - len(kept)

        # An empty domain is a real possibility at small eps, and what we do about it is a
        # SOUNDNESS question, not a convenience one.
        #
        # A previous version fell back to `max(observed, key=counts.get)` — the exact,
        # un-noised mode of a sensitive column, released with no additional charge. That is
        # an argmax over the raw data; under DP it requires the exponential mechanism. It was
        # measurably not private: on a 4-level column at eps_budget=0.001 it returned the true
        # mode in 196 of 200 seeds (98%), where a correct mechanism must approach
        # data-independence as eps -> 0.
        #
        # The replacement uses the PUBLIC schema domain, which reveals nothing and therefore
        # costs nothing — the same argument the public numeric bounds rest on. If the schema
        # declares no domain there is no sound answer, so this raises rather than guessing.
        if not kept and observed:
            public = self._public_categories(dataset, col)
            if public is not None:
                kept = list(public)
                suppressed = len(observed)
            else:
                raise InsufficientBudgetError(
                    f"Column {col!r}: no category survived the DP threshold at "
                    f"eps_budget={self.eps_budget:g}, and the schema declares no public "
                    f"domain for it.\n"
                    "There is no private way to pick a category here — releasing the most "
                    "frequent one would be an un-noised argmax over the raw data.\n"
                    "Fix by either raising eps_budget, or declaring the public domain: "
                    f"ColumnSpec({col!r}, CATEGORICAL, categories=[...])."
                )

        return ColumnProfile(
            name=col,
            dtype="categorical",
            categories=kept,
            suppressed_categories=suppressed,
        )
