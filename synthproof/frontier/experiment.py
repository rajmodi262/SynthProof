"""Multi-seed experiment runner with confidence intervals.

Every cell of the grid (dataset × mechanism × epsilon) is run over several seeds and reported
as a mean with a bootstrapped 95% interval. A single-seed number from a randomised mechanism
is not evidence, and the preregistration commits to 5 seeds per configuration.
"""

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Union

import numpy as np
import pandas as pd

from synthproof.accounting.accountant import Accountant
from synthproof.accounting.calibration import BudgetPlan
from synthproof.attacks.attribute_inference import AttributeInferenceAttack
from synthproof.attacks.distance_mia import DistanceMIABaseline
from synthproof.attacks.domias import DOMIAS
from synthproof.attacks.exact_match_risk import ExactMatchRiskEvaluator
from synthproof.attacks.linkability import LinkabilityEvaluator
from synthproof.audit.canary import AuditResult, CanaryAuditor, CanarySet
from synthproof.audit.steinke import OneRunCanarySet, SteinkeAuditor, SteinkeResult
from synthproof.data.dataset import TabularDataset
from synthproof.data.profiler import DPDomainProfiler
from synthproof.evaluate.fidelity import association_error, pairwise_tvd
from synthproof.evaluate.utility import UtilityEvaluator
from synthproof.frontier.checkpoint import run_with_checkpoints
from synthproof.generators.aim import AIMGenerator, mbi_available
from synthproof.generators.independent import IndependentMarginalGenerator
from synthproof.generators.moments import GaussianMomentGenerator
from synthproof.generators.pairwise import PairwiseMarginalGenerator

DEFAULT_SEEDS = (0, 1, 2, 3, 4)
# Part of every cached cell's configuration hash. Bump it whenever a change alters what a cell
# computes, so a checkpoint from older code can never be silently reused. "audit27" = the
# research/27 fixes (declared domains released whole, rebuilt AIM/MST on one zCDP budget,
# held-out utility, table-wide structure metrics, mixed-type MIA).
PIPELINE_VERSION = "audit27"
DEFAULT_EPS_GRID = (0.5, 1.0, 2.0, 4.0, 8.0)

# Mechanism families. "independent" and "pairwise" differ in model class, which is what H1
# compares; "moments" is a second independent-marginal implementation kept as a control.
MECHANISMS: Dict[str, type] = {
    "independent": IndependentMarginalGenerator,
    "moments": GaussianMomentGenerator,
    "pairwise": PairwiseMarginalGenerator,
}

# `dpvae` is the first NON-marginal-based mechanism here, and it is registered as a control
# rather than a competitor. Every other entry selects a set of low-order marginals; a VAE
# trained with DP-SGD selects nothing, which is what makes it the control for the
# clique-selection confound. See generators/dpvae.py.
#
# Registered behind an import guard for the same reason AIM is: it needs JAX, and a missing
# optional backend should make ONE mechanism unavailable, not break the import of the module
# every experiment goes through. jax IS a declared dependency now, so this should not fire --
# it is here so that if it ever does, the failure is legible.
try:
    from synthproof.generators.dpvae import DPVAEGenerator

    MECHANISMS["dpvae"] = DPVAEGenerator
except ImportError:  # pragma: no cover - only when JAX is absent
    pass

# Real AIM needs private-PGM, which needs Python >= 3.11. Registered only when importable so
# the rest of the grid still runs on an environment without it.
if mbi_available():
    MECHANISMS["aim"] = AIMGenerator
    # AIM's engine with the selection step deleted and a data-independent workload in its
    # place. It exists to isolate selection: same model class, same inference, same clique
    # count, same budget, no exponential mechanism. See generators/fixed_workload.py.
    from synthproof.generators.fixed_workload import FixedWorkloadGenerator

    MECHANISMS["fixed_workload"] = FixedWorkloadGenerator

    # MST: the same select-measure-generate family as AIM, but with the model class fixed to a
    # spanning tree (d-1 edges chosen Kruskal-style) rather than AIM's adaptive, unconstrained
    # selection. Registered behind the same mbi guard because it shares private-PGM. See
    # generators/mst.py.
    from synthproof.generators.mst import MSTGenerator

    MECHANISMS["mst"] = MSTGenerator


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


