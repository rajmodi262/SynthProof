"""Pareto Privacy-Utility Frontier Engine and Privacy Data Sheet Certificate Exporter."""

import json
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional

from synthproof.accounting.accountant import Accountant
from synthproof.accounting.calibration import BudgetPlan
from synthproof.audit.canary import CanaryAuditor
from synthproof.data.dataset import TabularDataset
from synthproof.data.profiler import DPDomainProfiler
from synthproof.evaluate.utility import UtilityEvaluator
from synthproof.generators.aim import AIMGenerator
from synthproof.generators.copula import GaussianCopulaGenerator
from synthproof.ledger.ledger import Ledger
from synthproof.ledger.types import LedgerEntry


@dataclass
class FrontierPoint:
    """A single point along the Privacy-Utility frontier curve."""
    target_eps: float
    proved_eps: float
    audited_eps: float
    tstr_f1: float
    trtr_f1: float
    marginal_distance: float


@dataclass
class PrivacyDataSheet:
    """Privacy Data Sheet export artifact.

    NOT YET SIGNED. The README describes a *signed* data sheet; that is not implemented.
    `ledger_hash` is now a real hash chaining the spends recorded during this sweep
    (it previously always returned the all-zero genesis hash because nothing was ever
    appended), but the sheet itself carries no Ed25519 signature and there is no
    standalone third-party verifier. See brutal_project_audit.md, F10 / Tier 3 item 19.
    """
    dataset_name: str
    num_rows: int
    mechanism_used: str
    total_proved_eps: float
    total_audited_eps: float
    frontier_curve: List[Dict]
    ledger_hash: str
    signature: None = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


class FrontierEngine:
    """Sweeps target epsilon values to generate the Pareto Privacy-Utility curve and certificate."""

    def __init__(self, seed: int = 42):
        self.seed = seed

    def run_sweep(
        self,
        dataset: TabularDataset,
        eps_grid: Optional[List[float]] = None,
        delta: float = 1e-5,
        mechanism: str = "AIM / MST",
    ) -> PrivacyDataSheet:
        """Executes sweep across eps_grid, building frontier curve and Privacy Data Sheet."""
        if eps_grid is None:
            eps_grid = [0.5, 1.0, 2.0]
        ledger = Ledger(db_path=":memory:")
        curve_points: List[FrontierPoint] = []
        use_aim = mechanism.lower() in ("aim", "mst", "aim / mst")
        mechanism_label = "AIM_Marginal_Generator" if use_aim else "Gaussian_Copula_Generator"

        for eps in eps_grid:
            # Split the release budget across the stages that touch the data, so the
            # composed total approximates `eps` instead of exceeding it by whatever
            # profiling happened to spend (audit finding F2).
            plan = BudgetPlan.split(eps, delta=delta, profile_frac=0.1)
            # 2% headroom absorbs float slack in the calibration search; RDP composition
            # is sublinear, so the true total is at or below profile_eps + synthesis_eps.
            acc = Accountant(budget_eps=eps * 1.02, budget_delta=delta)

            auditor = CanaryAuditor(num_canaries=5, seed=self.seed)
            aug_dataset, canary_set = auditor.plant_canaries(dataset)

            # Profile the augmented table so planted canaries fall inside the domain the
            # generator can emit; profiling the original leaves the audit structurally dead.
            profiler = DPDomainProfiler(accountant=acc, eps_budget=plan.profile_eps)
            profile = profiler.profile(aug_dataset, seed=self.seed)

            gen = (AIMGenerator(seed=self.seed) if use_aim
                   else GaussianCopulaGenerator(seed=self.seed))
            gen.fit(aug_dataset, profile, acc, target_eps=plan.synthesis_eps)

            synthetic_df = gen.generate(num_samples=dataset.num_rows)

            audit_res = auditor.audit(synthetic_df, canary_set)
            proved_eps = acc.total()

            # Record the spend so ledger_hash below is a real chain head rather than
            # the genesis hash.
            ledger.append(LedgerEntry(
                dataset_id=dataset.name,
                run_id=f"frontier_eps_{eps}",
                mechanism_name=mechanism_label,
                eps_spent=float(proved_eps),
                delta=delta,
                seed=self.seed,
            ))

            target_col = (dataset.categorical_cols[0]
                          if dataset.categorical_cols else "category")
            evaluator = UtilityEvaluator(target_col=target_col)
            utility_res = evaluator.evaluate(dataset.df, synthetic_df)

            point = FrontierPoint(
                target_eps=eps,
                proved_eps=proved_eps,
                audited_eps=audit_res.audited_eps,
                tstr_f1=utility_res.tstr_macro_f1,
                trtr_f1=utility_res.trtr_macro_f1,
                marginal_distance=utility_res.marginal_distance,
            )
            curve_points.append(point)

        last_pt = curve_points[-1] if curve_points else FrontierPoint(0, 0, 0, 0, 0, 0)
        return PrivacyDataSheet(
            dataset_name=dataset.name,
            num_rows=dataset.num_rows,
            mechanism_used=mechanism_label,
            total_proved_eps=last_pt.proved_eps,
            total_audited_eps=last_pt.audited_eps,
            frontier_curve=[asdict(pt) for pt in curve_points],
            ledger_hash=ledger.get_latest_hash(),
        )
