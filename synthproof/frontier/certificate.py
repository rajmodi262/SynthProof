"""Privacy Data Sheet: the artefact a release ships with.

This module is now a thin exporter over `frontier.experiment.run_cell`. It used to carry its
own copy of the plant/profile/fit/audit/evaluate loop, which drifted from the canonical one in
three ways that all corrupted published numbers:

  * it only ever instantiated `IndependentMarginalGenerator` and `GaussianCopulaGenerator`,
    while labelling the former "AIM_Marginal_Generator" — so the CLI, the API and the web
    console all reported AIM for a run of independent 1-D histograms. Real AIM and the
    pairwise generator were unreachable from any user-facing entry point;
  * it had no multi-seed aggregation and no confidence intervals;
  * it defaulted the utility target to `categorical_cols[0]`, which on UCI Adult is
    `workclass` — not the benchmark's task, and near chance for every mechanism.

Mechanism names now come from the same registry the experiments use, so a data sheet cannot
name an algorithm the code did not run.
"""

import json
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Sequence

from synthproof.data.dataset import TabularDataset
from synthproof.frontier.experiment import MECHANISMS, run_cell
from synthproof.ledger.ledger import Ledger
from synthproof.ledger.types import LedgerEntry


@dataclass
class FrontierPoint:
    """A single point along the privacy-utility frontier."""

    target_eps: float
    proved_eps: float
    audited_eps: float
    audit_p: float
    tstr_f1: float
    trtr_f1: float
    correlation_error: float
    mia_auc: float


@dataclass
class PrivacyDataSheet:
    """The machine-readable claim that accompanies a release.

    `signature` is populated by `synthproof.ledger.signing.sign_datasheet`. A sheet with
    `signature=None` is a record, not a proof: nothing stops a third party editing any field
    in it. `synthproof verify` checks a signed one.
    """

    dataset_name: str
    num_rows: int
    mechanism: str                 # registry key — the algorithm that actually ran
    mechanism_available: bool
    delta: float
    seed: int
    target_column: str
    total_proved_eps: float
    total_audited_eps: float
    frontier_curve: List[Dict]
    ledger_hash: str
    evaluation: Dict = field(default_factory=dict)
    attacks_run: List[str] = field(default_factory=list)
    attacks_not_implemented: List[str] = field(default_factory=list)
    signature: Optional[str] = None
    public_key: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    def signing_payload(self) -> bytes:
        """Canonical bytes covered by the signature.

        Everything except the signature itself and the public key, serialised with sorted
        keys so the same sheet always produces the same bytes.
        """
        d = self.to_dict()
        d.pop("signature", None)
        d.pop("public_key", None)
        return json.dumps(d, sort_keys=True, separators=(",", ":")).encode("utf-8")


class FrontierEngine:
    """Sweeps epsilon and exports a Privacy Data Sheet."""

    def __init__(self, seed: int = 42):
        self.seed = seed

    def run_sweep(
        self,
        dataset: TabularDataset,
        eps_grid: Optional[Sequence[float]] = None,
        delta: float = 1e-5,
        mechanism: str = "pairwise",
        target_col: Optional[str] = None,
        num_canaries: int = 30,
        ledger: Optional[Ledger] = None,
    ) -> PrivacyDataSheet:
        """Runs one release per epsilon and returns the resulting data sheet."""
        if mechanism not in MECHANISMS:
            raise KeyError(
                f"Unknown mechanism {mechanism!r}. Available in this environment: "
                f"{sorted(MECHANISMS)}."
            )

        eps_grid = list(eps_grid) if eps_grid else [0.5, 1.0, 2.0]
        ledger = ledger or Ledger(db_path=":memory:")

        if target_col is None:
            target_col = ("income" if "income" in dataset.categorical_cols
                          else (dataset.categorical_cols[0]
                                if dataset.categorical_cols else None))
        if target_col is None:
            raise ValueError(
                "A data sheet needs a categorical target column for the utility evaluation."
            )

        curve: List[FrontierPoint] = []
        evaluation: Dict = {}

        for eps in eps_grid:
            res = run_cell(dataset, mechanism, float(eps), seed=self.seed, delta=delta,
                           num_canaries=num_canaries, target_col=target_col)

            curve.append(FrontierPoint(
                target_eps=float(eps),
                proved_eps=res["proved_eps"],
                audited_eps=res["audited_eps"],
                audit_p=res["audit_p"],
                tstr_f1=res["tstr_f1"],
                trtr_f1=res["trtr_f1"],
                correlation_error=res["correlation_error"],
                mia_auc=res["mia_auc"],
            ))
            evaluation = {
                "reference": res["reference"],
                "utility_source": res["utility_source"],
                "canary_fraction": res["canary_fraction"],
                "num_canaries": num_canaries,
            }

            ledger.append(LedgerEntry(
                dataset_id=dataset.name,
                run_id=f"{mechanism}_eps{eps}_seed{self.seed}",
                mechanism_name=mechanism,
                eps_spent=float(res["proved_eps"]),
                delta=delta,
                seed=self.seed,
            ))

        last = curve[-1]
        return PrivacyDataSheet(
            dataset_name=dataset.name,
            num_rows=dataset.num_rows,
            mechanism=mechanism,
            mechanism_available=mechanism in MECHANISMS,
            delta=delta,
            seed=self.seed,
            target_column=target_col,
            total_proved_eps=last.proved_eps,
            total_audited_eps=last.audited_eps,
            frontier_curve=[asdict(p) for p in curve],
            ledger_hash=ledger.get_latest_hash(),
            evaluation=evaluation,
            attacks_run=["canary_audit", "distance_mia"],
            attacks_not_implemented=["LiRA", "DOMIAS", "attribute_inference"],
        )