def bootstrap_ci(
    values: Sequence[float], confidence: float = 0.95, resamples: int = 4000, seed: int = 0
) -> Interval:
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
    # Table-wide structure (audit M1): every column pair, not the one pair in corr_cols.
    structure_error_all: Optional[Interval] = None
    pair_tvd: Optional[Interval] = None
    usefulness_multi: Optional[Interval] = None
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


def informative_numeric_columns(
    df, cols: Sequence[str], max_modal_share: float = MAX_MODAL_SHARE
) -> List[str]:
    """Numeric columns with enough spread for a correlation to mean anything."""
    keep = []
    for c in cols:
        s = df[c]
        if s.std() > 0 and (s.value_counts(normalize=True).iloc[0] <= max_modal_share):
            keep.append(c)
    return keep


def _cramers_v(x, y) -> float:
    """Bias-corrected Cramér's V association between two categorical series, in [0, 1]."""
    from scipy.stats import chi2_contingency

    tab = pd.crosstab(x, y)
    if tab.shape[0] < 2 or tab.shape[1] < 2:
        return 0.0
    chi2 = chi2_contingency(tab, correction=False)[0]
    n = tab.to_numpy().sum()
    if n == 0:
        return 0.0
    phi2 = chi2 / n
    r, k = tab.shape
    phi2c = max(0.0, phi2 - (k - 1) * (r - 1) / (n - 1))
    rc = r - (r - 1) ** 2 / (n - 1)
    kc = k - (k - 1) ** 2 / (n - 1)
    denom = min(kc - 1, rc - 1)
    return float(np.sqrt(phi2c / denom)) if denom > 0 else 0.0


def _correlation_ratio(categories, values) -> float:
    """Correlation ratio (eta) between a categorical and a numeric series, in [0, 1]."""
    cats = pd.Series(categories).astype(str)
    vals = pd.to_numeric(pd.Series(values), errors="coerce")
    mask = vals.notna()
    cats, vals = cats[mask], vals[mask]
    if len(vals) < 2:
        return 0.0
    grand = vals.mean()
    ss_between = sum(len(g) * (g.mean() - grand) ** 2 for _, g in vals.groupby(cats.values))
    ss_total = float(((vals - grand) ** 2).sum())
    return float(np.sqrt(ss_between / ss_total)) if ss_total > 0 else 0.0


def _association_matrix(df, cols: List[str]) -> np.ndarray:
    """Symmetric pairwise association matrix over mixed-type columns, each entry in [0, 1].

    num-num uses |Pearson|, num-cat/cat-num uses the correlation ratio (eta), and cat-cat
    uses bias-corrected Cramér's V. This generalises the Pearson correlation matrix so an
    all-categorical or mixed table gets a structure score at all.
    """
    is_num = {c: pd.api.types.is_numeric_dtype(df[c]) for c in cols}
    n = len(cols)
    m = np.eye(n)
    for i in range(n):
        for j in range(i + 1, n):
            ci, cj = cols[i], cols[j]
            if is_num[ci] and is_num[cj]:
                v = abs(float(df[[ci, cj]].corr().iloc[0, 1]))
            elif is_num[ci] and not is_num[cj]:
                v = _correlation_ratio(df[cj], df[ci])
            elif not is_num[ci] and is_num[cj]:
                v = _correlation_ratio(df[ci], df[cj])
            else:
                v = _cramers_v(df[ci], df[cj])
            m[i, j] = m[j, i] = 0.0 if v != v else v
    return m


