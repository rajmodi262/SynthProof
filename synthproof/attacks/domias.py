"""DOMIAS — density-ratio membership inference for synthetic data.

After van Breugel, Sun, Qian & van der Schaar (2023), "Membership Inference Attacks against
Synthetic Data through Overfitting Detection".

WHY THIS ATTACK AND NOT LiRA. The synopsis promises four attacks; two existed and both were
weak. LiRA (Carlini et al. 2022) is the strongest known membership attack, but it needs 64+
shadow models — here, 64+ full synthesis runs — which is days of laptop compute for a result
that is noisy on tabular data. DOMIAS is designed specifically for the synthetic-data setting,
needs a single reference set, and costs one density estimate.

THE IDEA. A record is more likely to have been in the training set if the synthetic
distribution assigns it *more* mass than the general population does. So score each target by

    score(x) = p_synthetic(x) / p_reference(x)

Overfitting shows up as local excess density around training points. The ratio matters rather
than `p_synthetic(x)` alone: a record can be likely under the synthetic data simply because it
is a typical record, and dividing by a reference density removes that confound. Scoring by
`p_synthetic` alone recovers a *typicality* attack, which is what a naive nearest-neighbour
distance heuristic — the baseline already in this package — largely measures.

WHAT IT REQUIRES. A reference set drawn from the same population that the mechanism did NOT
see. The holdout split serves this purpose, and using it here does not leak: the attack is our
adversary, not part of the release.

REPORTING. AUC and TPR at low FPR, never accuracy at a median threshold. Carlini et al.'s
methodological argument applies directly — a privacy violation affecting a few individuals
with high confidence is far more serious than a marginal average-case improvement, and average
accuracy hides exactly that.
"""

from dataclasses import dataclass
from typing import List, Optional

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, roc_curve
from sklearn.neighbors import KernelDensity, NearestNeighbors
from sklearn.preprocessing import StandardScaler


@dataclass
class DomiasResult:
    """Density-ratio membership inference outcome. Every field is computed."""

    auc: float                  # threshold-free discrimination; 0.5 is chance
    advantage: float            # max_t (TPR(t) - FPR(t))
    tpr_at_1pct_fpr: float      # the low-FPR regime that actually matters
    tpr_at_01pct_fpr: float
    num_members: int
    num_nonmembers: int
    num_reference: int
    estimator: str
    bandwidth: float
    note: str = (
        "DOMIAS density-ratio attack (van Breugel et al. 2023). Scores by "
        "p_synthetic(x) / p_reference(x); the denominator removes the typicality confound "
        "that a raw-density or nearest-neighbour attack conflates with membership."
    )


