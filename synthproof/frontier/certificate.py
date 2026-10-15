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

import functools
import secrets
from dataclasses import asdict
from typing import Callable, Dict, List, Optional, ParamSpec, Sequence, TypeVar

import pandas as pd

from synthproof.accounting.differential import (
    cross_check_spends,
)
from synthproof.accounting.differential import (
    enforce as enforce_accountant_agreement,  # `enforce` is taken by preflight
)
from synthproof.accounting.noise import exact_noise
from synthproof.audit.ceiling import ceiling_for
from synthproof.audit.steinke import DEFAULT_ALPHA
from synthproof.data.dataset import TabularDataset
from synthproof.data.preflight import enforce
from synthproof.frontier.experiment import MECHANISMS, default_target, run_cell
from synthproof.frontier.release_size import DP_COUNT_FRAC, declared, dp_count
from synthproof.frontier.sheet import (  # noqa: F401  (re-exported for existing callers)
    _RESIDUAL_RISK,
    ATTACKS_NOT_IMPLEMENTED,
    EVALUATION_PRIVACY,
    FrontierPoint,
    PrivacyDataSheet,
    fingerprint_key_id,
    input_fingerprint,
    mechanism_events_from_spends,
)
from synthproof.ledger.ledger import Ledger
from synthproof.ledger.types import LedgerEntry

_P = ParamSpec("_P")
_R = TypeVar("_R")


def _with_exact_noise(fn: Callable[_P, _R]) -> Callable[_P, _R]:
    """Runs a release with the exact-arithmetic CKS'20 samplers (accounting/noise.py).

    A release is what leaves the curator, so it gets the sampler whose decisions involve no
    floating point. The research grids call run_cell directly and keep the float sampler, so
    their committed numbers stay reproducible.
    """

    @functools.wraps(fn)
    def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _R:
        with exact_noise():
            return fn(*args, **kwargs)

    return wrapper