def _mean_abs_corr_error(real, synth, cols: List[str]) -> float:
    """Mean absolute error over the pairwise association matrix — a structure metric.

    Independent-marginal mechanisms score badly here by construction; a model that captures
    pairwise dependence should score better. This is the quantity that separates the families.

    When every column is numeric this is exactly the mean absolute error of the Pearson
    correlation matrix (the original metric, unchanged, so committed numeric results are
    preserved). When any column is categorical it falls back to a mixed association matrix
    (|Pearson| / correlation-ratio / Cramér's V) so categorical and mixed tables score too.
    """
    if len(cols) < 2:
        return float("nan")
    all_numeric = all(pd.api.types.is_numeric_dtype(real[c]) for c in cols)
    iu = np.triu_indices(len(cols), k=1)
    if all_numeric:
        a = real[cols].corr().to_numpy()
        b = synth[cols].corr().to_numpy()
        diff = np.abs(a[iu] - b[iu])
        return float(np.nanmean(diff)) if diff.size else float("nan")
    a = _association_matrix(real, cols)
    b = _association_matrix(synth, cols)
    diff = np.abs(a[iu] - b[iu])
    return float(np.nanmean(diff)) if diff.size else float("nan")


def run_cell(
    dataset: TabularDataset,
    mechanism: str,
    target_eps: float,
    seed: int,
    delta: float = 1e-5,
    holdout_frac: float = 0.3,
    num_canaries: int = 60,
    target_col: Optional[str] = None,
    corr_cols: Optional[Sequence[str]] = None,
    on_stage: Optional[Callable[[str, dict], None]] = None,
    return_artifacts: bool = False,
    separate_utility_fit: bool = True,
    auditor_kind: str = "one_run",
    release_rows: Optional[int] = None,
) -> Dict[str, Any]:
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
        release_rows: Rows in each synthetic release. It must be PUBLIC: under add/remove-one the
            exact row count is private, so a release sized from the table leaks it
            (docs/design/PUBLIC_RELEASE_BOUNDARY.md, D2). None keeps `len(fit_df)`, which is
            public only when the table size and `holdout_frac` are protocol constants fixed
            before the data is read -- true of the research grids, and of nothing else.
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
    if release_rows is not None and (int(release_rows) != release_rows or release_rows < 1):
        raise ValueError(f"release_rows must be a positive integer, got {release_rows!r}.")
    num_release = len(fit_df) if release_rows is None else int(release_rows)
    # The evaluators and attacks hand their seed to NumPy's legacy generator and to scikit-learn,
    # which accept only 32 bits. They draw no DP noise, so reducing the seed costs no privacy, and
    # every seed below 2**32 -- all the research grids use -- is unchanged.
    eval_seed = seed % (2**32)

    # Profiling is free when the schema declares every bound and category domain (true of every
    # registry dataset): it then reads nothing and charges nothing, so the WHOLE budget goes to
    # synthesis. Reserving 10% for a profiler that spends none of it left that share idle (audit
    # H1, research/27). Only a schema with undeclared domains gets the 10/90 split.
    needs_profile = (
        DPDomainProfiler(
            accountant=Accountant(budget_eps=float("inf"), budget_delta=delta), eps_budget=1.0
        )._query_count(fit_ds)
        > 0
    )
    plan = (
        BudgetPlan.split(target_eps, delta=delta, profile_frac=0.1)
        if needs_profile
        else BudgetPlan(total_eps=target_eps, delta=delta, profile_eps=0.0, synthesis_eps=target_eps)
    )
    # Budget = the target itself, plus float slack only. It used to be `target * 1.02`, a 2%
    # overshoot allowance nothing needed or explained (audit L4).
    budget_cap = target_eps * (1.0 + 1e-6)
    acc = Accountant(budget_eps=budget_cap, budget_delta=delta)
    emit(
        "budget",
        {
            "total_eps": target_eps,
            "profile_eps": plan.profile_eps,
            "synthesis_eps": plan.synthesis_eps,
            "delta": delta,
        },
    )

    # The one-run construction is the default: it spends one canary per comparison rather
    # than two, and is measurably more sensitive to PARTIAL leakage, which is the regime a
    # real mechanism lives in. See results/AUDITOR_COMPARISON.md. The paired auditor stays
    # selectable so the two can be compared on identical runs.
    auditor: Union[SteinkeAuditor, CanaryAuditor]
    if auditor_kind == "one_run":
        auditor = SteinkeAuditor(num_canaries=num_canaries, seed=seed)
    elif auditor_kind == "paired":
        auditor = CanaryAuditor(num_canaries=num_canaries, seed=seed)
    else:
        raise ValueError(f"Unknown auditor {auditor_kind!r}. Use 'one_run' or 'paired'.")
    aug_ds, canary_set = auditor.plant_canaries(fit_ds)
    # Report what was actually planted, not what was requested. They coincide today, but a
    # reported count that cannot drift from reality is worth one attribute access.
    # isinstance, not the string tag: this is what tells the type checker (and the next
    # reader) which result shape follows from which auditor.
    # The canary set is a union for the same reason the auditor is, so it gets the same
    # treatment. Narrowing on the SET rather than on the auditor is what lets the field
    # accesses below be checked.
    if isinstance(canary_set, OneRunCanarySet):
        planted = canary_set.num_included
        total_canaries = len(canary_set.canaries)
    else:
        planted = len(canary_set.members)
        total_canaries = len(canary_set.members) + len(canary_set.holdout)
    emit(
        "canaries",
        {
            "auditor": auditor_kind,
            "planted": planted,
            "total_canaries": total_canaries,
            "fraction_of_fit": round(planted / max(1, len(fit_df)), 5),
        },
    )

    def _synthesise(source: TabularDataset, accountant: Accountant):
        """Profiles and fits one release from `source`, returning its synthetic table."""
        # eps_budget must be positive; with a fully declared schema it is never spent.
        prof = DPDomainProfiler(accountant=accountant, eps_budget=plan.profile_eps or 1.0).profile(
            source, seed=seed
        )
        generator = MECHANISMS[mechanism](seed=seed)
        # The prediction target is public (it is printed in the release's data sheet); a
        # mechanism that can use a target-aware workload is told it.
        if hasattr(generator, "target_col") and target_col is not None:
            generator.target_col = target_col
        generator.fit(source, prof, accountant, target_eps=plan.synthesis_eps)
        return generator.generate(num_samples=num_release), prof

    # ---------------------------------------------------------------- audit release
    # Fitted on the canary-augmented table, because an audit needs planted canaries to
    # detect. This release is used for the audit and the membership-inference attack ONLY.
    audit_synth, profile = _synthesise(aug_ds, acc)
    emit(
        "profile",
        {
            "eps_spent": float(acc.total()),
            "eps_remaining": float(acc.remaining()),
            "suppressed_categories": int(
                sum(c.suppressed_categories for c in profile.columns.values())
            ),
            "public_ranges": int(sum(1 for c in profile.columns.values() if c.is_public_range)),
        },
    )
    emit(
        "fit",
        {
            "eps_spent": float(acc.total()),
            "eps_remaining": float(acc.remaining()),
            "charges": len(acc.spends),
        },
    )
    emit("generate", {"rows": len(audit_synth)})

    # The two auditors return different result types -- SteinkeResult carries the ceiling,
    # accuracy and saturation flag; AuditResult carries the TPR/FPR pair from the paired
    # construction. Branching on the auditor's type rather than on a string keeps the two
    # sets of field accesses provably matched to the object that produced them.
    if isinstance(auditor, SteinkeAuditor) and isinstance(canary_set, OneRunCanarySet):
        steinke_result = auditor.audit(audit_synth, canary_set, delta=delta)
        audit: Union[SteinkeResult, AuditResult] = steinke_result
        emit(
            "audit",
            {
                "audited_eps": float(steinke_result.audited_eps),
                "ceiling": float(steinke_result.ceiling),
                "accuracy": float(steinke_result.accuracy),
                "guesses": int(steinke_result.guesses),
                "saturated": bool(steinke_result.saturated),
                "p_value": float(steinke_result.p_value),
            },
        )
    elif isinstance(auditor, CanaryAuditor) and isinstance(canary_set, CanarySet):
        paired_result = auditor.audit(audit_synth, canary_set)
        audit = paired_result
        emit(
            "audit",
            {
                "audited_eps": float(paired_result.audited_eps),
                "tpr": float(paired_result.tpr),
                "fpr": float(paired_result.fpr),
                "p_value": float(paired_result.p_value),
            },
        )
    else:  # pragma: no cover - the two constructors above cannot produce a mixed pair
        raise TypeError(
            f"Auditor {type(auditor).__name__} produced a "
            f"{type(canary_set).__name__}, which it should not be able to."
        )

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
        util_acc = Accountant(budget_eps=budget_cap, budget_delta=delta)
        util_synth, _ = _synthesise(fit_ds, util_acc)
        utility_source = "clean_fit"
    else:
        util_acc, util_synth = acc, audit_synth
        utility_source = "audit_fit"
    emit("utility_fit", {"source": utility_source, "eps_spent": float(util_acc.total())})

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

    # Scored on `holdout_df`: real rows neither release was fitted on (audit M2).
    util = UtilityEvaluator(target_col=target_col, seed=eval_seed, multi_model=True).evaluate(
        reference_df, util_synth, test_df=holdout_df
    )
    emit("utility", {"tstr_f1": float(util.tstr_macro_f1), "trtr_f1": float(util.trtr_macro_f1)})

    # The MIA runs against the AUDIT release. It asks whether training membership is
    # recoverable, which is a question about the release that actually contained the members.
    # Both distance-based adversaries need a shared numeric column to measure proximity /
    # density on. An all-categorical release (Mushroom, Nursery) has none, so the question
    # does not arise -- reported as NOT APPLICABLE, never as a passed attack, the same rule
    # linkability follows. Attribute inference and singling-out below are set-based and still
    # run, so an all-categorical cell is not left with zero privacy evidence.
    try:
        mia = DistanceMIABaseline(seed=eval_seed, max_records=400).evaluate(
            audit_synth, train_df=fit_ds.df, test_df=holdout_df
        )
        emit(
            "attack",
            {
                "auc": float(mia.auc),
                "advantage": float(mia.advantage),
                "tpr_at_1pct_fpr": float(mia.tpr_at_1pct_fpr),
            },
        )
    except ValueError as exc:
        mia = None
        emit("attack", {"not_applicable": str(exc)})

    # A second, structurally different adversary. The two fail differently -- the baseline is
    # a raw proximity heuristic, DOMIAS divides by a reference density to remove the
    # typicality confound -- so both are reported rather than one standing in for the other.
    try:
        domias = DOMIAS(seed=eval_seed, max_records=400).evaluate(
            audit_synth, train_df=fit_ds.df, test_df=holdout_df
        )
        emit(
            "attack_domias",
            {"auc": float(domias.auc), "tpr_at_1pct_fpr": float(domias.tpr_at_1pct_fpr)},
        )
    except ValueError as exc:
        domias = None
        emit("attack_domias", {"not_applicable": str(exc)})

    # Singling out: does any real record appear in the release as a unique exact match? This
    # is the one risk of the EDPB's three that a release can fail outright rather than by
    # degree, so it is cheap and worth running on every cell. Scored against the AUDIT release
    # for the same reason the MIA is -- that is the release that contained the members.
    singling = ExactMatchRiskEvaluator(seed=eval_seed, max_records=400).evaluate(
        audit_synth, target_df=fit_ds.df
    )
    emit(
        "attack_singling_out",
        {
            "risk": float(singling.singling_out_risk),
            "unique_matches": int(singling.num_unique_matches),
        },
    )

    # Linkability: the third EDPB risk. Two disjoint halves of a record are matched to the
    # release independently; agreement beyond the shuffled-release baseline is the link.
    # With singling out and attribute inference already running, this completes 3 of 3.
    # A table with fewer than four columns cannot be split into two disjoint halves, so the
    # question does not arise. That is NOT APPLICABLE, not a failure, and it must not take the
    # release down with it -- the built-in toy table has three columns and did exactly that.
    # Reported as absent rather than skipped silently, the same rule the second accountant
    # follows: an absent check must never look like a passed one.
    try:
        linkability = LinkabilityEvaluator(seed=eval_seed, max_records=400).evaluate(
            audit_synth, target_df=fit_ds.df
        )
        emit(
            "attack_linkability",
            {
                "rate": float(linkability.linkability_rate),
                "excess_over_baseline": float(linkability.excess_over_baseline),
            },
        )
    except ValueError as exc:
        linkability = None
        emit("attack_linkability", {"not_applicable": str(exc)})

    # Attribute inference, scored against a CONDITIONAL baseline rather than a marginal one.
    # Jayaraman & Evans (CCS 2022) showed that reporting raw attack accuracy as "leakage"
    # mostly measures imputability; `leakage_vs_conditional` is the number that isolates what
    # the release itself contributed. Uses the canary-free release, because this asks what a
    # recipient of the published table can infer.
    attr = AttributeInferenceAttack(
        target_column=target_col, seed=eval_seed, max_records=400
    ).evaluate(util_synth, target_df=fit_ds.df, reference_df=reference_df)
    emit(
        "attack_attribute_inference",
        {
            "accuracy": float(attr.attack_accuracy),
            "leakage_vs_conditional": float(attr.leakage_vs_conditional),
        },
    )

    out: Dict[str, Any] = {
        "proved_eps": float(acc.total()),
        "audited_eps": float(audit.audited_eps),
        "audit_p": float(audit.p_value),
        "tstr_f1": float(util.tstr_macro_f1),
        # Mean per-column Wasserstein-1, SD-standardised. Computed since the first version of
        # this pipeline and never reported; a metric nothing reads cannot catch anything.
        "marginal_w1": float(util.marginal_distance),
        "trtr_f1": float(util.trtr_macro_f1),
        # Mean TSTR/TRTR over random forest, logistic regression and gradient boosting (M3).
        "usefulness_multi": float(util.usefulness_multi),
        # NaN, not 0.0, when a distance-based attack does not apply (all-categorical release).
        # A zero would read as "attack ran, found nothing" -- an absent measurement, not a null.
        "mia_auc": (float(mia.auc) if mia else float("nan")),
        "domias_auc": (float(domias.auc) if domias else float("nan")),
        "domias_tpr_at_1pct": (float(domias.tpr_at_1pct_fpr) if domias else float("nan")),
        "singling_out_risk": float(singling.singling_out_risk),
        # NaN, not 0.0, when the risk does not apply. A zero here would read as "measured, no
        # linkability found" -- the difference between an absent measurement and a null one.
        "linkability_rate": (float(linkability.linkability_rate) if linkability else float("nan")),
        "linkability_excess": (
            float(linkability.excess_over_baseline) if linkability else float("nan")
        ),
        "attr_inference_accuracy": float(attr.attack_accuracy),
        "attr_leakage_vs_conditional": float(attr.leakage_vs_conditional),
        "correlation_error": _mean_abs_corr_error(
            reference_df,
            util_synth,
            (
                list(corr_cols)
                if corr_cols is not None
                else informative_numeric_columns(reference_df, fit_ds.numerical_cols)
            ),
        ),
        # Table-wide structure over EVERY column pair (audit M1, research/27).
        "structure_error_all": association_error(reference_df, util_synth),
        "pair_tvd": pairwise_tvd(reference_df, util_synth),
        # Metadata a consumer needs in order to read the two metrics above honestly.
        "reference": "fit_split",
        "auditor": auditor_kind,
        # The most this audit could have certified. Without it, `audited_eps` is not
        # interpretable -- see results/AUDITOR_COMPARISON.md.
        "audit_ceiling": float(getattr(audit, "ceiling", float("nan"))),
        "utility_source": utility_source,
        "canary_fraction": (
            0.0 if separate_utility_fit else len(canary_set.members) / max(1, len(fit_df))
        ),
    }

    if return_artifacts:
        out.update(
            {
                # `_synth` is the UTILITY release — the canary-free one a console should show.
                # `_audit_synth` is the canary-trained release the audit ran against.
                "_synth": util_synth,
                "_audit_synth": audit_synth,
                "_fit_df": fit_ds.df,
                "_holdout_df": holdout_df,
                "_profile": profile,
                "_canaries": canary_set,
                "_spends": acc.spends,
                "_audit": audit,
                "_mia": mia,
                "_domias": domias,
                "_singling_out": singling,
                "_linkability": linkability,
                "_attr_inference": attr,
            }
        )
    return out


