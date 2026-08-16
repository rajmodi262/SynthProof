"""Privacy Data Sheet: the artefact a release ships with.

This module is now a thin exporter over `frontier.experiment.run_cell`. It used to carry its
own copy of the plant/profile/fit/audit/evaluate loop, which drifted from the canonical one in
three ways that all corrupted published numbers:

  * it only ever instantiated `IndependentMarginalGenerator` and `GaussianMomentGenerator`,
    while labelling the former "AIM_Marginal_Generator" — so the CLI, the API and the web
    console all reported AIM for a run of independent 1-D histograms. Real AIM and the
    pairwise generator were unreachable from any user-facing entry point;
  * it had no multi-seed aggregation and no confidence intervals;
  * it defaulted the utility target to `categorical_cols[0]`, which on UCI Adult is
    `workclass` — not the benchmark's task, and near chance for every mechanism.

Mechanism names now come from the same registry the experiments use, so a data sheet cannot
name an algorithm the code did not run.
"""

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Sequence

import pandas as pd

from synthproof.audit.steinke import max_provable_epsilon
from synthproof.data.dataset import TabularDataset
from synthproof.data.preflight import enforce
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
    mechanism: str  # registry key — the algorithm that actually ran
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

    # ---- disclosure -------------------------------------------------------
    # These answer the questions a compliance reader has and the numbers above do not. They are
    # metadata about how the release was produced, not measurements, so none of them costs
    # budget.
    #
    # `domain_source` is the most important field in the sheet. A release whose column bounds
    # and category domains were read out of the sensitive table has already leaked them, and
    # every epsilon below is conditional on metadata that was never charged. Without this field
    # a reader cannot tell that case from a declared-schema release, and the two are not
    # comparable.
    domain_source: str = "unknown"  # declared | codebook | charged | inferred-nonprivate
    unit_of_privacy: str = "add/remove-one-record"
    contribution_bound: int = 1
    input_fingerprint: Optional[str] = None  # SHA-256 of the input table
    audit_ceiling: Optional[float] = None  # most this canary count could ever certify
    preflight_findings: List[Dict] = field(default_factory=list)
    residual_risk: List[str] = field(default_factory=list)

    signature: Optional[str] = None
    public_key: Optional[str] = None

    # ---- derived, for a human reader -------------------------------------

    def membership_odds(self) -> float:
        """Worst-case posterior an adversary can reach about one record's membership.

        `e^eps / (1 + e^eps)`, from a prior of 0.5. Arithmetic on an already-released
        parameter — it reads no data and costs nothing.

        Reported because epsilon alone is not interpretable: Nanayakkara et al. (USENIX
        Security 2023) found odds-based explanations beat both example-output explanations and
        descriptions that omit epsilon entirely, for non-expert comprehension of what a given
        budget actually permits.
        """
        e = math.exp(min(self.total_proved_eps, 700.0))  # guard the float, not the claim
        return e / (1.0 + e)

    def plain_statement(self) -> str:
        """One sentence a non-specialist can act on."""
        pct = 100.0 * self.membership_odds()
        return (
            f"An adversary who already knows every other record can improve a guess about "
            f"whether any one person is in this dataset from 50 in 100 to at most "
            f"{pct:.0f} in 100 (epsilon = {self.total_proved_eps:.2f}, "
            f"delta = {self.delta:g})."
        )

    def audit_is_informative(self) -> bool:
        """False when the auditor could not have detected the budget that was spent.

        An audited bound of 0 beside a ceiling below the proved epsilon says the instrument
        was too weak to see anything, not that nothing leaked. Reporting the two side by side
        is what stops that misreading.
        """
        if self.audit_ceiling is None:
            return False
        return self.audit_ceiling >= self.total_proved_eps

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


