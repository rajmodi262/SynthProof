"""The Privacy Data Sheet -- the signed record a release ships with -- and its keyed input
fingerprint."""

import hashlib
import hmac
import json
import math
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional

import pandas as pd


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


# What the evaluation numbers in a sheet are, stated in the sheet itself. Every one of them is
# computed on the sensitive table, and none is noised. PUBLIC_RELEASE_BOUNDARY.md, D4.
EVALUATION_PRIVACY = (
    "NOT COVERED BY EPSILON: total_audited_eps, evaluation, and the utility and audit fields of "
    "frontier_curve are measured on the sensitive input table (its holdout split, and canaries "
    "planted in it). They are published as scientific measurements and are non-private "
    "statistics of that table. total_proved_eps covers the synthetic table and its size only."
)


def mechanism_events_from_spends(spends) -> List[Dict]:
    """The release's noisy steps as a compact, signable list: identical charges are merged.

    Order does not matter to composition, so merging identical (mechanism, sensitivity, scale,
    sampling) charges into one entry with summed repetitions loses nothing and keeps a
    15-column AIM release to a handful of lines.
    """
    merged: Dict[tuple, Dict] = {}
    for sp in spends:
        m = sp.mechanism
        key = (m.name, float(m.sensitivity), float(m.noise_scale), m.sampling_rate)
        if key not in merged:
            merged[key] = {
                "name": m.name,
                "sensitivity": float(m.sensitivity),
                "noise_scale": float(m.noise_scale),
                "steps": 0,
                "sampling_rate": m.sampling_rate,
            }
        merged[key]["steps"] += int(m.steps or 1)
    return list(merged.values())


@dataclass
class PrivacyDataSheet:
    """The machine-readable claim that accompanies a release.

    `signature` is populated by `synthproof.ledger.signing.sign_datasheet`. A sheet with
    `signature=None` is a record, not a proof: nothing stops a third party editing any field
    in it. `synthproof verify` checks a signed one.
    """

    dataset_name: str
    # Rows in the RELEASED synthetic table, never the input's exact count, which is private under
    # add/remove-one. `release_rows_source` says why this number is public.
    num_rows: int
    mechanism: str  # registry key — the algorithm that actually ran
    mechanism_available: bool
    delta: float
    # None on every release. The run seed replays every noise draw, so a reader holding it and
    # every other record can rebuild the release for both candidate tables and see which one
    # matches (research/release_boundary/). PUBLIC_RELEASE_BOUNDARY.md, D5.
    seed: Optional[int]
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
    # `deployment_model` is the one category from the expert-elicited DP privacy label of Dibia,
    # Lu, Bhattacharjee, Near & Feng (arXiv 2507.15997, 2025) that this sheet previously lacked.
    # Their experts stressed that the deployment model implies a materially different threat
    # model and is routinely underspecified: in the LOCAL model each record is perturbed before
    # it reaches the curator, so no trusted party ever holds the raw table; in the CENTRAL model
    # the curator does, and every epsilon here is conditional on that curator being trusted.
    # SynthProof is central-model: we read your table.
    deployment_model: str = "central"  # central | local | shuffle
    # HMAC-SHA-256 of the input table under the curator's secret key, or None without one. An
    # unkeyed hash would be a membership test (PUBLIC_RELEASE_BOUNDARY.md, D3).
    input_fingerprint: Optional[str] = None
    # How the fingerprint was computed, and a public commitment to the key. Declaring these turns
    # boundary-audit RB3 from "unverifiable" into a checkable NOTE: a reader sees the fingerprint
    # is keyed, and a signed sheet binds the producer to that claim.
    fingerprint_scheme: Optional[str] = None  # "hmac-sha256" when keyed; None when no fingerprint
    fingerprint_key_id: Optional[str] = None  # commitment to the key, not the key itself
    # Where `num_rows` came from: protocol | declared | dp_count.
    release_rows_source: str = "unknown"
    # Epsilon a dp_count size cost. Already included in total_proved_eps.
    release_rows_eps: float = 0.0
    evaluation_privacy: str = EVALUATION_PRIVACY
    # THE OPERATING RANGE OF THE EMPIRICAL MEASUREMENT. `audit_ceiling` alone is not enough:
    # this repo carries three ceiling series in two units, and quoting one where another belongs
    # is a checkable error (see audit/ceiling.py). So the estimator, the budget and the
    # confidence level travel WITH the number, and `validate_audit_reporting` refuses a release
    # that reports an audited epsilon without them.
    audit_ceiling: Optional[float] = None  # most this budget could ever certify
    audit_estimator: Optional[str] = None  # one_run | paired_cp | gdp
    audit_budget: Optional[int] = None  # canaries (m), or runs per world for gdp
    audit_alpha: Optional[float] = None  # confidence level of the reported lower bound
    preflight_findings: List[Dict] = field(default_factory=list)
    residual_risk: List[str] = field(default_factory=list)

    # `accountant_agreement` records what a SECOND, independent accountant said about the same
    # release. A grey-box audit of twelve DP libraries found thirteen guarantee violations
    # (Cebere et al., arXiv 2602.17454, 2026), so an epsilon resting on one implementation
    # rests on one implementation's bugs. The verdict is inside the signed payload precisely so
    # it cannot be stripped: a reader can tell a cross-checked release from an unchecked one.
    # `unavailable`/`unsupported` are reported rather than hidden -- an absent check must never
    # look like a passed one. See accounting/differential.py.
    accountant_agreement: Optional[Dict] = None
    # Every noisy step of the release (mechanism, sensitivity, noise scale, repetitions), signed
    # with the rest of the sheet, so boundary-audit can RECOMPUTE epsilon with both accountants
    # instead of reading the maker's own verdict above (audit C4, research/27). Noise scales are
    # data-independent calibration outputs, so publishing them reveals nothing about the input.
    mechanism_events: Optional[List[Dict]] = None

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

    def validate_audit_reporting(self) -> None:
        """Refuses a sheet that reports an audited epsilon without the instrument's reach.

        This is the enforceable half of the project's central claim. An empirical privacy
        number with no operating range is not a weaker result, it is an unreadable one: this
        project published `eps_audited = 0.000` against `eps_proved = 7.36` and read it as a
        fact about the mechanism, when 60 canaries could not have exceeded 2.97 against a
        release that was 100% verbatim training data.

        Raises:
            ValueError: naming exactly which fields are missing, and how to supply them.
        """
        if self.total_audited_eps is None:
            return
        missing = [
            name
            for name, value in (
                ("audit_ceiling", self.audit_ceiling),
                ("audit_estimator", self.audit_estimator),
                ("audit_budget", self.audit_budget),
                ("audit_alpha", self.audit_alpha),
            )
            if value is None
        ]
        if missing:
            raise ValueError(
                "this sheet reports total_audited_eps="
                f"{self.total_audited_eps} but is missing {', '.join(missing)}. An empirical "
                "privacy number cannot be interpreted without the reach of the instrument that "
                "produced it. Supply the estimator family, the budget and alpha, and derive the "
                "ceiling with synthproof.audit.ceiling.ceiling_for(estimator, budget, alpha)."
            )

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    def signing_payload(self) -> bytes:
        """Canonical bytes covered by the signature.

        Everything except the signature itself and the public key, serialised with sorted
        keys and normalized whole floats so the same sheet always produces the same bytes
        even when roundtripped across JavaScript and Python runtimes.
        """
        from synthproof.ledger.signing import canonical_sheet_payload

        return canonical_sheet_payload(self.to_dict())