def run_grid(
    dataset: TabularDataset,
    mechanisms: Sequence[str] = tuple(MECHANISMS),
    eps_grid: Sequence[float] = DEFAULT_EPS_GRID,
    seeds: Sequence[int] = DEFAULT_SEEDS,
    delta: float = 1e-5,
    target_col: Optional[str] = None,
    corr_cols: Optional[Sequence[str]] = None,
    progress: Optional[Callable[[str], None]] = None,
    checkpoint_dir: Optional[str] = None,
) -> List[CellResult]:
    """Runs the full grid, aggregating each cell across seeds.

    Args:
        checkpoint_dir: When set, every (mechanism, eps, seed) cell is written there the
            moment it completes, and a restart skips whatever is already on disk under the
            same configuration. This grid has been lost twice — once to a MemoryError at cell
            59, once to a teardown at cell 64 — because results were only written at the end.
            Aggregation still happens only after every cell has a result, so a partial run can
            never be mistaken for a complete one.
    """
    # Flatten first: checkpointing is per (mechanism, eps, seed), and a flat list makes the
    # cell index stable across restarts as long as the grid definition is unchanged.
    cells = [
        {
            "mechanism": mech,
            "target_eps": float(eps),
            "seed": int(seed),
            "delta": float(delta),
            "dataset": dataset.name,
            "rows": dataset.num_rows,
            "target_col": target_col,
            "corr_cols": list(corr_cols) if corr_cols is not None else None,
            "pipeline": PIPELINE_VERSION,
        }
        for mech in mechanisms
        for eps in eps_grid
        for seed in seeds
    ]

    def compute(cfg: Dict[str, Any]) -> Dict[str, float]:
        out = run_cell(
            dataset,
            cfg["mechanism"],
            cfg["target_eps"],
            cfg["seed"],
            delta=cfg["delta"],
            target_col=target_col,
            corr_cols=corr_cols,
        )
        # Only JSON-serialisable scalars go to disk; artefacts stay in memory.
        serialisable: Dict[str, Any] = {
            k: v
            for k, v in out.items()
            if not k.startswith("_") and isinstance(v, (int, float, str))
        }
        return serialisable

    if checkpoint_dir is not None:
        flat = run_with_checkpoints(cells, compute, Path(checkpoint_dir), progress=progress)
    else:
        flat = []
        for cfg in cells:
            if progress:
                progress(f"  {cfg['mechanism']:<12} eps={cfg['target_eps']:<5} seed={cfg['seed']}")
            flat.append(compute(cfg))

    # Re-group into (mechanism, eps) cells, aggregating across seeds.
    by_cell: Dict[tuple, Dict[str, List[float]]] = {}
    for cfg, metrics in zip(cells, flat, strict=True):
        key = (cfg["mechanism"], cfg["target_eps"])
        raw = by_cell.setdefault(key, {})
        for k, v in metrics.items():
            raw.setdefault(k, []).append(v)

    results: List[CellResult] = []
    for mech in mechanisms:
        for eps in eps_grid:
            raw = by_cell[(mech, float(eps))]
            results.append(
                CellResult(
                    dataset=dataset.name,
                    mechanism=mech,
                    target_eps=float(eps),
                    seeds=len(seeds),
                    proved_eps=bootstrap_ci(raw["proved_eps"]),
                    audited_eps=bootstrap_ci(raw["audited_eps"]),
                    audit_p=bootstrap_ci(raw["audit_p"]),
                    tstr_f1=bootstrap_ci(raw["tstr_f1"]),
                    trtr_f1=bootstrap_ci(raw["trtr_f1"]),
                    mia_auc=bootstrap_ci(raw["mia_auc"]),
                    correlation_error=bootstrap_ci(raw["correlation_error"]),
                    structure_error_all=(
                        bootstrap_ci(raw["structure_error_all"]) if "structure_error_all" in raw else None
                    ),
                    pair_tvd=bootstrap_ci(raw["pair_tvd"]) if "pair_tvd" in raw else None,
                    usefulness_multi=(
                        bootstrap_ci(raw["usefulness_multi"]) if "usefulness_multi" in raw else None
                    ),
                    raw=raw,
                )
            )
    return results
