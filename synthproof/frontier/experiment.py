"""Multi-seed experiment runner with confidence intervals.

Every cell of the grid (dataset × mechanism × epsilon) is run over several seeds and reported
as a mean with a bootstrapped 95% interval. A single-seed number from a randomised mechanism
is not evidence, and the preregistration commits to 5 seeds per configuration.
"""

from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence

import numpy as np

from synthproof.accounting.accountant import Accountant
from synthproof.accounting.calibration import BudgetPlan
from synthproof.attacks.distance_mia import DistanceMIABaseline
from synthproof.audit.canary import CanaryAuditor
from synthproof.data.dataset import TabularDataset
from synthproof.data.profiler import DPDomainProfiler
from synthproof.evaluate.utility import UtilityEvaluator
from synthproof.generators.aim import AIMGenerator, mbi_available
from synthproof.generators.copula import GaussianCopulaGenerator
from synthproof.generators.independent import IndependentMarginalGenerator
from synthproof.generators.pairwise import PairwiseMarginalGenerator

DEFAULT_SEEDS = (0, 1, 2, 3, 4)
DEFAULT_EPS_GRID = (0.5, 1.0, 2.0, 4.0, 8.0)

# Mechanism families. "independent" and "pairwise" differ in model class, which is what H1
# compares; "copula" is a second independent-marginal implementation kept as a control.
MECHANISMS: Dict[str, type] = {
    "independent": IndependentMarginalGenerator,
    "copula": GaussianCopulaGenerator,
    "pairwise": PairwiseMarginalGenerator,
}

# Real AIM needs private-PGM, which needs Python >= 3.11. Registered only when importable so
# the rest of the grid still runs on an environment without it.
if mbi_available():
    MECHANISMS["aim"] = AIMGenerator


@dataclass
class Interval:
    """A point estimate with a bootstrapped confidence interval."""

    mean: float
    lo: float
    hi: float
    sd: float
    n: int

    def __str__(self) -> str:
        return f"{self.mean:.3f} [{self.lo:.3f}, {self.hi:.3f}]"


def bootstrap_ci(values: Sequence[float], confidence: float = 0.95,
                 resamples: int = 4000, seed: int = 0) -> Interval:
    """Percentile bootstrap interval over `values`."""
    arr = np.asarray([v for v in values if np.isfinite(v)], dtype=float)
    if arr.size == 0:
        return Interval(float("nan"), float("nan"), float("nan"), float("nan"), 0)
    if arr.size == 1:
        v = float(arr[0])
        return Interval(v, v, v, 0.0, 1)

    rng = np.random.default_rng(seed)
    means = rng.choice(arr, size=(resamples, arr.size), replace=True).mean(axis=1)
    alpha = (1.0 - confidence) / 2.0
    return Interval(
        mean=float(arr.mean()),
        lo=float(np.quantile(means, alpha)),
        hi=float(np.quantile(means, 1.0 - alpha)),
        sd=float(arr.std(ddof=1)) if arr.size > 1 else 0.0,
        n=int(arr.size),
    )


