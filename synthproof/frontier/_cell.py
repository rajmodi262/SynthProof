"""The stages of one experiment cell -- split, budget plan, auditor, audit, attacks -- used by
`run_cell`."""

from typing import Any, Dict, Tuple

import numpy as np

from synthproof.accounting.accountant import Accountant
from synthproof.accounting.calibration import BudgetPlan
from synthproof.attacks.attribute_inference import AttributeInferenceAttack
from synthproof.attacks.distance_mia import DistanceMIABaseline
from synthproof.attacks.domias import DOMIAS
from synthproof.attacks.exact_match_risk import ExactMatchRiskEvaluator
from synthproof.attacks.linkability import LinkabilityEvaluator
from synthproof.audit.canary import CanaryAuditor, CanarySet
from synthproof.audit.steinke import OneRunCanarySet, SteinkeAuditor
from synthproof.data.dataset import TabularDataset
from synthproof.data.profiler import DPDomainProfiler
from synthproof.evaluate.structure import (  # noqa: F401  (re-exported for existing callers)
    MAX_MODAL_SHARE,
    _association_matrix,
    _correlation_ratio,
    _cramers_v,
    _mean_abs_corr_error,
    informative_numeric_columns,
)


def _split(dataset: TabularDataset, seed: int, holdout_frac: float):
    """A seeded fit/holdout split. Returns (holdout_df, fit_df, fit_ds)."""
    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(dataset.df))
    n_hold = max(20, int(len(idx) * holdout_frac))
    holdout_df = dataset.df.iloc[idx[:n_hold]].reset_index(drop=True)
    fit_df = dataset.df.iloc[idx[n_hold:]].reset_index(drop=True)
    return holdout_df, fit_df, TabularDataset(fit_df, name=dataset.name, schema=dataset.schema)


def _plan_for(fit_ds: TabularDataset, target_eps: float, delta: float) -> BudgetPlan:
    """Profiling is free when the schema declares every bound and category domain (true of every
    registry dataset): it then reads nothing and charges nothing, so the WHOLE budget goes to
    synthesis. Reserving 10% for a profiler that spends none of it left that share idle (audit
    H1, research/27). Only a schema with undeclared domains gets the 10/90 split."""
    needs_profile = (
        DPDomainProfiler(
            accountant=Accountant(budget_eps=float("inf"), budget_delta=delta), eps_budget=1.0
        )._query_count(fit_ds)
        > 0
    )
    if needs_profile:
        return BudgetPlan.split(target_eps, delta=delta, profile_frac=0.1)
    return BudgetPlan(total_eps=target_eps, delta=delta, profile_eps=0.0, synthesis_eps=target_eps)


def _make_auditor(auditor_kind: str, num_canaries: int, seed: int):
    """The one-run construction is the default: it spends one canary per comparison rather
    than two, and is measurably more sensitive to PARTIAL leakage, which is the regime a
    real mechanism lives in. See results/AUDITOR_COMPARISON.md. The paired auditor stays
    selectable so the two can be compared on identical runs."""
    if auditor_kind == "one_run":
        return SteinkeAuditor(num_canaries=num_canaries, seed=seed)
    if auditor_kind == "paired":
        return CanaryAuditor(num_canaries=num_canaries, seed=seed)
    raise ValueError(f"Unknown auditor {auditor_kind!r}. Use 'one_run' or 'paired'.")


def _canary_counts(canary_set) -> Tuple[int, int]:
    """(planted, total). Report what was actually planted, not what was requested. Narrowing on
    the SET rather than on the auditor is what lets the field accesses be checked."""
    if isinstance(canary_set, OneRunCanarySet):
        return canary_set.num_included, len(canary_set.canaries)
    return len(canary_set.members), len(canary_set.members) + len(canary_set.holdout)


def _run_audit(auditor, canary_set, audit_synth, delta: float, emit):
    """The two auditors return different result types -- SteinkeResult carries the ceiling,
    accuracy and saturation flag; AuditResult carries the TPR/FPR pair from the paired
    construction. Branching on the auditor's type rather than on a string keeps the two
    sets of field accesses provably matched to the object that produced them."""
    if isinstance(auditor, SteinkeAuditor) and isinstance(canary_set, OneRunCanarySet):
        res = auditor.audit(audit_synth, canary_set, delta=delta)
        emit(
            "audit",
            {
                "audited_eps": float(res.audited_eps),
                "ceiling": float(res.ceiling),
                "accuracy": float(res.accuracy),
                "guesses": int(res.guesses),
                "saturated": bool(res.saturated),
                "p_value": float(res.p_value),
            },
        )
        return res
    if isinstance(auditor, CanaryAuditor) and isinstance(canary_set, CanarySet):
        paired = auditor.audit(audit_synth, canary_set)
        emit(
            "audit",
            {
                "audited_eps": float(paired.audited_eps),
                "tpr": float(paired.tpr),
                "fpr": float(paired.fpr),
                "p_value": float(paired.p_value),
            },
        )
        return paired
    raise TypeError(  # pragma: no cover - the two constructors cannot produce a mixed pair
        f"Auditor {type(auditor).__name__} produced a "
        f"{type(canary_set).__name__}, which it should not be able to."
    )


