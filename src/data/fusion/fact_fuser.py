"""
Fact fuser — merges multiple SportsFact objects for the same slot.

When multiple sources provide data for the same key:
  - Higher trust_tier sources win ties
  - When sources agree within threshold → weighted average, boosted confidence
  - When sources disagree → prefer higher tier, note conflict
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from src.data.models.facts import FactBundle, SportsFact

logger = logging.getLogger("omega.data.fusion.fact_fuser")


def fuse_facts(bundle: FactBundle) -> Dict[str, Any]:
    """Merge multiple facts into a single fused value dict.

    Args:
        bundle: FactBundle with facts from multiple sources.

    Returns:
        Merged dict of {key: value} representing the best available data.
    """
    if not bundle.facts:
        return {}

    # Group facts by key
    by_key: Dict[str, List[SportsFact]] = {}
    for fact in bundle.facts:
        by_key.setdefault(fact.key, []).append(fact)

    fused: Dict[str, Any] = {}

    for key, facts in by_key.items():
        if len(facts) == 1:
            fused[key] = facts[0].value
        else:
            fused[key] = _merge_values(key, facts)

    bundle.fused_value = fused
    return fused


def _merge_values(key: str, facts: List[SportsFact]) -> Any:
    """Merge multiple values for the same key.

    Strategy:
    1. Sort by trust tier (lower = better) then by confidence (higher = better)
    2. For numeric values: weighted average if sources agree, else prefer highest tier
    3. For non-numeric values: prefer highest-tier source
    """
    # Sort: best source first (lowest tier, then highest confidence)
    sorted_facts = sorted(
        facts,
        key=lambda f: (f.attribution.trust_tier, -f.attribution.confidence),
    )

    # Try numeric merge
    numeric_facts = []
    for f in sorted_facts:
        try:
            numeric_facts.append((f, float(f.value)))
        except (ValueError, TypeError):
            pass

    if numeric_facts:
        return _merge_numeric(key, numeric_facts)

    # Non-numeric: return highest-tier value
    return sorted_facts[0].value


def _merge_numeric(
    key: str, facts_with_values: List[tuple]
) -> float:
    """Merge numeric values using trust-weighted average.

    If values are close (within 10% of mean), use weighted average.
    If values diverge, prefer the highest-trust source.
    """
    if len(facts_with_values) == 1:
        return facts_with_values[0][1]

    values = [v for _, v in facts_with_values]
    mean = sum(values) / len(values)

    if mean == 0:
        return facts_with_values[0][1]

    # Check if values agree (range within 10% of mean)
    max_deviation = (max(values) - min(values)) / abs(mean)

    if max_deviation <= 0.10:
        # Sources agree — weighted average by confidence
        total_weight = 0.0
        weighted_sum = 0.0
        for fact, val in facts_with_values:
            weight = fact.attribution.confidence
            weighted_sum += weight * val
            total_weight += weight
        if total_weight > 0:
            return round(weighted_sum / total_weight, 2)
        return mean

    # Sources disagree — prefer highest-tier source
    logger.debug(
        "Source disagreement on %s: max_deviation=%.1f%%, using highest-tier value",
        key, max_deviation * 100,
    )
    return facts_with_values[0][1]  # Already sorted by tier