@dataclass
class CellResult:
    """Aggregated result for one (dataset, mechanism, epsilon) cell."""

    dataset: str
    mechanism: str
    target_eps: float
    seeds: int
    proved_eps: Interval
    audited_eps: Interval
    audit_p: Interval
    tstr_f1: Interval
    trtr_f1: Interval
    mia_auc: Interval
    correlation_error: Interval
    raw: Dict[str, List[float]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("raw", None)
        return d


# A column that is overwhelmingly one value carries almost no correlation signal, and its
# sample correlation is dominated by the handful of non-modal rows. Including such columns
# makes the structure metric measure noise. UCI Adult's capital_gain (91.6% zeros) and
# capital_loss (95.5% zeros) are exactly this case.
MAX_MODAL_SHARE = 0.85


def informative_numeric_columns(df, cols: Sequence[str],
                                max_modal_share: float = MAX_MODAL_SHARE) -> List[str]:
    """Numeric columns with enough spread for a correlation to mean anything."""
    keep = []
    for c in cols:
        s = df[c]
        if s.std() > 0 and (s.value_counts(normalize=True).iloc[0] <= max_modal_share):
            keep.append(c)
    return keep


def _mean_abs_corr_error(real, synth, cols: List[str]) -> float:
    """Mean absolute error over the pairwise correlation matrix — a structure metric.

    Independent-marginal mechanisms score badly here by construction; a model that captures
    pairwise dependence should score better. This is the quantity that separates the families.
    """
    if len(cols) < 2:
        return float("nan")
    a = real[cols].corr().to_numpy()
    b = synth[cols].corr().to_numpy()
    iu = np.triu_indices(len(cols), k=1)
    diff = np.abs(a[iu] - b[iu])
    return float(np.nanmean(diff)) if diff.size else float("nan")


def run_cell(dataset: TabularDataset, mechanism: str, target_eps: float,
             seed: int, delta: float = 1e-5, holdout_frac: float = 0.3,
             num_canaries: int = 60, target_col: Optional[str] = None,
             corr_cols: Optional[Sequence[str]] = None,
             on_stage: Optional[Callable[[str, dict], None]] = None,
             return_artifacts: bool = False) -> Dict[str, Any]:
    """Runs one (mechanism, epsilon, seed) configuration and returns raw measurements.

    Args:
        on_stage: Optional callback invoked as `on_stage(name, payload)` after each pipeline
            stage. The API's live console uses this to stream progress; it exists so the demo
            surface drives THIS pipeline rather than reimplementing it. A fourth parallel
            pipeline is exactly the divergence that let the sweep runner and the frontier
            engine drift apart.
        return_artifacts: When True, the returned dict additionally carries the fitted
            objects (`_synth`, `_fit_df`, `_holdout_df`, `_profile`, `_canaries`, `_spends`)
            under underscore-prefixed keys. Numeric keys are unchanged either way, so callers
            that aggregate results are unaffected.
    """
    if mechanism not in MECHANISMS:
        raise KeyError(f"Unknown mechanism {mechanism!r}. Known: {sorted(MECHANISMS)}")

    emit = on_stage if on_stage is not None else (lambda *_a, **_k: None)

    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(dataset.df))
    n_hold = max(20, int(len(idx) * holdout_frac))
    holdout_df = dataset.df.iloc[idx[:n_hold]].reset_index(drop=True)
    fit_df = dataset.df.iloc[idx[n_hold:]].reset_index(drop=True)
    fit_ds = TabularDataset(fit_df, name=dataset.name, schema=dataset.schema)
    emit("split", {"fit_rows": len(fit_df), "holdout_rows": len(holdout_df)})

    plan = BudgetPlan.split(target_eps, delta=delta, profile_frac=0.1)
    acc = Accountant(budget_eps=target_eps * 1.02, budget_delta=delta)
    emit("budget", {"total_eps": target_eps, "profile_eps": plan.profile_eps,
                    "synthesis_eps": plan.synthesis_eps, "delta": delta})

    auditor = CanaryAuditor(num_canaries=num_canaries, seed=seed)
    aug_ds, canary_set = auditor.plant_canaries(fit_ds)
    # Report what was actually planted, not what was requested. They coincide today, but a
    # reported count that cannot drift from reality is worth one attribute access.
    emit("canaries", {
        "planted": len(canary_set.members),
        "holdout": len(canary_set.holdout),
        "fraction_of_fit": round(len(canary_set.members) / max(1, len(fit_df)), 5),
    })

    profiler = DPDomainProfiler(accountant=acc, eps_budget=plan.profile_eps)
    profile = profiler.profile(aug_ds, seed=seed)
    emit("profile", {
        "eps_spent": float(acc.total()),
        "eps_remaining": float(acc.remaining()),
        "suppressed_categories": int(sum(c.suppressed_categories
                                         for c in profile.columns.values())),
        "public_ranges": int(sum(1 for c in profile.columns.values() if c.is_public_range)),
    })

    gen = MECHANISMS[mechanism](seed=seed)
    gen.fit(aug_ds, profile, acc, target_eps=plan.synthesis_eps)
    emit("fit", {"eps_spent": float(acc.total()), "eps_remaining": float(acc.remaining()),
                 "charges": len(acc.spends)})

    synth = gen.generate(num_samples=len(fit_df))
    emit("generate", {"rows": len(synth)})

    audit = auditor.audit(synth, canary_set)
    emit("audit", {"audited_eps": float(audit.audited_eps), "tpr": float(audit.tpr),
                   "fpr": float(audit.fpr), "p_value": float(audit.p_value)})

    # Defaulting to categorical_cols[0] picked `workclass` on UCI Adult — 7 classes, 73%
    # majority — which is not the benchmark's prediction task and produced macro-F1 near
    # chance for every mechanism, hiding any real difference. Callers should name the target.
    if target_col is None:
        target_col = dataset.categorical_cols[0] if dataset.categorical_cols else None
    if target_col is None:
        raise ValueError("Utility evaluation needs a categorical target column.")
    # REFERENCE TABLE. Both metrics below score the synthetic output against `fit_ds.df`,
    # not against `dataset.df`. Two reasons, and the choice is deliberate:
    #
    #   * `dataset.df` includes the holdout rows the generator never saw, so scoring against
    #     it mixes a fidelity question with a generalisation question.
    #   * `fit_ds.df` is the real population the mechanism was trained on. The canaries in
    #     `aug_ds` are an audit instrument we injected, not data anyone wants reproduced.
    #
    # This does NOT eliminate canary contamination — the generator was still FITTED on a
    # table containing `num_canaries` extreme rows, and on UCI Adult 60 of them move
    # corr(age, hours_per_week) substantially. It removes the holdout leak and makes the
    # reference the closest available match to what the mechanism saw. `canary_fraction` is
    # returned alongside so no consumer can read `correlation_error` as a clean fidelity
    # measurement without seeing how contaminated the fit was.
    reference_df = fit_ds.df

    util = UtilityEvaluator(target_col=target_col, seed=seed).evaluate(reference_df, synth)
    emit("utility", {"tstr_f1": float(util.tstr_macro_f1),
                     "trtr_f1": float(util.trtr_macro_f1)})

    mia = DistanceMIABaseline(seed=seed, max_records=400).evaluate(
        synth, train_df=fit_ds.df, test_df=holdout_df)
    emit("attack", {"auc": float(mia.auc), "advantage": float(mia.advantage),
                    "tpr_at_1pct_fpr": float(mia.tpr_at_1pct_fpr)})

    out: Dict[str, Any] = {
        "proved_eps": float(acc.total()),
        "audited_eps": float(audit.audited_eps),
        "audit_p": float(audit.p_value),
        "tstr_f1": float(util.tstr_macro_f1),
        "trtr_f1": float(util.trtr_macro_f1),
        "mia_auc": float(mia.auc),
        "correlation_error": _mean_abs_corr_error(
            reference_df, synth,
            list(corr_cols) if corr_cols is not None
            else informative_numeric_columns(reference_df, fit_ds.numerical_cols)),
        # Metadata a consumer needs in order to read the two metrics above honestly.
        "reference": "fit_split",
        "canary_fraction": len(canary_set.members) / max(1, len(fit_df)),
    }

    if return_artifacts:
        out.update({
            "_synth": synth, "_fit_df": fit_ds.df, "_holdout_df": holdout_df,
            "_profile": profile, "_canaries": canary_set, "_spends": acc.spends,
            "_audit": audit, "_mia": mia,
        })
    return out


