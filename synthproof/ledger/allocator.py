"""Adaptive DP privacy budget allocator across columns and release tasks."""

from typing import Dict, List


class Allocator:
    """Allocates an epsilon budget across columns using uniform or weighted splits.

    NOTE: nothing in the pipeline currently calls this. Wiring it into the generators is
    a prerequisite for hypothesis H3. See brutal_project_audit.md, Tier 3 item 20.
    """

    @staticmethod
    def allocate_uniform(total_eps: float, items: List[str]) -> Dict[str, float]:
        """Splits total_eps uniformly among items."""
        if total_eps <= 0:
            raise ValueError(f"Total epsilon must be positive, got {total_eps}")
        if not items:
            return {}
        per_item = total_eps / len(items)
        return {item: per_item for item in items}

    @staticmethod
    def allocate_weighted(total_eps: float, weights: Dict[str, float]) -> Dict[str, float]:
        """Splits total_eps across items proportional to positive weights."""
        if total_eps <= 0:
            raise ValueError(f"Total epsilon must be positive, got {total_eps}")
        if not weights:
            return {}
        
        sum_weights = sum(max(0.0, w) for w in weights.values())
        if sum_weights <= 0:
            # Fallback to uniform if all weights <= 0
            return Allocator.allocate_uniform(total_eps, list(weights.keys()))
        
        allocation = {}
        for item, w in weights.items():
            clean_w = max(0.0, w)
            allocation[item] = total_eps * (clean_w / sum_weights)
        return allocation
