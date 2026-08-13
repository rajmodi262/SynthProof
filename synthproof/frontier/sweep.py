"""Experiment execution sweep runner.

IMPORTANT — read before citing any number this produces:
  * The default dataset is a 100-row TOY table whose columns are drawn INDEPENDENTLY.
    There is no joint structure for a synthesiser to preserve, so utility numbers from
    this sweep measure almost nothing.
  * A single seed is used. The preregistration commits to 5 seeds on UCI Adult and
    ACSIncome.
  * This sweep therefore does NOT execute the preregistered protocol. See
    docs/preregistration.md and brutal_project_audit.md (F9).
"""

from dataclasses import dataclass
from typing import List

import numpy as np

from synthproof.accounting.accountant import Accountant
from synthproof.accounting.calibration import BudgetPlan
from synthproof.attacks.distance_mia import DistanceMIABaseline
from synthproof.attacks.exact_match_risk import ExactMatchRiskEvaluator
from synthproof.audit.canary import CanaryAuditor
from synthproof.data.dataset import TabularDataset
from synthproof.data.profiler import DPDomainProfiler
from synthproof.evaluate.utility import UtilityEvaluator
from synthproof.generators.aim import AIMGenerator
from synthproof.generators.copula import GaussianCopulaGenerator


@dataclass
class SweepRowResult:
    """One experimental cell. Every field is measured; none are assumed."""

    dataset_name: str
    mechanism_name: str
    target_eps: float
    proved_eps: float
    audited_eps: float
    audit_p_value: float
    tstr_f1: float
    trtr_f1: float
    singling_out_risk: float
    mia_auc: float
    mia_advantage: float


class SweepRunner:
    """Orchestrates experimental sweeps across datasets, mechanisms, and privacy budgets."""

    def __init__(self, seed: int = 42, holdout_frac: float = 0.3):
        self.seed = seed
        self.holdout_frac = holdout_frac

    def _split(self, dataset: TabularDataset):
        """Splits into a fitting set and a true non-member holdout for the MIA."""
        rng = np.random.default_rng(self.seed)
        idx = rng.permutation(len(dataset.df))
        n_hold = max(5, int(len(idx) * self.holdout_frac))
        holdout_df = dataset.df.iloc[idx[:n_hold]].reset_index(drop=True)
        fit_df = dataset.df.iloc[idx[n_hold:]].reset_index(drop=True)
        return (
            TabularDataset(df=fit_df, name=dataset.name),
            holdout_df,
        )

    def run_cell(
        self,
        dataset: TabularDataset,
        mechanism_name: str,
        target_eps: float,
        delta: float = 1e-5,
    ) -> SweepRowResult:
        """Executes a single experimental sweep cell."""
        np.random.seed(self.seed)

        # The generator only ever sees fit_ds. holdout_df are genuine non-members, which
        # is what makes the membership inference result interpretable. (The previous
        # version fit on the full table and then compared its first half against its
        # second half — both were members, so the attack could not have worked.)
        fit_ds, holdout_df = self._split(dataset)

        # One budget for the whole release, split across the stages that read the data.
        plan = BudgetPlan.split(target_eps, delta=delta, profile_frac=0.1)
        acc = Accountant(budget_eps=target_eps * 1.02, budget_delta=delta)

        auditor = CanaryAuditor(num_canaries=5, seed=self.seed)
        aug_dataset, canary_set = auditor.plant_canaries(fit_ds)

        # Profile the augmented table so planted canaries are inside the domain the
        # generator can actually emit; otherwise the audit is structurally dead.
        profiler = DPDomainProfiler(accountant=acc, eps_budget=plan.profile_eps)
        profile = profiler.profile(aug_dataset, seed=self.seed)

        if mechanism_name.lower() in ("aim", "mst", "aim / mst"):
            gen = AIMGenerator(seed=self.seed)
        else:
            gen = GaussianCopulaGenerator(seed=self.seed)

        gen.fit(aug_dataset, profile, acc, target_eps=plan.synthesis_eps)
        synthetic_df = gen.generate(num_samples=dataset.num_rows)

        audit_res = auditor.audit(synthetic_df, canary_set)
        proved_eps = float(acc.total())

        target_col = dataset.categorical_cols[0] if dataset.categorical_cols else "category"
        utility_res = UtilityEvaluator(target_col=target_col, seed=self.seed).evaluate(
            dataset.df, synthetic_df
        )

        risk_res = ExactMatchRiskEvaluator(seed=self.seed).evaluate(synthetic_df, dataset.df)

        mia_res = DistanceMIABaseline(seed=self.seed).evaluate(
            synthetic_df, train_df=fit_ds.df, test_df=holdout_df
        )

        return SweepRowResult(
            dataset_name=dataset.name,
            mechanism_name=mechanism_name,
            target_eps=target_eps,
            proved_eps=proved_eps,
            audited_eps=audit_res.audited_eps,
            audit_p_value=audit_res.p_value,
            tstr_f1=utility_res.tstr_macro_f1,
            trtr_f1=utility_res.trtr_macro_f1,
            singling_out_risk=risk_res.singling_out_risk,
            mia_auc=mia_res.auc,
            mia_advantage=mia_res.advantage,
        )

    def run_full_sweep(self) -> List[SweepRowResult]:
        """Runs the sweep over the toy benchmark. See the module docstring for caveats."""
        dataset = TabularDataset.create_synthetic_toy(num_rows=100, seed=self.seed)
        results = []

        eps_grid = [0.5, 1.0, 2.0, 4.0, 8.0]
        mechanisms = ["AIM / MST", "Gaussian Copula"]

        for mech in mechanisms:
            for eps in eps_grid:
                results.append(self.run_cell(dataset, mech, eps))

        return results
