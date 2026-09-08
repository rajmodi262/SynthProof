"""Classify a published empirical-privacy claim by the reach of the instrument that produced it.

THE QUESTION. A paper reports an empirical epsilon -- or reports that no leakage was detected --
for a mechanism with a stated analytic bound. Could its instrument have detected that bound at
all? With `m` canaries at confidence `alpha`, a *perfect* adversary cannot push the reported
lower bound above `eps_max(m)`. If that ceiling sits below the mechanism's proved epsilon, a null
result is the instrument reading its own floor, and says nothing about the mechanism.

This module is pure arithmetic over an extraction table. It does no fetching, no parsing and no
inference: everything it needs was read out of the papers by hand, under
`docs/CEILING_SURVEY_PROTOCOL.md`, which was frozen and committed before any paper was read.

WHAT IS NOT OURS. The ceiling is a corollary of Steinke, Nasr & Jagielski (2023) Thm 2.1 / Eq.
(3); Keinan, Shenfeld & Ligett (arXiv:2503.07199, NeurIPS 2025) Thm 5.2 formalise the one-run
case; and the concept is already named **"maximum auditable epsilon"** by Annamalai, Ganev &
De Cristofaro (USENIX Security 2024, arXiv:2405.10994) S2.2, who compute it numerically in S7.5
**for their own configuration only**. Applying it per-paper across the literature is the part
that is ours.

WHY THE VALIDATION IS SO STRICT. A table like this is only as credible as its provenance. Two
rules from the protocol are enforced in code rather than trusted to discipline: every value needs
a locator, and a row whose estimator family could not be READ is EXCLUDED rather than guessed --
three ceiling series live in this repo, in two units, and applying the wrong one is an error an
examiner can catch by recomputing a single cell.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from synthproof.audit.ceiling import ESTIMATORS, ceiling_for

__all__ = [
    "NOT_REPORTED",
    "Row",
    "Classified",
    "Summary",
    "classify",
    "classify_all",
    "summarise",
    "wilson_interval",
]

#: The literal an extractor writes when a paper does not state a value. Distinguishing "absent"
#: from "we did not look" is the whole point of the NOT REPORTED class, so it is a sentinel
#: rather than `None`.
NOT_REPORTED = "NOT REPORTED"

_CLASSES = ("UNDERPOWERED", "SATURATED", "INTERPRETABLE", "NOT REPORTED", "EXCLUDED")


class ProtocolViolation(ValueError):
    """Raised when a row breaks a rule fixed in the pre-registered protocol."""


@dataclass(frozen=True)
class Row:
    """One extracted configuration. Fields mirror protocol S4 exactly.

    A value is either a real number/string **with a locator**, or the sentinel `NOT_REPORTED`.
    """

    paper_id: str
    config_label: str
    estimator_family: str  # one_run | paired_cp | gdp | other | NOT REPORTED
    budget: Optional[int]
    alpha: Optional[float]
    eps_emp: Optional[float]
    emp_unit: str  # epsilon | mu
    eps_proved: Optional[float]
    proved_unit: str  # epsilon | mu
    acknowledged_limit: str  # yes | no | NOT REPORTED
    extractor: str
    source_depth: str  # full text | abstract only | could not obtain
    locators: Dict[str, str] = field(default_factory=dict)
    notes: str = ""
    # Protocol amendment A1. The first extraction pass is by machine, which does NOT satisfy S6's
    # two-human requirement. A row is worthless until someone has read the source themselves, so
    # this gates K in code rather than in a reviewer's memory.
    verified_by_human: bool = False

    def validate(self) -> None:
        """Enforce the protocol rules that are cheap to break and expensive to discover."""
        if not self.paper_id:
            raise ProtocolViolation("paper_id is required")
        if self.acknowledged_limit not in ("yes", "no", NOT_REPORTED):
            raise ProtocolViolation(
                f"{self.paper_id}: acknowledged_limit must be 'yes', 'no' or {NOT_REPORTED!r}; "
                f"got {self.acknowledged_limit!r}. Whether the paper disclosed its own limit "
                f"decides whether it counts toward K (protocol S8)."
            )
        # A unit is only meaningful when there is a value to carry it. Papers in the frame that
        # report no empirical privacy quantity at all are a real and expected case -- they land
        # in NOT REPORTED, which is one of the results this survey exists to produce -- and
        # demanding "epsilon" or "mu" from them would force an extractor to invent one.
        for unit_name, unit, value in (
            ("emp_unit", self.emp_unit, self.eps_emp),
            ("proved_unit", self.proved_unit, self.eps_proved),
        ):
            if value is not None and unit not in ("epsilon", "mu"):
                raise ProtocolViolation(
                    f"{self.paper_id}: {unit_name} must be 'epsilon' or 'mu' when "
                    f"{unit_name.replace('_unit', '')} has a value; got {unit!r}"
                )
        # Protocol S4: a number without a locator is not admissible.
        # A locator key may cover more than one field -- "eps_emp and eps_proved: Section 6,
        # Figure 7" is a perfectly good citation for both, and refusing it would push extractors
        # toward duplicating the same reference rather than toward citing more carefully. So the
        # test is that SOME key names this field, not that a key equals it exactly.
        located = {k.lower() for k in self.locators}
        for name in ("budget", "alpha", "eps_emp", "eps_proved"):
            if getattr(self, name) is not None and not any(name in k for k in located):
                raise ProtocolViolation(
                    f"{self.paper_id}: {name} has a value but no locator. Protocol S4: a number "
                    f"without a section/table/figure/page reference is not admissible. Add "
                    f"locators[{name!r}], or set the value to None and record {NOT_REPORTED}."
                )


@dataclass(frozen=True)
class Classified:
    row: Row
    klass: str
    ceiling: Optional[float]
    ceiling_unit: Optional[str]
    reason: str

    @property
    def counts_toward_k(self) -> bool:
        """Protocol S8 + amendment A1.

        K counts underpowered papers that did NOT acknowledge the limitation -- a paper that
        disclosed its own run-count limit is a restatement, not a finding -- AND whose row a
        human has checked against the source. An unverified machine row is a draft, not evidence.
        """
        return (
            self.klass == "UNDERPOWERED"
            and self.row.acknowledged_limit == "no"
            and self.row.verified_by_human
        )


def classify(row: Row) -> Classified:
    """Classify one configuration. Never guesses; excludes instead."""
    row.validate()

    if row.estimator_family not in ESTIMATORS:
        # Protocol S5. `other` and NOT REPORTED both land here, and the count is reported.
        return Classified(
            row=row,
            klass="EXCLUDED",
            ceiling=None,
            ceiling_unit=None,
            reason=(
                f"estimator_family={row.estimator_family!r} is not one of {ESTIMATORS}; the "
                f"ceiling series cannot be determined, so the row is excluded rather than "
                f"guessed (protocol S5)."
            ),
        )

    if row.budget is None or row.alpha is None:
        return Classified(
            row=row,
            klass="NOT REPORTED",
            ceiling=None,
            ceiling_unit=None,
            reason=(
                "the paper does not state "
                + " and ".join(
                    n for n, v in (("budget", row.budget), ("alpha", row.alpha)) if v is None
                )
                + ", so the reach of its instrument cannot be recomputed."
            ),
        )

    try:
        ceil_ = ceiling_for(row.estimator_family, row.budget, row.alpha)
    except ValueError as exc:
        # e.g. a measured series queried at a budget this project never measured.
        return Classified(
            row=row,
            klass="EXCLUDED",
            ceiling=None,
            ceiling_unit=None,
            reason=f"no sourced ceiling available: {exc}",
        )

    if row.eps_proved is None:
        return Classified(
            row=row,
            klass="NOT REPORTED",
            ceiling=ceil_.value,
            ceiling_unit=ceil_.unit,
            reason="the paper states no analytic bound at this operating point to compare against.",
        )

    # Protocol S7: comparison only ever within a unit. `exceeds` raises on a mismatch, and that
    # is a protocol violation rather than a classification outcome.
    if ceil_.unit != row.proved_unit:
        raise ProtocolViolation(
            f"{row.paper_id}: the {row.estimator_family!r} ceiling is in {ceil_.unit!r} but the "
            f"paper's bound is in {row.proved_unit!r}. Comparing them is a units error, not a "
            f"rounding one. Re-extract with the estimator that matches the reported unit, or "
            f"exclude the row."
        )

    if ceil_.value < row.eps_proved:
        return Classified(
            row=row,
            klass="UNDERPOWERED",
            ceiling=ceil_.value,
            ceiling_unit=ceil_.unit,
            reason=(
                f"ceiling {ceil_.value:.4f} < proved {row.eps_proved:.4f}: even a perfect "
                f"adversary against a fully verbatim release could not have confirmed the bound "
                f"at this budget, so a null here is the instrument's floor."
            ),
        )

    if row.eps_emp is not None and ceil_.value > 0 and row.eps_emp >= 0.95 * ceil_.value:
        return Classified(
            row=row,
            klass="SATURATED",
            ceiling=ceil_.value,
            ceiling_unit=ceil_.unit,
            reason=(
                f"reported {row.eps_emp:.4f} is within 5% of the ceiling {ceil_.value:.4f}: the "
                f"estimate is pinned at the top of the instrument and the true value may be "
                f"higher."
            ),
        )

    return Classified(
        row=row,
        klass="INTERPRETABLE",
        ceiling=ceil_.value,
        ceiling_unit=ceil_.unit,
        reason=(
            f"ceiling {ceil_.value:.4f} >= proved {row.eps_proved:.4f}: the instrument could "
            f"have detected the bound, so the reported value carries evidential weight."
        ),
    )


def classify_all(rows: Sequence[Row]) -> List[Classified]:
    """Classify a table. A row that breaks the protocol is EXCLUDED and says why.

    `classify` raises on a protocol violation, which is right for a single row: the caller has
    made an error and should hear about it. But over a table, one bad row must not abort the
    survey and must not vanish either. Protocol S5 already prescribes the answer for a row whose
    ceiling cannot be determined -- exclude it, count it, report it -- and a units mismatch is
    exactly that case. So the violation becomes the exclusion reason and travels into the table
    where a human will see it.
    """
    out: List[Classified] = []
    for r in rows:
        try:
            out.append(classify(r))
        except ProtocolViolation as exc:
            out.append(
                Classified(
                    row=r,
                    klass="EXCLUDED",
                    ceiling=None,
                    ceiling_unit=None,
                    reason=f"protocol violation, excluded rather than guessed: {exc}",
                )
            )
    return out


def wilson_interval(successes: int, trials: int, z: float = 1.959963984540054) -> Tuple[float, float]:
    """Wilson score interval. Chosen over the normal approximation because K may be small.

    The default `z` is the two-sided 95% normal quantile.
    """
    if trials <= 0:
        return (0.0, 0.0)
    p = successes / trials
    denom = 1.0 + z * z / trials
    centre = (p + z * z / (2 * trials)) / denom
    half = (z / denom) * math.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials))
    return (max(0.0, centre - half), min(1.0, centre + half))


@dataclass(frozen=True)
class Summary:
    n_papers_included: int
    k: int
    k_rate: float
    k_ci: Tuple[float, float]
    by_class: Dict[str, int]
    n_excluded_undeterminable_estimator: int
    n_not_reported: int
    n_underpowered_but_acknowledged: int
    n_awaiting_human_verification: int
    per_estimator: Dict[str, Dict[str, int]]

    def headline(self) -> str:
        lo, hi = self.k_ci
        if self.n_papers_included == 0:
            return "NO PAPERS INCLUDED. Nothing can be concluded."
        if self.n_awaiting_human_verification:
            return (
                f"PRELIMINARY -- K IS NOT YET COMPUTABLE. "
                f"{self.n_awaiting_human_verification} of {self.n_papers_included} included "
                f"papers are machine-extracted and NOT yet verified against the source by a "
                f"human, so they are excluded from K by protocol amendment A1. The classes below "
                f"are a draft for a human to check, not a result. Do not quote K from this run."
            )
        if self.k == 0:
            return (
                f"K = 0 of {self.n_papers_included}. **No included paper was underpowered "
                f"without saying so.** The honest conclusion is that this literature reports "
                f"its own limits; the contribution reduces to the NOT-REPORTED count "
                f"({self.n_not_reported}) and the artefact work. Declared acceptable in advance "
                f"by protocol S10."
            )
        return (
            f"K = {self.k} of {self.n_papers_included} included papers "
            f"({100 * self.k_rate:.1f}%, 95% Wilson CI [{100 * lo:.1f}%, {100 * hi:.1f}%]) "
            f"report an empirical privacy result their own stated configuration could not have "
            f"produced, without acknowledging the limitation."
        )


def summarise(classified: Sequence[Classified]) -> Summary:
    """Paper-level summary. Protocol S3: a paper's class is its MOST FAVOURABLE configuration."""
    order = {"INTERPRETABLE": 0, "SATURATED": 1, "NOT REPORTED": 2, "UNDERPOWERED": 3, "EXCLUDED": 4}

    best: Dict[str, Classified] = {}
    for c in classified:
        pid = c.row.paper_id
        if pid not in best or order[c.klass] < order[best[pid].klass]:
            best[pid] = c

    papers = list(best.values())
    included = [c for c in papers if c.klass != "EXCLUDED"]

    by_class: Dict[str, int] = {k: 0 for k in _CLASSES}
    for c in papers:
        by_class[c.klass] += 1

    k = sum(1 for c in included if c.counts_toward_k)
    n = len(included)

    per_estimator: Dict[str, Dict[str, int]] = {}
    for c in papers:
        fam = c.row.estimator_family
        per_estimator.setdefault(fam, {kk: 0 for kk in _CLASSES})
        per_estimator[fam][c.klass] += 1

    return Summary(
        n_papers_included=n,
        k=k,
        k_rate=(k / n) if n else 0.0,
        k_ci=wilson_interval(k, n),
        by_class=by_class,
        n_excluded_undeterminable_estimator=by_class["EXCLUDED"],
        n_not_reported=by_class["NOT REPORTED"],
        n_underpowered_but_acknowledged=sum(
            1 for c in included if c.klass == "UNDERPOWERED" and c.row.acknowledged_limit == "yes"
        ),
        n_awaiting_human_verification=sum(1 for c in included if not c.row.verified_by_human),
        per_estimator=per_estimator,
    )


def to_dict(classified: Sequence[Classified]) -> List[dict]:
    return [
        {**asdict(c.row), "class": c.klass, "ceiling": c.ceiling,
         "ceiling_unit": c.ceiling_unit, "reason": c.reason,
         "counts_toward_k": c.counts_toward_k}
        for c in classified
    ]
