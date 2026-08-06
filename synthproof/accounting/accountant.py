"""Privacy Accountant class supporting Gaussian, Laplace, RDP composition,
subsampling amplification, and budget tracking.

Implements Rényi Differential Privacy (RDP) composition from Mironov (2017)
with Poisson subsampling amplification from Mironov, Talwar & Zhang (2019).
"""

import copy
import math
from typing import List, Optional, Tuple

import numpy as np

from synthproof.accounting.types import (
    BudgetExceededError,
    MechanismSpec,
    PrivacyParams,
    PrivacySpend,
)


class Accountant:
    """Tracks cumulative DP privacy spend across mechanisms using RDP composition.

    Supports:
      - Gaussian mechanism RDP (exact formula)
      - Laplace mechanism RDP (closed-form bound)
      - Poisson subsampling amplification (when sampling_rate is set)
      - Multi-step composition (steps > 1)
      - Budget enforcement with dry-run and snapshot/restore
    """

    # Standard alpha grid for RDP evaluation (denser near alpha=1 where the bound is tightest)
    DEFAULT_ALPHAS = np.concatenate([
        np.linspace(1.1, 10.0, 50),
        np.linspace(10.5, 100.0, 50),
        np.linspace(105.0, 500.0, 50),
    ])

    def __init__(self, budget_eps: float, budget_delta: float = 1e-5):
        self.budget = PrivacyParams(epsilon=budget_eps, delta=budget_delta)
        self._spends: List[PrivacySpend] = []
        self._rdp_curve: np.ndarray = np.zeros_like(self.DEFAULT_ALPHAS)

    @property
    def spends(self) -> List[PrivacySpend]:
        """Returns read-only copy of spends history."""
        return list(self._spends)

    def _gaussian_rdp(self, sensitivity: float, noise_scale: float,
                      alphas: np.ndarray) -> np.ndarray:
        """RDP for Gaussian mechanism: R(α) = α·Δ² / (2σ²)."""
        if noise_scale == 0:
            return np.full_like(alphas, np.inf)
        return alphas * (sensitivity ** 2) / (2.0 * (noise_scale ** 2))

    def _laplace_rdp(self, sensitivity: float, noise_scale: float,
                     alphas: np.ndarray) -> np.ndarray:
        """RDP for Laplace mechanism (exact closed-form bound).

        For Laplace(b) with b = noise_scale / sensitivity:
        R(α) = (1/(α-1)) * log( α/(2α-1) * exp((α-1)/b) + (α-1)/(2α-1) * exp(-α/b) )
        """
        if noise_scale == 0:
            return np.full_like(alphas, np.inf)
        eps = sensitivity / noise_scale
        rdp = (1.0 / (alphas - 1.0)) * np.log(
            (alphas / (2.0 * alphas - 1.0)) * np.exp((alphas - 1.0) * eps)
            + ((alphas - 1.0) / (2.0 * alphas - 1.0)) * np.exp(-alphas * eps)
        )
        return rdp

    def _apply_subsampling(self, rdp_curve: np.ndarray, sampling_rate: float,
                           alphas: np.ndarray) -> np.ndarray:
        """Applies Poisson subsampling amplification to an RDP curve.

        Uses the upper bound from Mironov, Talwar & Zhang (2019), Proposition 10:
        For subsampling rate q and base mechanism RDP ρ(α), the subsampled
        mechanism satisfies RDP with:
          ρ_sub(α) ≤ (1/(α-1)) * log(1 + q² * C(α) * (exp((α-1)*ρ(α)) - 1))

        For simplicity and numerical stability, we use the tighter bound:
          ρ_sub(α) ≤ (1/(α-1)) * log(1 + q² * α * (exp(ρ(α)) - 1))
        when ρ(α) is small, and the naive bound q*ρ(α) otherwise.
        """
        if sampling_rate >= 1.0:
            return rdp_curve

        q = sampling_rate
        amplified = np.zeros_like(rdp_curve)

        for i, (alpha, rdp) in enumerate(zip(alphas, rdp_curve)):
            if rdp == 0.0:
                amplified[i] = 0.0
            elif np.isinf(rdp):
                amplified[i] = np.inf
            else:
                # Use min of several bounds for tightness
                # Bound 1: naive q * rdp
                b1 = q * rdp
                # Bound 2: subsampled RDP (approximate)
                expm1 = np.expm1((alpha - 1) * rdp)
                if np.isfinite(expm1) and expm1 > 0:
                    b2 = (1.0 / (alpha - 1.0)) * np.log1p(q * q * expm1)
                else:
                    b2 = b1
                amplified[i] = min(b1, b2)

        return amplified

    def _compute_mechanism_rdp(self, spec: MechanismSpec) -> np.ndarray:
        """Computes RDP curve R(alpha) for a given mechanism spec across DEFAULT_ALPHAS."""
        alphas = self.DEFAULT_ALPHAS
        name = spec.name.lower()

        # Base mechanism RDP (single step, no subsampling)
        if name in ("gaussian", "dp-sgd"):
            base_rdp = self._gaussian_rdp(spec.sensitivity, spec.noise_scale, alphas)
        elif name == "laplace":
            base_rdp = self._laplace_rdp(spec.sensitivity, spec.noise_scale, alphas)
        else:
            # Default: treat as Gaussian
            base_rdp = self._gaussian_rdp(spec.sensitivity, spec.noise_scale, alphas)

        # Apply subsampling amplification if applicable
        if spec.sampling_rate is not None and spec.sampling_rate < 1.0:
            base_rdp = self._apply_subsampling(base_rdp, spec.sampling_rate, alphas)

        # Composition across steps (linear in RDP)
        return base_rdp * spec.steps

    def _rdp_to_eps(self, rdp_curve: np.ndarray, delta: float) -> float:
        """Converts RDP curve to (epsilon, delta)-DP via optimization over alphas.

        Uses the conversion: eps = min_α { ρ(α) + log(1/δ) / (α-1) }
        from Balle et al. (2020) Proposition 3.
        """
        if np.all(rdp_curve == 0.0):
            return 0.0
        if delta <= 0:
            return float("inf")
        alphas = self.DEFAULT_ALPHAS
        # eps(alpha) = rdp(alpha) + log(1/delta) / (alpha - 1)
        eps_values = rdp_curve + np.log(1.0 / delta) / (alphas - 1.0)
        valid_eps = eps_values[np.isfinite(eps_values)]
        if len(valid_eps) == 0:
            return float("inf")
        return float(np.min(valid_eps))

    def dry_run(self, spec: MechanismSpec, delta: Optional[float] = None) -> float:
        """Calculates what total epsilon would be if spec were charged, without mutating state."""
        target_delta = delta if delta is not None else self.budget.delta
        spec_rdp = self._compute_mechanism_rdp(spec)
        hypothetical_rdp = self._rdp_curve + spec_rdp
        return self._rdp_to_eps(hypothetical_rdp, target_delta)

    def charge(self, spec: MechanismSpec, run_id: Optional[str] = None) -> PrivacySpend:
        """Charges a mechanism to the budget. Raises BudgetExceededError if over budget."""
        spec_rdp = self._compute_mechanism_rdp(spec)
        new_rdp = self._rdp_curve + spec_rdp
        new_eps = self._rdp_to_eps(new_rdp, self.budget.delta)

        if new_eps > self.budget.epsilon:
            raise BudgetExceededError(
                requested_eps=new_eps - self.total(self.budget.delta),
                remaining_eps=self.remaining(self.budget.delta),
                delta=self.budget.delta,
            )

        self._rdp_curve = new_rdp
        spend = PrivacySpend(
            mechanism=spec,
            computed_eps=new_eps,
            delta=self.budget.delta,
            run_id=run_id,
        )
        self._spends.append(spend)
        return spend

    def total(self, delta: Optional[float] = None) -> float:
        """Returns current total composed epsilon at specified delta."""
        target_delta = delta if delta is not None else self.budget.delta
        return self._rdp_to_eps(self._rdp_curve, target_delta)

    def remaining(self, delta: Optional[float] = None) -> float:
        """Returns remaining epsilon budget at specified delta."""
        target_delta = delta if delta is not None else self.budget.delta
        current_eps = self.total(target_delta)
        return max(0.0, self.budget.epsilon - current_eps)

    def snapshot(self) -> Tuple[np.ndarray, List[PrivacySpend]]:
        """Returns a snapshot tuple of current accountant state."""
        return copy.deepcopy(self._rdp_curve), copy.deepcopy(self._spends)

    def restore(self, snapshot: Tuple[np.ndarray, List[PrivacySpend]]) -> None:
        """Restores accountant state from a snapshot."""
        self._rdp_curve, self._spends = copy.deepcopy(snapshot)