def run_grid(dataset: TabularDataset,
             mechanisms: Sequence[str] = tuple(MECHANISMS),
             eps_grid: Sequence[float] = DEFAULT_EPS_GRID,
             seeds: Sequence[int] = DEFAULT_SEEDS,
             delta: float = 1e-5,
             target_col: Optional[str] = None,
             corr_cols: Optional[Sequence[str]] = None,
             progress: Optional[Callable[[str], None]] = None) -> List[CellResult]:
    """Runs the full grid, aggregating each cell across seeds."""
    results: List[CellResult] = []
    for mech in mechanisms:
        for eps in eps_grid:
            raw: Dict[str, List[float]] = {}
            for seed in seeds:
                if progress:
                    progress(f"  {mech:<12} eps={eps:<5} seed={seed}")
                for k, v in run_cell(dataset, mech, eps, seed, delta=delta,
                                     target_col=target_col, corr_cols=corr_cols).items():
                    raw.setdefault(k, []).append(v)

            results.append(CellResult(
                dataset=dataset.name, mechanism=mech, target_eps=float(eps),
                seeds=len(seeds),
                proved_eps=bootstrap_ci(raw["proved_eps"]),
                audited_eps=bootstrap_ci(raw["audited_eps"]),
                audit_p=bootstrap_ci(raw["audit_p"]),
                tstr_f1=bootstrap_ci(raw["tstr_f1"]),
                trtr_f1=bootstrap_ci(raw["trtr_f1"]),
                mia_auc=bootstrap_ci(raw["mia_auc"]),
                correlation_error=bootstrap_ci(raw["correlation_error"]),
                raw=raw,
            ))
    return results