# What differential privacy does NOT cover. Stated in the sheet because a reader who sees only
# an epsilon will reasonably assume it covers more than it does, and every item here has bitten
# a real deployment.
_RESIDUAL_RISK = [
    "The guarantee is per-record. A person contributing several rows is protected proportionally "
    "less; see `contribution_bound`.",
    "It bounds what an adversary learns from THIS release. It says nothing about what they learn "
    "by combining it with another release of the same people.",
    "It does not stop correct inference about groups. Learning that a population has high "
    "prevalence of a condition is the intended output, not a leak.",
    "The signature proves the sheet is unaltered, not that the numbers are right. Anyone holding "
    "the signing key can produce a sheet saying anything.",
    "An audited epsilon of 0 means the auditor detected nothing, which is only informative if "
    "`audit_ceiling` exceeds the proved epsilon. Check `audit_is_informative()`.",
]


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
        domain_source: str = "declared",
        contribution_bound: int = 1,
        skip_preflight: bool = False,
    ) -> PrivacyDataSheet:
        """Runs one release per epsilon and returns the resulting data sheet.

        Args:
            domain_source: How the schema was obtained — `declared`, `codebook`, `charged`, or
                `inferred-nonprivate`. Recorded in the sheet, because a reader cannot otherwise
                tell a release with a public domain from one whose domain leaked.
            skip_preflight: Bypasses the refusal checks. Exists for the research grids, which
                run known benchmarks under declared schemas, and for tests. It is never the
                right setting for a release someone else will rely on.
        """
        if mechanism not in MECHANISMS:
            raise KeyError(
                f"Unknown mechanism {mechanism!r}. Available in this environment: "
                f"{sorted(MECHANISMS)}."
            )

        # Refuse before anything reads a cell. `preflight` inspects only the declared schema
        # and the row count, so this check is itself free — see synthproof/data/preflight.py
        # for why a check that reads the data would be the defect it is meant to catch.
        findings = []
        if not skip_preflight:
            findings = enforce(
                dataset.schema,
                dataset.num_rows,
                schema_declared=(domain_source != "inferred-nonprivate"),
                contribution_bound=contribution_bound,
            )

        eps_grid = list(eps_grid) if eps_grid else [0.5, 1.0, 2.0]
        ledger = ledger or Ledger(db_path=":memory:")

        if target_col is None:
            target_col = (
                "income"
                if "income" in dataset.categorical_cols
                else (dataset.categorical_cols[0] if dataset.categorical_cols else None)
            )
        if target_col is None:
            raise ValueError(
                "A data sheet needs a categorical target column for the utility evaluation."
            )

        curve: List[FrontierPoint] = []
        evaluation: Dict = {}

        for eps in eps_grid:
            res = run_cell(
                dataset,
                mechanism,
                float(eps),
                seed=self.seed,
                delta=delta,
                num_canaries=num_canaries,
                target_col=target_col,
            )

            curve.append(
                FrontierPoint(
                    target_eps=float(eps),
                    proved_eps=res["proved_eps"],
                    audited_eps=res["audited_eps"],
                    audit_p=res["audit_p"],
                    tstr_f1=res["tstr_f1"],
                    trtr_f1=res["trtr_f1"],
                    correlation_error=res["correlation_error"],
                    mia_auc=res["mia_auc"],
                )
            )
            evaluation = {
                "reference": res["reference"],
                "utility_source": res["utility_source"],
                "canary_fraction": res["canary_fraction"],
                "num_canaries": num_canaries,
            }

            ledger.append(
                LedgerEntry(
                    dataset_id=dataset.name,
                    run_id=f"{mechanism}_eps{eps}_seed{self.seed}",
                    mechanism_name=mechanism,
                    eps_spent=float(res["proved_eps"]),
                    delta=delta,
                    seed=self.seed,
                )
            )

        # A fingerprint of the exact table this release describes. Without it a sheet cannot be
        # tied to an input, so two releases of different data look interchangeable and a repeat
        # release of the SAME data cannot be detected at all — which is the first thing a
        # cross-session budget filter would need.
        fingerprint = hashlib.sha256(
            pd.util.hash_pandas_object(dataset.df, index=False).values.tobytes()
        ).hexdigest()

        last = curve[-1]
        return PrivacyDataSheet(
            domain_source=domain_source,
            contribution_bound=contribution_bound,
            input_fingerprint=fingerprint,
            audit_ceiling=max_provable_epsilon(num_canaries) if num_canaries > 1 else None,
            preflight_findings=[f.to_dict() for f in findings],
            residual_risk=_RESIDUAL_RISK,
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
