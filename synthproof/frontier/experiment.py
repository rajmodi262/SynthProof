"""Multi-seed experiment runner with confidence intervals.

Every cell of the grid (dataset × mechanism × epsilon) is run over several seeds and reported
as a mean with a bootstrapped 95% interval. A single-seed number from a randomised mechanism
is not evidence, and the preregistration commits to 5 seeds per configuration.
"""

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Union

from synthproof.accounting.accountant import Accountant
from synthproof.audit.canary import AuditResult, CanaryAuditor
from synthproof.audit.steinke import SteinkeAuditor, SteinkeResult
from synthproof.data.dataset import TabularDataset
from synthproof.data.profiler import DPDomainProfiler
from synthproof.evaluate.fidelity import association_error, pairwise_tvd
from synthproof.evaluate.structure import (  # noqa: F401  (re-exported for existing callers)
    MAX_MODAL_SHARE,
    _association_matrix,
    _correlation_ratio,
    _cramers_v,
    _mean_abs_corr_error,
    informative_numeric_columns,
)
from synthproof.evaluate.utility import UtilityEvaluator
from synthproof.frontier._cell import (
    _canary_counts,
    _make_auditor,
    _nan_if_absent,
    _plan_for,
    _run_attacks,
    _run_audit,
    _split,
)
from synthproof.frontier.checkpoint import run_with_checkpoints
from synthproof.frontier.results import (  # noqa: F401  (re-exported for existing callers)
    CellResult,
    Interval,
    bootstrap_ci,
)
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


def default_target(dataset: TabularDataset, requested: Optional[str] = None) -> Optional[str]:
    """The column the utility evaluation predicts: the caller's choice, or a stated default.

    The default used to be the FIRST categorical column, which is almost never the prediction
    task: on the five demo tables it picked gender, home_ownership, contract_type,
    years_at_company and education_num, so every utility and attribute-inference number those
    releases reported was measured on a column nobody wanted to predict. The default is now
    `income` when present, else the LAST categorical column -- where the target sits in UCI
    tables and in every bundled demo. A caller who knows the task should name it.

    Raises ValueError when `requested` is not a categorical column of the table.
    """
    if requested is not None:
        if requested not in dataset.categorical_cols:
            raise ValueError(
                f"Target column {requested!r} is not a categorical column of this table "
                f"(categorical: {dataset.categorical_cols})."
            )
        return requested
    if "income" in dataset.categorical_cols:
        return "income"
    return dataset.categorical_cols[-1] if dataset.categorical_cols else None


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

    holdout_df, fit_df, fit_ds = _split(dataset, seed, holdout_frac)
    emit("split", {"fit_rows": len(fit_df), "holdout_rows": len(holdout_df)})
    if release_rows is not None and (int(release_rows) != release_rows or release_rows < 1):
        raise ValueError(f"release_rows must be a positive integer, got {release_rows!r}.")
    num_release = len(fit_df) if release_rows is None else int(release_rows)
    # The evaluators and attacks hand their seed to NumPy's legacy generator and to scikit-learn,
    # which accept only 32 bits. They draw no DP noise, so reducing the seed costs no privacy, and
    # every seed below 2**32 -- all the research grids use -- is unchanged.
    eval_seed = seed % (2**32)

    plan = _plan_for(fit_ds, target_eps, delta)
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

    auditor: Union[SteinkeAuditor, CanaryAuditor] = _make_auditor(auditor_kind, num_canaries, seed)
    aug_ds, canary_set = auditor.plant_canaries(fit_ds)
    planted, total_canaries = _canary_counts(canary_set)
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
            # What PROFILING spent, not the accountant's running total: this stage is reported
            # after the fit has also charged, so acc.total() showed the whole budget here and the
            # console read it as "domain discovery cost 1.000" when it cost 0 (declared schema).
            "eps_spent": float(profile.eps_spent),
            "eps_remaining": float(acc.budget.epsilon - profile.eps_spent),
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
    audit: Union[SteinkeResult, AuditResult] = _run_audit(
        auditor, canary_set, audit_synth, delta, emit
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
    target_col = default_target(dataset, target_col)
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

    atk = _run_attacks(
        audit_synth, util_synth, fit_ds, holdout_df, reference_df, target_col, eval_seed, emit
    )
    mia, domias, linkability = atk["mia"], atk["domias"], atk["linkability"]

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
        "usefulness_multi": (
            float(util.usefulness_multi) if util.usefulness_multi is not None else float("nan")
        ),
        "mia_auc": _nan_if_absent(mia, "auc"),
        "domias_auc": _nan_if_absent(domias, "auc"),
        "domias_tpr_at_1pct": _nan_if_absent(domias, "tpr_at_1pct_fpr"),
        "singling_out_risk": float(atk["singling"].singling_out_risk),
        "linkability_rate": _nan_if_absent(linkability, "linkability_rate"),
        "linkability_excess": _nan_if_absent(linkability, "excess_over_baseline"),
        "attr_inference_accuracy": float(atk["attr"].attack_accuracy),
        "attr_leakage_vs_conditional": float(atk["attr"].leakage_vs_conditional),
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
                "_singling_out": atk["singling"],
                "_linkability": linkability,
                "_attr_inference": atk["attr"],
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
                        bootstrap_ci(raw["structure_error_all"])
                        if "structure_error_all" in raw
                        else None
                    ),
                    pair_tvd=bootstrap_ci(raw["pair_tvd"]) if "pair_tvd" in raw else None,
                    usefulness_multi=(
                        bootstrap_ci(raw["usefulness_multi"]) if "usefulness_multi" in raw else None
                    ),
                    raw=raw,
                )
            )
    return results
