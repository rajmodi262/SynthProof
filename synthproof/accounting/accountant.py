"""Privacy accountant with budget enforcement, dry-run, and snapshot/restore.

The composition math is delegated to Google's `dp_accounting` (the reference
implementation used by TensorFlow Privacy). This module owns the *interface* — budget
enforcement, spend history, dry-run, snapshot/restore — which is the part specific to
SynthProof; it does not re-derive privacy theory.

This replaces a hand-rolled RDP implementation whose subsampling amplification used
``min(q * rho(alpha), truncated_MTZ)``. Neither branch was a citable theorem: RDP does
not amplify linearly under subsampling, the MTZ series was truncated, and the alpha grid
was non-integer while the MTZ bound requires integer orders. See brutal_project_audit.md,
finding F4.
"""

import copy
from typing import List, Optional, Sequence, Tuple

from dp_accounting import dp_event
from dp_accounting.rdp import rdp_privacy_accountant

from synthproof.accounting.types import (
    BudgetExceededError,
    MechanismSpec,
    PrivacyParams,
    PrivacySpend,
)

# Standard RDP order grid (as used by TensorFlow Privacy). Includes integer orders,
# which the subsampled-RDP bounds require.
DEFAULT_ORDERS: Sequence[float] = (
    [1 + x / 10.0 for x in range(1, 100)]
    + list(range(11, 64))
    + [128, 256, 512, 1024]
)

# Mechanism names accepted in MechanismSpec.name, mapped to how they are accounted.
_GAUSSIAN_NAMES = frozenset({"gaussian", "dp-sgd", "dpsgd"})
_LAPLACE_NAMES = frozenset({"laplace"})


class Accountant:
    """Tracks cumulative DP spend across mechanisms and enforces a budget.

    Supports:
      - Gaussian and Laplace mechanisms
      - Poisson subsampling amplification (when ``sampling_rate`` is set)
      - Multi-step composition (``steps > 1``)
      - Budget enforcement, dry-run, and snapshot/restore
    """

    def __init__(self, budget_eps: float, budget_delta: float = 1e-5,
                 orders: Optional[Sequence[float]] = None):
        self.budget = PrivacyParams(epsilon=budget_eps, delta=budget_delta)
        self._orders = list(orders) if orders is not None else list(DEFAULT_ORDERS)
        self._events: List[Tuple[dp_event.DpEvent, int]] = []
        self._spends: List[PrivacySpend] = []

    # ------------------------------------------------------------------ properties

    @property
    def spends(self) -> List[PrivacySpend]:
        """Read-only copy of the spend history."""
        return list(self._spends)

    @property
    def events(self) -> List[Tuple[dp_event.DpEvent, int]]:
        """Read-only copy of the composed (event, repetitions) pairs."""
        return list(self._events)

    # ------------------------------------------------------------------ translation

    @staticmethod
    def to_dp_event(spec: MechanismSpec) -> dp_event.DpEvent:
        """Translates a MechanismSpec into a dp_accounting DpEvent.

        The noise multiplier is the noise scale expressed in units of sensitivity, which
        is what dp_accounting expects: sigma/Delta for Gaussian, b/Delta for Laplace.
        """
        name = spec.name.lower()

        # Zero noise is not "a very small amount of privacy loss" — it is none at all.
        # Modelling it explicitly keeps epsilon at infinity instead of silently
        # producing a finite number.
        if spec.noise_scale == 0:
            return dp_event.NonPrivateDpEvent()

        noise_multiplier = spec.noise_scale / spec.sensitivity

        if name in _GAUSSIAN_NAMES:
            base = dp_event.GaussianDpEvent(noise_multiplier)
        elif name in _LAPLACE_NAMES:
            base = dp_event.LaplaceDpEvent(noise_multiplier)
        else:
            raise ValueError(
                f"Unknown mechanism {spec.name!r}. Supported: "
                f"{sorted(_GAUSSIAN_NAMES | _LAPLACE_NAMES)}. "
                "(A previous version silently accounted unknown mechanisms as Gaussian.)"
            )

        if spec.sampling_rate is not None and spec.sampling_rate < 1.0:
            base = dp_event.PoissonSampledDpEvent(spec.sampling_rate, base)

        return base

    # ------------------------------------------------------------------ composition

    def _epsilon_for(self, events: List[Tuple[dp_event.DpEvent, int]], delta: float) -> float:
        """Composes (event, count) pairs in a fresh accountant and returns epsilon."""
        if not events:
            return 0.0
        if delta <= 0:
            return float("inf")
        acct = rdp_privacy_accountant.RdpAccountant(self._orders)
        for ev, count in events:
            # compose() takes a repetition count directly; composing `count` separate
            # events instead makes calibration search prohibitively slow for large step
            # counts (e.g. 100-step subsampled Gaussian).
            acct.compose(ev, count)
        return float(acct.get_epsilon(delta))

    def _events_for(self, spec: MechanismSpec) -> List[Tuple[dp_event.DpEvent, int]]:
        """Expands a spec into a single (event, repetitions) pair."""
        return [(self.to_dp_event(spec), spec.steps)]

    # ------------------------------------------------------------------ public API

    def dry_run(self, spec: MechanismSpec, delta: Optional[float] = None) -> float:
        """Total epsilon that *would* result from charging `spec`, without mutating state."""
        target_delta = delta if delta is not None else self.budget.delta
        return self._epsilon_for(self._events + self._events_for(spec), target_delta)

    def charge(self, spec: MechanismSpec, run_id: Optional[str] = None) -> PrivacySpend:
        """Charges a mechanism to the budget.

        Raises:
            BudgetExceededError: if the resulting total would exceed the budget. The
                accountant is left unmodified in that case.
        """
        prior_eps = self.total()
        new_events = self._events + self._events_for(spec)
        new_eps = self._epsilon_for(new_events, self.budget.delta)

        if new_eps > self.budget.epsilon:
            raise BudgetExceededError(
                requested_eps=new_eps - prior_eps,
                remaining_eps=max(0.0, self.budget.epsilon - prior_eps),
                delta=self.budget.delta,
            )

        self._events = new_events
        spend = PrivacySpend(
            mechanism=spec,
            computed_eps=new_eps,
            marginal_eps=new_eps - prior_eps,
            delta=self.budget.delta,
            run_id=run_id,
        )
        self._spends.append(spend)
        return spend

    def total(self, delta: Optional[float] = None) -> float:
        """Current total composed epsilon at the given delta."""
        target_delta = delta if delta is not None else self.budget.delta
        return self._epsilon_for(self._events, target_delta)

    def remaining(self, delta: Optional[float] = None) -> float:
        """Remaining epsilon budget at the given delta."""
        target_delta = delta if delta is not None else self.budget.delta
        return max(0.0, self.budget.epsilon - self.total(target_delta))

    # ------------------------------------------------------------------ state

    def snapshot(self) -> Tuple[List[Tuple[dp_event.DpEvent, int]], List[PrivacySpend]]:
        """Returns a snapshot of the current accountant state."""
        return list(self._events), copy.deepcopy(self._spends)

    def restore(
        self, snapshot: Tuple[List[Tuple[dp_event.DpEvent, int]], List[PrivacySpend]]
    ) -> None:
        """Restores accountant state from a snapshot."""
        events, spends = snapshot
        self._events = list(events)
        self._spends = copy.deepcopy(spends)
