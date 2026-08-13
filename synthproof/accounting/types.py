"""Core data structures and exceptions for Differential Privacy accounting."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class BudgetExceededError(Exception):
    """Raised when a privacy charge exceeds the remaining allocated budget."""

    def __init__(self, requested_eps: float, remaining_eps: float, delta: float):
        self.requested_eps = requested_eps
        self.remaining_eps = remaining_eps
        self.delta = delta
        super().__init__(
            f"Privacy spend of epsilon={requested_eps:.4f} exceeds remaining "
            f"epsilon={remaining_eps:.4f} at delta={delta:.2e}"
        )


@dataclass(frozen=True)
class PrivacyParams:
    """Holds total privacy budget parameters (epsilon, delta)."""

    epsilon: float
    delta: float = 1e-5

    def __post_init__(self):
        if self.epsilon < 0:
            raise ValueError(f"Epsilon must be non-negative, got {self.epsilon}")
        if not (0 <= self.delta < 1.0):
            raise ValueError(f"Delta must be in [0, 1), got {self.delta}")


@dataclass(frozen=True)
class MechanismSpec:
    """Specification of a DP mechanism execution."""

    name: str
    sensitivity: float
    noise_scale: float
    sampling_rate: Optional[float] = None
    steps: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.sensitivity <= 0:
            raise ValueError(f"Sensitivity must be positive, got {self.sensitivity}")
        if self.noise_scale < 0:
            raise ValueError(f"Noise scale must be non-negative, got {self.noise_scale}")
        if self.steps < 1:
            raise ValueError(f"Steps must be at least 1, got {self.steps}")
        if self.sampling_rate is not None and not (0 < self.sampling_rate <= 1.0):
            raise ValueError(f"Sampling rate must be in (0, 1.0], got {self.sampling_rate}")


@dataclass(frozen=True)
class PrivacySpend:
    """Record of a single privacy charge to the accountant.

    Note the distinction between the two epsilon fields: composition is sublinear, so the
    marginal cost of a charge is not the same as its cost in isolation, and the running
    total is not the sum of the marginals.
    """

    spend_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    mechanism: MechanismSpec = field(default_factory=lambda: MechanismSpec("gaussian", 1.0, 1.0))
    computed_eps: float = 0.0     # cumulative total epsilon AFTER this charge
    marginal_eps: float = 0.0     # increase in the total attributable to this charge
    delta: float = 1e-5
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    run_id: Optional[str] = None