class FrontierEngine:
    """Sweeps epsilon and exports a Privacy Data Sheet."""

    def __init__(self, seed: Optional[int] = None):
        # Omitted, the seed is drawn from the OS and never leaves this object. A default anyone
        # can read in the source (it used to be 42) is a published seed. 63 bits keeps it a
        # valid signed 64-bit integer wherever a library stores one.
        self.seed = seed if seed is not None else secrets.randbits(63)
        # Populated only when `run_sweep(retain_release=True)`. None means "not retained",
        # which is not the same as "the release was empty" -- callers must check.
        self.last_release: Optional[pd.DataFrame] = None

    @_with_exact_noise
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
        retain_release: bool = False,
        release_rows: Optional[int] = None,
        fingerprint_key: Optional[bytes] = None,
    ) -> PrivacyDataSheet:
        """Runs one release per epsilon and returns the resulting data sheet.

        Args:
            domain_source: How the schema was obtained — `declared`, `codebook`, `charged`, or
                `inferred-nonprivate`. Recorded in the sheet, because a reader cannot otherwise
                tell a release with a public domain from one whose domain leaked.
            skip_preflight: Bypasses the refusal checks. Exists for the research grids, which
                run known benchmarks under declared schemas, and for tests. It is never the
                right setting for a release someone else will rely on.
            retain_release: Keeps the synthetic table from the LAST epsilon on
                `self.last_release`, so a caller can write out the data the sheet describes.
                Off by default: the grids sweep many epsilons and holding each release would
                retain memory they have no use for, which is why the artefacts are otherwise
                read once and dropped. `last_release` is the canary-free utility release --
                the audit release is trained on planted canaries and must never be shipped.
            release_rows: The PUBLIC number of rows to release, declared before the data is
                read. None spends `DP_COUNT_FRAC` of the smallest epsilon on a noisy count
                instead, taken out of each release's budget and included in every proved
                epsilon. The exact row count is never used: under add/remove-one it is
                private (PUBLIC_RELEASE_BOUNDARY.md, D2).
            fingerprint_key: The curator's secret for `input_fingerprint`, from
                `signing.load_fingerprint_key`. None omits the field (D3).
        """
        if mechanism not in MECHANISMS:
            raise KeyError(
                f"Unknown mechanism {mechanism!r}. Available in this environment: "
                f"{sorted(MECHANISMS)}."
            )

        # Refuse before anything reads a cell. `preflight` inspects only the declared schema
        # and the row count, so this check is itself free — see synthproof/data/preflight.py
        # for why a check that reads the data would be the defect it is meant to catch.
        eps_grid = list(eps_grid) if eps_grid else [0.5, 1.0, 2.0]

        # The size every artefact reports and the gate judges. Never `dataset.num_rows`: under
        # add/remove-one that is private, and a refusal near the 500-row floor would announce it.
        # A dp_count is spent before the gate runs, so a refused input has still paid for it.
        if release_rows is not None:
            size = declared(release_rows)
        else:
            count_eps = DP_COUNT_FRAC * min(float(e) for e in eps_grid)
            size = dp_count(dataset.num_rows, count_eps, seed=self.seed)

        findings = []
        if not skip_preflight:
            findings = enforce(
                dataset.schema,
                size.rows,
                schema_declared=(domain_source != "inferred-nonprivate"),
                contribution_bound=contribution_bound,
            )
        ledger = ledger or Ledger(db_path=":memory:")

        target_col = default_target(dataset, target_col)
        if target_col is None:
            raise ValueError(
                "A data sheet needs a categorical target column for the utility evaluation."
            )

        curve: List[FrontierPoint] = []
        evaluation: Dict = {}
        self.last_release = None

        for eps in eps_grid:
            res = run_cell(
                dataset,
                mechanism,
                # A charged count comes out of this release's budget, so the total never exceeds
                # the epsilon that was asked for. It is pure eps-DP and composes basically.
                float(eps) - size.eps,
                seed=self.seed,
                release_rows=size.rows,
                delta=delta,
                num_canaries=num_canaries,
                target_col=target_col,
                # Needed for `_spends`: the differential accountant cross-checks the charges
                # this release actually made, not a reconstruction of them. The artefacts are
                # read once below and never retained.
                return_artifacts=True,
            )

            if retain_release:
                # `_synth`, never `_audit_synth`. The audit release is fitted on a split with
                # canaries planted in it; shipping it would release the canaries themselves.
                self.last_release = res["_synth"]

            curve.append(
                FrontierPoint(
                    target_eps=float(eps),
                    proved_eps=res["proved_eps"] + size.eps,
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

            # Ask a second, independent accountant about the release we just composed, from
            # the charges actually recorded rather than from a reconstruction. `enforce`
            # raises only on under-reporting; a conservative gap or an unavailable second
            # accountant is reported on the certificate, not hidden.
            # Derived from the artefacts this run produced, never hardcoded. The previous
            # version listed DOMIAS and attribute inference as NOT IMPLEMENTED while
            # `run_cell` was running both -- a false statement inside a signed payload, and
            # the mirror image of audit finding G1 (the console that hardcoded four PASSED
            # verdicts). A list that does not read the run will drift from it.
            attacks_run = ["canary_audit"] + [
                name
                for key, name in (
                    ("_mia", "distance_mia"),
                    ("_domias", "domias"),
                    ("_singling_out", "exact_match_risk"),
                    ("_linkability", "linkability"),
                    ("_attr_inference", "attribute_inference"),
                )
                if res.get(key) is not None
            ]

            agreement = enforce_accountant_agreement(
                cross_check_spends(res.get("_spends", []), delta)
            )
            events = mechanism_events_from_spends(res.get("_spends", []))

            ledger.append(
                LedgerEntry(
                    dataset_id=dataset.name,
                    run_id=f"{mechanism}_eps{eps}_seed{self.seed}",
                    mechanism_name=mechanism,
                    eps_spent=float(res["proved_eps"]) + size.eps,
                    delta=delta,
                    seed=self.seed,
                )
            )

        # A fingerprint of the exact table this release describes. Without it a sheet cannot be
        # tied to an input, so two releases of different data look interchangeable and a repeat
        # release of the SAME data cannot be detected at all — which is the first thing a
        # cross-session budget filter would need.
        # Keyed, because a plain hash is a membership test for anyone who knows the other records.
        fingerprint = (
            input_fingerprint(dataset.df, fingerprint_key) if fingerprint_key is not None else None
        )

        last = curve[-1]
        return PrivacyDataSheet(
            domain_source=domain_source,
            contribution_bound=contribution_bound,
            input_fingerprint=fingerprint,
            fingerprint_scheme=("hmac-sha256" if fingerprint_key is not None else None),
            fingerprint_key_id=(
                fingerprint_key_id(fingerprint_key) if fingerprint_key is not None else None
            ),
            audit_ceiling=(
                ceiling_for("one_run", num_canaries).value if num_canaries > 1 else None
            ),
            audit_estimator="one_run" if num_canaries > 1 else None,
            audit_budget=num_canaries if num_canaries > 1 else None,
            audit_alpha=DEFAULT_ALPHA if num_canaries > 1 else None,
            preflight_findings=[f.to_dict() for f in findings],
            residual_risk=_RESIDUAL_RISK,
            accountant_agreement=agreement.to_dict(),
            mechanism_events=events,
            dataset_name=dataset.name,
            num_rows=size.rows,
            release_rows_source=size.source,
            release_rows_eps=size.eps,
            mechanism=mechanism,
            mechanism_available=mechanism in MECHANISMS,
            delta=delta,
            seed=None,  # withheld: it replays every noise draw (D5)
            target_column=target_col,
            total_proved_eps=last.proved_eps,
            total_audited_eps=last.audited_eps,
            frontier_curve=[asdict(p) for p in curve],
            ledger_hash=ledger.get_latest_hash(),
            evaluation=evaluation,
            attacks_run=attacks_run,
            attacks_not_implemented=ATTACKS_NOT_IMPLEMENTED,
        )
