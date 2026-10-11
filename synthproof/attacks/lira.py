"""LiRA: the Likelihood Ratio Attack (Carlini et al., IEEE S&P 2022), run against a synthesiser.

WHAT MAKES THIS LiRA AND NOT A CHEAPER ATTACK WEARING ITS NAME. This repository refused, twice,
to call a weaker attack "LiRA" (audit finding F7: a module of that name reported a fabricated
AUC). What this module does is the algorithm itself, adapted from classifiers to generative
releases the way the synthetic-data literature does (Stadler et al., USENIX Sec 2022; Houssiau
et al., "TAPAS", 2022):

  1. For each TARGET record x, train K SHADOW releases with the same mechanism and epsilon on
     datasets drawn from the attacker's reference population: half with x included (IN), half
     without (OUT).
  2. Score every shadow release by a per-record statistic s(release, x).
  3. Fit a Gaussian to the IN scores and one to the OUT scores -- per target. The per-example
     calibration is LiRA's contribution: a record that is far from everything scores low in
     every release, member or not, and a global threshold misreads that as non-membership.
  4. For a CHALLENGE release, membership evidence is the likelihood ratio
         Lambda = log N(s; mu_in, sd_in) - log N(s; mu_out, sd_out).
  5. Report AUC and TPR at low FPR over many targets x many fresh challenge releases (half of
     which contain the target), which is how Carlini et al. say an MIA must be read.

THE SCORE. s = -log(1 + d(x, release)), where d is the distance to the nearest released record:
numeric columns standardised by the release's own spread, plus one per mismatched categorical
column -- the same metric as `DistanceMIABaseline`. LiRA's strength comes from steps 1, 3 and 4,
not from the score; a stronger score would only strengthen the attack.

THREAT MODEL, stated. The attacker knows the mechanism, its epsilon, the release size and the
target record, and holds a reference sample from the same population (disjoint from the
targets). That is the standard LiRA adversary and stronger than a typical real one.

COST. Each target needs K + C fits. Carlini et al. use up to 256 shadows; here K is a parameter
(default 16). Fewer shadows give noisier Gaussians and therefore a WEAKER attack, so a null at
small K is a bounded null, never evidence of privacy. A positive control (a leaky generator)
must be detected before any null is reported -- `scripts/run_lira.py` does that first.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import roc_auc_score, roc_curve

from synthproof.accounting.accountant import Accountant
from synthproof.data.dataset import TabularDataset
from synthproof.data.profiler import DPDomainProfiler

# A Gaussian fitted to near-identical scores would have sd ~ 0 and produce infinite ratios. The
# floor is relative to the spread of all shadow scores for that target.
_SD_FLOOR_FRAC = 0.05


@dataclass
class LiRAResult:
    """Outcome of one LiRA run."""

    mechanism: str
    target_eps: Optional[float]
    auc: float
    tpr_at_1pct_fpr: float
    tpr_at_10pct_fpr: float
    num_targets: int
    num_shadows: int
    num_challenges: int
    train_size: int
    per_target: List[Dict[str, Any]] = field(default_factory=list)
    # One entry per challenge release: the likelihood ratio, the true membership bit, and which
    # target it attacked. Kept so the AUC's interval can be resampled BY TARGET -- challenges on
    # the same record are not independent.
    scores: List[float] = field(default_factory=list)
    labels: List[int] = field(default_factory=list)
    groups: List[int] = field(default_factory=list)

    def auc_ci(self, resamples: int = 2000, seed: int = 0) -> "tuple[float, float]":
        """95% percentile bootstrap interval for the AUC, resampling targets."""
        rng = np.random.default_rng(seed)
        y, s, g = np.asarray(self.labels), np.asarray(self.scores), np.asarray(self.groups)
        uniq = np.unique(g)
        aucs = []
        for _ in range(resamples):
            pick = rng.choice(uniq, size=len(uniq), replace=True)
            idx = np.concatenate([np.flatnonzero(g == t) for t in pick])
            if len(np.unique(y[idx])) == 2:
                aucs.append(roc_auc_score(y[idx], s[idx]))
        return float(np.quantile(aucs, 0.025)), float(np.quantile(aucs, 0.975))


def _distance_scores(target: pd.DataFrame, release: pd.DataFrame) -> float:
    """-log(1 + nearest distance) from the one-row `target` to `release`."""
    num = [c for c in target.columns if pd.api.types.is_numeric_dtype(release[c])]
    cat = [c for c in target.columns if c not in num]
    d2 = np.zeros(len(release))
    if num:
        rel = release[num].to_numpy(dtype=float)
        scale = np.nanstd(rel, axis=0)
        scale[~np.isfinite(scale) | (scale == 0)] = 1.0
        d2 += np.nansum(((rel - target[num].to_numpy(dtype=float)[0]) / scale) ** 2, axis=1)
    if cat:
        d2 += (release[cat].astype(str).to_numpy() != target[cat].astype(str).to_numpy()[0]).sum(
            axis=1
        )
    return float(-np.log1p(np.sqrt(d2.min())))


class LiRAAttack:
    """Shadow-release LiRA against a synthesis mechanism."""

    def __init__(
        self,
        make_generator: Callable[[int], Any],
        mechanism_name: str,
        target_eps: Optional[float],
        num_targets: int = 20,
        num_shadows: int = 16,
        num_challenges: int = 8,
        train_size: int = 1000,
        delta: float = 1e-5,
        seed: int = 0,
        target_selection: str = "outlier",
    ):
        """
        Args:
            make_generator: seed -> a fresh, unfitted generator (e.g. lambda s: MSTGenerator(s)).
            target_eps: epsilon the mechanism is run at; None for a non-private control.
            num_shadows: shadow releases per target, split evenly IN / OUT. Must be >= 4.
            num_challenges: fresh releases per target that are actually attacked, half IN.
            target_selection: "outlier" (most isolated records, the vulnerable ones the
                literature attacks) or "random".
        """
        if num_shadows < 4 or num_shadows % 2:
            raise ValueError("num_shadows must be an even number >= 4.")
        if num_challenges < 2 or num_challenges % 2:
            raise ValueError("num_challenges must be an even number >= 2.")
        if target_selection not in ("outlier", "random"):
            raise ValueError("target_selection must be 'outlier' or 'random'.")
        self.make_generator = make_generator
        self.mechanism_name = mechanism_name
        self.target_eps = target_eps
        self.num_targets = num_targets
        self.num_shadows = num_shadows
        self.num_challenges = num_challenges
        self.train_size = train_size
        self.delta = delta
        self.seed = seed
        self.target_selection = target_selection

    # ------------------------------------------------------------------ pieces

    def _release(self, train: pd.DataFrame, population: TabularDataset, seed: int) -> pd.DataFrame:
        """Fits the mechanism on `train` exactly as a release would, and returns its output."""
        ds = TabularDataset(train.reset_index(drop=True), schema=population.schema)
        eps = self.target_eps if self.target_eps is not None else 1.0
        acc = Accountant(budget_eps=eps * (1 + 1e-6), budget_delta=self.delta)
        prof = DPDomainProfiler(accountant=acc, eps_budget=eps).profile(ds, seed=seed)
        gen = self.make_generator(seed)
        gen.fit(ds, prof, acc, target_eps=eps)
        return gen.generate(num_samples=len(train))

    def _choose_targets(self, df: pd.DataFrame, rng: np.random.Generator) -> np.ndarray:
        if self.target_selection == "random":
            return rng.choice(len(df), size=self.num_targets, replace=False)
        # Isolation = distance to the nearest OTHER record (the same metric as the score), on a
        # capped sample for speed. The lowest score is the most isolated record.
        sample = df.sample(n=min(len(df), 600), random_state=int(rng.integers(2**31)))
        iso = np.array(
            [
                _distance_scores(sample.iloc[[i]], sample.drop(index=sample.index[i]))
                for i in range(len(sample))
            ]
        )
        top = np.argsort(iso)[: self.num_targets]
        return np.array([df.index.get_loc(sample.index[i]) for i in top])

    def _score(
        self,
        x: pd.DataFrame,
        member: int,
        pool: pd.DataFrame,
        population: TabularDataset,
        rng: np.random.Generator,
    ) -> float:
        """One release on a fresh reference sample, with x in it iff `member`; x's score."""
        rows = rng.choice(len(pool), size=self.train_size, replace=False)
        train = pool.iloc[rows]
        if member:
            # Replace one record, so IN and OUT releases have the same size.
            train = pd.concat([train.iloc[:-1], x], ignore_index=True)
        seed = int(rng.integers(0, 2**31 - 1))
        return _distance_scores(x, self._release(train, population, seed))

    @staticmethod
    def _fit_gaussian(xs: List[float], floor: float):
        a = np.asarray(xs, dtype=float)
        return float(a.mean()), float(max(a.std(ddof=1) if len(a) > 1 else 0.0, floor))

    # ------------------------------------------------------------------ run

    def run(self, population: TabularDataset) -> LiRAResult:
        """Attacks `num_targets` records of `population`; the rest is the reference pool."""
        rng = np.random.default_rng(self.seed)
        df = population.df.reset_index(drop=True)
        if len(df) < self.train_size + self.num_targets + 1:
            raise ValueError("population is too small for this train_size and num_targets.")
        targets = self._choose_targets(df, rng)
        pool = df.drop(index=list(targets)).reset_index(drop=True)

        lrs: List[float] = []
        labels: List[int] = []
        groups: List[int] = []
        per_target: List[Dict[str, Any]] = []
        for t_idx in targets:
            x = df.iloc[[t_idx]]
            scores: Dict[int, List[float]] = {1: [], 0: []}
            for k in range(self.num_shadows):
                member = k % 2
                scores[member].append(self._score(x, member, pool, population, rng))
            spread = np.ptp(scores[0] + scores[1]) or 1.0
            mu_in, sd_in = self._fit_gaussian(scores[1], _SD_FLOOR_FRAC * spread)
            mu_out, sd_out = self._fit_gaussian(scores[0], _SD_FLOOR_FRAC * spread)

            for c in range(self.num_challenges):
                member = c % 2
                s = self._score(x, member, pool, population, rng)
                lr = float(
                    stats.norm.logpdf(s, mu_in, sd_in) - stats.norm.logpdf(s, mu_out, sd_out)
                )
                lrs.append(lr)
                labels.append(member)
                groups.append(int(t_idx))
            per_target.append(
                {
                    "target": int(t_idx),
                    "mu_in": mu_in,
                    "mu_out": mu_out,
                    "sd_in": sd_in,
                    "sd_out": sd_out,
                }
            )

        y, score = np.asarray(labels), np.asarray(lrs)
        fpr, tpr, _ = roc_curve(y, score)
        return LiRAResult(
            mechanism=self.mechanism_name,
            target_eps=self.target_eps,
            auc=float(roc_auc_score(y, score)),
            tpr_at_1pct_fpr=float(np.interp(0.01, fpr, tpr)),
            tpr_at_10pct_fpr=float(np.interp(0.10, fpr, tpr)),
            num_targets=len(targets),
            num_shadows=self.num_shadows,
            num_challenges=self.num_challenges,
            train_size=self.train_size,
            per_target=per_target,
            scores=lrs,
            labels=labels,
            groups=groups,
        )