class DOMIAS:
    """Membership inference by the synthetic-to-reference density ratio."""

    def __init__(self, seed: int = 42, bandwidth: Optional[float] = None,
                 max_records: Optional[int] = None, estimator: str = "knn",
                 k: int = 5):
        """
        Args:
            bandwidth: KDE bandwidth. None selects Scott's rule from the synthetic sample,
                which adapts to dimension and sample size rather than being tuned per
                dataset — tuning it against the target would be attacker knowledge we have
                no right to assume.
            max_records: Cap on records scored per split, for runtime.
            estimator: "knn" (default) or "kde". k-NN adapts its scale locally and can see
                memorised records; a fixed-bandwidth KDE cannot. See `_log_density_knn`.
            k: Neighbour count for the k-NN estimator. Small k is more sensitive to
                memorisation; large k is smoother and less variable.
        """
        if estimator not in ("knn", "kde"):
            raise ValueError(f"estimator must be 'knn' or 'kde', got {estimator!r}")
        self.seed = seed
        self.bandwidth = bandwidth
        self.max_records = max_records
        self.estimator = estimator
        self.k = k

    # ------------------------------------------------------------------ internals

    @staticmethod
    def _numeric_columns(*frames: pd.DataFrame) -> List[str]:
        """Numeric columns present in every frame."""
        shared = set(frames[0].columns)
        for f in frames[1:]:
            shared &= set(f.columns)
        return [c for c in frames[0].columns
                if c in shared and pd.api.types.is_numeric_dtype(frames[0][c])]

    def _scott_bandwidth(self, x: np.ndarray) -> float:
        """Scott's rule on standardised data: n^(-1/(d+4))."""
        n, d = x.shape
        if n < 2:
            return 1.0
        return float(max(1e-3, n ** (-1.0 / (d + 4))))

    def _log_density_kde(self, train: np.ndarray, query: np.ndarray,
                         bw: float) -> np.ndarray:
        kde = KernelDensity(kernel="gaussian", bandwidth=bw).fit(train)
        return kde.score_samples(query)

    def _log_density_knn(self, train: np.ndarray, query: np.ndarray,
                         k: int, leave_one_out: bool = False) -> np.ndarray:
        """k-nearest-neighbour log density, up to a constant that cancels in the ratio.

        WHY NOT KDE. A fixed-bandwidth KDE cannot see the signal this attack depends on.
        Measured on a release that reproduces its training data verbatim, Scott's-rule KDE
        gave AUC 0.558 while a plain nearest-neighbour distance heuristic gave 1.000 — the
        bandwidth (~0.35 in standardised units at n=800) smooths straight over the exact
        matches that ARE the leakage.

        The k-NN estimator adapts its scale locally: p(x) ~ k / (n * V_d * r_k(x)^d), so
        log p(x) = -d * log r_k(x) + const. As a record's distance to the release goes to
        zero its density goes to infinity, which is the correct behaviour for a memorised
        record. The constant depends only on n, d and k, so it cancels in the ratio provided
        both densities use the same k.
        """
        n, d = train.shape
        k = max(1, min(k, n - 1)) if n > 1 else 1

        # LEAVE-ONE-OUT, and why it is applied to only one of the two densities.
        #
        # The reference density is fitted on the non-member split, and those same records are
        # then scored against it — so each is its own nearest neighbour at distance 0, its
        # estimated reference density is enormous, and its ratio score is pushed down. That
        # depresses every non-member relative to every member and manufactures discrimination
        # from nothing. Measured: the shuffled control (a release containing no real record)
        # scored AUC 0.576 instead of chance until this was fixed.
        #
        # The SYNTHETIC density gets no such correction. A member sitting at distance 0 from
        # the release is not an artefact there — it is the release having memorised that
        # record, which is exactly the leakage this attack exists to detect.
        n_query = k + 1 if leave_one_out else k
        n_query = min(n_query, n)
        nn = NearestNeighbors(n_neighbors=n_query).fit(train)
        dist, _ = nn.kneighbors(query)

        if leave_one_out and dist.shape[1] > 1:
            # Drop a self-match when the query point is (numerically) in `train`.
            self_match = dist[:, 0] <= 1e-12
            r_k = np.where(self_match, dist[:, -1], dist[:, min(k - 1, dist.shape[1] - 1)])
        else:
            r_k = dist[:, -1]

        # Floor the radius so an exact match yields a large finite density rather than inf,
        # which would make the score unorderable.
        r_k = np.maximum(r_k, 1e-12)
        return -d * np.log(r_k)

    # ------------------------------------------------------------------ attack

    def evaluate(self, synthetic_df: pd.DataFrame, train_df: pd.DataFrame,
                 test_df: pd.DataFrame,
                 reference_df: Optional[pd.DataFrame] = None) -> DomiasResult:
        """Scores members vs non-members by density ratio.

        Args:
            synthetic_df: The release under attack.
            train_df: Records the mechanism saw (members).
            test_df: Records it did not (non-members).
            reference_df: Population reference. Defaults to `test_df` — the standard choice,
                since non-members are by construction drawn from the population and unseen by
                the mechanism.
        """
        if self.max_records is not None:
            train_df = train_df.head(self.max_records)
            test_df = test_df.head(self.max_records)

        reference_df = test_df if reference_df is None else reference_df
        cols = self._numeric_columns(train_df, test_df, synthetic_df, reference_df)
        if len(cols) < 1:
            raise ValueError("DOMIAS needs at least one shared numeric column.")
        if len(train_df) == 0 or len(test_df) == 0:
            raise ValueError("DOMIAS needs both member and non-member records.")

        # Standardise on the SYNTHETIC data: the attacker sees the release, not the original.
        scaler = StandardScaler().fit(synthetic_df[cols].to_numpy(dtype=float))

        def prep(df: pd.DataFrame) -> np.ndarray:
            return np.nan_to_num(scaler.transform(df[cols].to_numpy(dtype=float)))

        synth = prep(synthetic_df)
        ref = prep(reference_df)
        targets = np.vstack([prep(train_df), prep(test_df)])
        labels = np.concatenate([np.ones(len(train_df)), np.zeros(len(test_df))])

        bw = self.bandwidth or self._scott_bandwidth(synth)

        # Work in logs: the ratio spans many orders of magnitude, and the difference of
        # log-densities is numerically stable where the quotient is not.
        if self.estimator == "knn":
            log_p_synth = self._log_density_knn(synth, targets, self.k)
            # Leave-one-out on the reference only: scored non-members are usually IN the
            # reference set, and their self-match would fabricate discrimination.
            log_p_ref = self._log_density_knn(ref, targets, self.k, leave_one_out=True)
        else:
            log_p_synth = self._log_density_kde(synth, targets, bw)
            log_p_ref = self._log_density_kde(ref, targets, bw)
        scores = log_p_synth - log_p_ref

        auc = float(roc_auc_score(labels, scores))
        fpr, tpr, _ = roc_curve(labels, scores)

        return DomiasResult(
            auc=auc,
            advantage=float(np.max(tpr - fpr)),
            tpr_at_1pct_fpr=float(np.interp(0.01, fpr, tpr)),
            tpr_at_01pct_fpr=float(np.interp(0.001, fpr, tpr)),
            num_members=len(train_df),
            num_nonmembers=len(test_df),
            num_reference=len(reference_df),
            estimator=self.estimator,
            bandwidth=bw,
        )