# What differential privacy does NOT cover. Stated in the sheet because a reader who sees only
# an epsilon will reasonably assume it covers more than it does, and every item here has bitten
# a real deployment.
# Attacks NOT RUN on this release. LiRA is implemented as an offline audit of a mechanism
# configuration (synthproof/attacks/lira.py) -- it needs K shadow + C challenge releases per
# target -- so it is never run inside one release. Anything a release DOES run must never appear
# in this list -- see `attacks_run` below.
ATTACKS_NOT_IMPLEMENTED = ["LiRA"]

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
    "The evaluation figures -- utility, correlation error, membership-inference AUC and the "
    "audited epsilon -- are computed on the real table and are not covered by epsilon. See "
    "`evaluation_privacy`.",
]


def input_fingerprint(df: pd.DataFrame, key: bytes) -> str:
    """HMAC-SHA-256 of a table under the curator's secret key.

    The curator, holding the key, can recognise a repeat release of the same table. Nobody else
    can compute it for a candidate table, so it is no use as a membership test -- which an
    unkeyed SHA-256 of the table was, for anyone who knows every other record.
    """
    content = pd.util.hash_pandas_object(df, index=False).values.tobytes()  # type: ignore[union-attr]  # pandas-stubs: .values is ndarray for our numeric frames
    return hmac.new(key, content, hashlib.sha256).hexdigest()


def fingerprint_key_id(key: bytes) -> str:
    """A PUBLIC commitment to the fingerprint key: SHA-256 of a domain-separated tag plus the key,
    truncated. It names WHICH secret key the fingerprint is keyed under without revealing the key
    (SHA-256 is preimage-resistant), so a reader can see the fingerprint is keyed and, in a signed
    sheet, the producer is bound to that claim -- which is what turns boundary-audit RB3 from
    "unverifiable" into a checkable NOTE. It is a commitment, not a proof the fingerprint used it.
    """
    return hashlib.sha256(b"synthproof-fingerprint-key-commitment\x00" + key).hexdigest()[:16]