def _run_attacks(audit_synth, util_synth, fit_ds, holdout_df, reference_df, target_col, seed, emit):
    """Every attack the release is scored against. Returns them by name; an attack that does not
    apply to this table is None and reported as NOT APPLICABLE, never as a passed attack.

    The MIA runs against the AUDIT release: it asks whether training membership is recoverable,
    which is a question about the release that actually contained the members. The distance MIA
    counts categorical mismatches (audit C3), so it runs on every table. DOMIAS still needs a
    numeric column for its density estimate; on an all-categorical release (Mushroom, Nursery)
    it is reported as NOT APPLICABLE, the same rule linkability follows.
    """
    out: Dict[str, Any] = {}
    try:
        out["mia"] = DistanceMIABaseline(seed=seed, max_records=400).evaluate(
            audit_synth, train_df=fit_ds.df, test_df=holdout_df
        )
        emit(
            "attack",
            {
                "auc": float(out["mia"].auc),
                "advantage": float(out["mia"].advantage),
                "tpr_at_1pct_fpr": float(out["mia"].tpr_at_1pct_fpr),
            },
        )
    except ValueError as exc:
        out["mia"] = None
        emit("attack", {"not_applicable": str(exc)})

    # A second, structurally different adversary. The two fail differently -- the baseline is
    # a raw proximity heuristic, DOMIAS divides by a reference density to remove the
    # typicality confound -- so both are reported rather than one standing in for the other.
    try:
        out["domias"] = DOMIAS(seed=seed, max_records=400).evaluate(
            audit_synth, train_df=fit_ds.df, test_df=holdout_df
        )
        emit(
            "attack_domias",
            {
                "auc": float(out["domias"].auc),
                "tpr_at_1pct_fpr": float(out["domias"].tpr_at_1pct_fpr),
            },
        )
    except ValueError as exc:
        out["domias"] = None
        emit("attack_domias", {"not_applicable": str(exc)})

    # Singling out: does any real record appear in the release as a unique exact match? This
    # is the one risk of the EDPB's three that a release can fail outright rather than by
    # degree, so it is cheap and worth running on every cell. Scored against the AUDIT release
    # for the same reason the MIA is -- that is the release that contained the members.
    out["singling"] = ExactMatchRiskEvaluator(seed=seed, max_records=400).evaluate(
        audit_synth, target_df=fit_ds.df
    )
    emit(
        "attack_singling_out",
        {
            "risk": float(out["singling"].singling_out_risk),
            "unique_matches": int(out["singling"].num_unique_matches),
        },
    )

    # Linkability: the third EDPB risk. Two disjoint halves of a record are matched to the
    # release independently; agreement beyond the shuffled-release baseline is the link. A table
    # with fewer than four columns cannot be split into two disjoint halves, so the question does
    # not arise: NOT APPLICABLE, not a failure, and it must not take the release down with it.
    try:
        out["linkability"] = LinkabilityEvaluator(seed=seed, max_records=400).evaluate(
            audit_synth, target_df=fit_ds.df
        )
        emit(
            "attack_linkability",
            {
                "rate": float(out["linkability"].linkability_rate),
                "excess_over_baseline": float(out["linkability"].excess_over_baseline),
            },
        )
    except ValueError as exc:
        out["linkability"] = None
        emit("attack_linkability", {"not_applicable": str(exc)})

    # Attribute inference, scored against a CONDITIONAL baseline rather than a marginal one.
    # Jayaraman & Evans (CCS 2022) showed that reporting raw attack accuracy as "leakage"
    # mostly measures imputability; `leakage_vs_conditional` is the number that isolates what
    # the release itself contributed. Uses the canary-free release, because this asks what a
    # recipient of the published table can infer.
    out["attr"] = AttributeInferenceAttack(
        target_column=target_col, seed=seed, max_records=400
    ).evaluate(util_synth, target_df=fit_ds.df, reference_df=reference_df)
    emit(
        "attack_attribute_inference",
        {
            "accuracy": float(out["attr"].attack_accuracy),
            "leakage_vs_conditional": float(out["attr"].leakage_vs_conditional),
        },
    )
    return out


def _nan_if_absent(result, attr: str) -> float:
    """NaN, not 0.0, when an attack does not apply: a zero would read as 'attack ran, found
    nothing' -- an absent measurement, not a null."""
    return float(getattr(result, attr)) if result else float("nan")
