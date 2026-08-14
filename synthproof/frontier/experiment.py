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
             return_artifacts: bool = False,
             separate_utility_fit: bool = True) -> Dict[str, Any]:
    """Runs one (mechanism, epsilon, seed) configuration and returns raw measurements.

    Fits the mechanism TWICE by default: once on the canary-augmented split for the audit,
    and once on the clean split for utility and structure. Measuring both from a single
    canary-trained model is what made hypothesis H1 unmeasurable — see the comment at the
    utility release below.

    Args:
        on_stage: Optional callback invoked as `on_stage(name, payload)` after each pipeline
            stage. The API's live console uses this to stream progress; it exists so the demo
            surface drives THIS pipeline rather than reimplementing it. A fourth parallel
            pipeline is exactly the divergence that let the sweep runner and the frontier
            engine drift apart.
        return_artifacts: When True, the returned dict additionally carries the fitted
            objects (`_synth`, `_fit_df`, `_holdout_df`, `_profile`, `_canaries`, `_spends`,
            `_audit`, `_mia`) under underscore-prefixed keys. `_synth` is the UTILITY release,
            since that is the one a consumer should visualise. Numeric keys are unchanged
            either way, so callers that aggregate results are unaffected.
        separate_utility_fit: Fit a second, canary-free model for utility and structure.
            Setting this False restores the single-fit behaviour and reinstates the
            contamination; it exists for ablation and for halving the cost of a smoke test,
            and the choice is reported back as `utility_source`.
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

    def _synthesise(source: TabularDataset, accountant: Accountant):
        """Profiles and fits one release from `source`, returning its synthetic table."""
        prof = DPDomainProfiler(accountant=accountant,
                                eps_budget=plan.profile_eps).profile(source, seed=seed)
        generator = MECHANISMS[mechanism](seed=seed)
        generator.fit(source, prof, accountant, target_eps=plan.synthesis_eps)
        return generator.generate(num_samples=len(fit_df)), prof

    # ---------------------------------------------------------------- audit release
    # Fitted on the canary-augmented table, because an audit needs planted canaries to
    # detect. This release is used for the audit and the membership-inference attack ONLY.
    audit_synth, profile = _synthesise(aug_ds, acc)
    emit("profile", {
        "eps_spent": float(acc.total()),
        "eps_remaining": float(acc.remaining()),
        "suppressed_categories": int(sum(c.suppressed_categories
                                         for c in profile.columns.values())),
        "public_ranges": int(sum(1 for c in profile.columns.values() if c.is_public_range)),
    })
    emit("fit", {"eps_spent": float(acc.total()), "eps_remaining": float(acc.remaining()),
                 "charges": len(acc.spends)})
    emit("generate", {"rows": len(audit_synth)})

    audit = auditor.audit(audit_synth, canary_set)
    emit("audit", {"audited_eps": float(audit.audited_eps), "tpr": float(audit.tpr),
                   "fpr": float(audit.fpr), "p_value": float(audit.p_value)})

    # ---------------------------------------------------------------- utility release
    # A SECOND, independent fit on the clean split, used for utility and structure.
    #
    # This is the fix for the contamination that made H1 unmeasurable. Canaries are extreme
    # by construction, and enough of them move the joint distribution: measured on UCI Adult,
    # 60 canaries drop corr(age, hours_per_week) from 0.101 to 0.011. Scoring a
    # canary-trained model against any clean reference therefore penalises exactly the
    # mechanisms that model dependence well, because they faithfully reproduce an artefact we
    # injected. Randomising the canary direction changed the sign of that bias but not its
    # size.
    #
    # These are two measurements of one mechanism CONFIGURATION, not two releases of one
    # dataset — an experiment asking "what does this mechanism do at this epsilon", not a
    # data holder publishing twice. Each fit gets its own accountant and composes to the same
    # epsilon by construction, since the calibration inputs are identical.
    if separate_utility_fit:
        util_acc = Accountant(budget_eps=target_eps * 1.02, budget_delta=delta)
        util_synth, _ = _synthesise(fit_ds, util_acc)
        utility_source = "clean_fit"
    else:
        util_acc, util_synth = acc, audit_synth
        utility_source = "audit_fit"
    emit("utility_fit", {"source": utility_source,
                         "eps_spent": float(util_acc.total())})

    # Defaulting to categorical_cols[0] picked `workclass` on UCI Adult — 7 classes, 73%
    # majority — which is not the benchmark's prediction task and produced macro-F1 near
    # chance for every mechanism, hiding any real difference. Callers should name the target.
    if target_col is None:
        target_col = dataset.categorical_cols[0] if dataset.categorical_cols else None
    if target_col is None:
        raise ValueError("Utility evaluation needs a categorical target column.")
    # The reference is the clean fit split: the real population the mechanism was trained
    # on, and — unlike `dataset.df` — free of the holdout rows it never saw. With
    # `separate_utility_fit` the synthetic side is now canary-free too, so both sides of the
    # comparison describe the same population.
    reference_df = fit_ds.df

    util = UtilityEvaluator(target_col=target_col, seed=seed).evaluate(
        reference_df, util_synth)
    emit("utility", {"tstr_f1": float(util.tstr_macro_f1),
                     "trtr_f1": float(util.trtr_macro_f1)})

    # The MIA runs against the AUDIT release. It asks whether training membership is
    # recoverable, which is a question about the release that actually contained the members.
    mia = DistanceMIABaseline(seed=seed, max_records=400).evaluate(
        audit_synth, train_df=fit_ds.df, test_df=holdout_df)
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
            reference_df, util_synth,
            list(corr_cols) if corr_cols is not None
            else informative_numeric_columns(reference_df, fit_ds.numerical_cols)),
        # Metadata a consumer needs in order to read the two metrics above honestly.
        "reference": "fit_split",
        "utility_source": utility_source,
        "canary_fraction": (0.0 if separate_utility_fit
                            else len(canary_set.members) / max(1, len(fit_df))),
    }

    if return_artifacts:
        out.update({
            # `_synth` is the UTILITY release — the canary-free one a console should show.
            # `_audit_synth` is the canary-trained release the audit ran against.
            "_synth": util_synth, "_audit_synth": audit_synth,
            "_fit_df": fit_ds.df, "_holdout_df": holdout_df,
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
