"""Recomputing the claimed epsilon from the declared mechanism events, and the second
accountant cross-check (RB4, RB5)."""

from typing import Any, List, Mapping, Optional

from synthproof.audit.boundary._types import (
    LEAK,
    NOTE,
    UNVERIFIABLE,
    BoundaryFinding,
    _number,
)


def _recompute_epsilon(sheet: Mapping[str, Any]) -> Optional[List[BoundaryFinding]]:
    """RB5 from the artefact's own signed event list, not from its self-reported verdict.

    A sheet that carries `mechanism_events` (every noisy step: mechanism, sensitivity, noise
    scale, repetitions) lets the checker recompose epsilon itself with BOTH accountants. Before
    this, RB5 read `accountant_agreement.verdict` as written -- a maker could type "agree"
    (audit C4, research/27). Returns None when the sheet carries no events.
    """
    events = sheet.get("mechanism_events")
    if not isinstance(events, list) or not events:
        return None
    from synthproof.accounting.accountant import Accountant
    from synthproof.accounting.differential import cross_check_spends
    from synthproof.accounting.types import MechanismSpec

    delta = _number(sheet.get("delta"))
    if delta is None or not (0.0 < delta < 1.0):
        return [
            BoundaryFinding(
                "RB5",
                UNVERIFIABLE,
                "delta",
                f"The sheet carries an event list but no usable delta ({sheet.get('delta')!r}).",
                "An (epsilon, delta) guarantee cannot be recomposed without its delta, so the "
                "published epsilon cannot be checked from the artefact.",
                "Publish delta in (0, 1) alongside mechanism_events.",
            )
        ]
    try:
        acct = Accountant(budget_eps=float("inf"), budget_delta=delta)
        for ev in events:
            acct.charge(
                MechanismSpec(
                    name=str(ev["name"]),
                    sensitivity=float(ev["sensitivity"]),
                    noise_scale=float(ev["noise_scale"]),
                    steps=int(ev.get("steps", 1)),
                    sampling_rate=ev.get("sampling_rate"),
                )
            )
    except (KeyError, TypeError, ValueError) as exc:
        return [
            BoundaryFinding(
                "RB5",
                LEAK,
                "mechanism_events",
                f"The signed event list cannot be recomposed ({exc}).",
                "The published epsilon has no computation behind it that a reader can repeat.",
                "Publish a well-formed event list: name, sensitivity, noise_scale, steps.",
            )
        ]
    recomputed = acct.total() + (_number(sheet.get("release_rows_eps")) or 0.0)
    claimed = sheet.get("total_proved_eps")
    if not isinstance(claimed, (int, float)) or recomputed > float(claimed) * (1 + 1e-6) + 1e-9:
        return [
            BoundaryFinding(
                "RB5",
                LEAK,
                "total_proved_eps",
                f"Recomposing the signed event list gives epsilon {recomputed:.4f}, larger than "
                f"the published {claimed}.",
                "The headline guarantee under-states what the release's own steps cost.",
                "Publish the recomputed epsilon, or correct the event list.",
            )
        ]
    second = cross_check_spends(acct.spends, delta)
    if second.verdict == "under_report":
        return [
            BoundaryFinding(
                "RB5",
                LEAK,
                "mechanism_events",
                f"An independent accountant (autodp) composes the events to "
                f"{second.secondary_epsilon:.4f}, more than the published {claimed}.",
                "The published guarantee is not supported by an independent computation.",
                "Do not rely on total_proved_eps until the disagreement is resolved.",
            )
        ]
    return [
        BoundaryFinding(
            "RB5",
            NOTE,
            "mechanism_events",
            f"Recomputed here from the signed event list: epsilon {recomputed:.4f} "
            f"(published {claimed}); second accountant: {second.verdict}.",
            "The epsilon is repeatable by the reader, not taken on the maker's word.",
            "None.",
        )
    ]


def _cross_check(sheet: Mapping[str, Any]) -> List[BoundaryFinding]:
    agreement = sheet.get("accountant_agreement") or {}
    verdict = agreement.get("verdict") if isinstance(agreement, Mapping) else None
    # A maker's own admission of an under-report is a leak whatever the recomputation says.
    recomputed = None if verdict == "under_report" else _recompute_epsilon(sheet)
    if recomputed is not None:
        return recomputed
    if verdict == "under_report":
        return [
            BoundaryFinding(
                "RB5",
                LEAK,
                "accountant_agreement",
                "A second accountant composed this release to a LARGER epsilon than the one "
                "published.",
                "The published guarantee is not supported by an independent computation.",
                "Do not rely on total_proved_eps until the disagreement is resolved.",
            )
        ]
    if verdict in ("agree", "conservative"):
        return [
            BoundaryFinding(
                "RB5",
                UNVERIFIABLE,
                "accountant_agreement",
                f"The maker reports a second accountant said: {verdict}. The sheet carries no "
                "event list, so this checker cannot recompute it.",
                "The agreement is the maker's own statement, not something this file proves.",
                "Publish mechanism_events so a reader can recompose the epsilon.",
            )
        ]
    return [
        BoundaryFinding(
            "RB5",
            UNVERIFIABLE,
            "accountant_agreement",
            f"The epsilon was not independently cross-checked (verdict: {verdict or 'absent'}).",
            "It rests on a single accounting implementation, and audits of DP libraries have found "
            "guarantee violations in them.",
            "Treat total_proved_eps as one implementation's claim.",
        )
    ]
