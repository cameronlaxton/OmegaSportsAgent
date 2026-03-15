"""
Confidence scorer — computes a composite confidence score for a FactBundle.

Factors:
  - Source trust tier (higher tier = higher confidence)
  - Freshness (newer = higher confidence)
  - Agreement across sources (agreement = higher confidence)
  - Completeness (more critical keys present = higher confidence)
"""

from __future__ import annotations

import time
from typing import Dict, List

from agent.models import FRESHNESS_RULES
from src.data.models.facts import FactBundle
from src.data.sources.source_config import get_confidence_for_tier
from src.data.validators.completeness_validator import validate_completeness


def score_confidence(bundle: FactBundle) -> float:
    """Compute a composite confidence score for a FactBundle.

    Args:
        bundle: The fact bundle to score.

    Returns:
        Confidence score 0.0–1.0.
    """
    if not bundle.facts:
        return 0.0

    # Factor 1: Source trust (average confidence from trust tiers)
    source_score = _source_trust_score(bundle)

    # Factor 2: Freshness
    freshness_score = _freshness_score(bundle)

    # Factor 3: Agreement (bonus if multiple sources agree)
    agreement_score = _agreement_score(bundle)

    # Factor 4: Completeness
    completeness_score = validate_completeness(bundle)

    # Weighted combination
    composite = (
        0.35 * source_score
        + 0.25 * freshness_score
        + 0.20 * agreement_score
        + 0.20 * completeness_score
    )

    bundle.fused_confidence = round(min(1.0, max(0.0, composite)), 3)
    return bundle.fused_confidence


def _source_trust_score(bundle: FactBundle) -> float:
    """Score based on the trust tiers of contributing sources."""
    if not bundle.facts:
        return 0.0

    # Use the best (lowest tier) source's confidence
    best_tier = min(f.attribution.trust_tier for f in bundle.facts)
    return get_confidence_for_tier(best_tier)


def _freshness_score(bundle: FactBundle) -> float:
    """Score based on how fresh the data is relative to freshness rules."""
    if not bundle.facts:
        return 0.0

    max_age = FRESHNESS_RULES.get(bundle.data_type, 86400.0)
    now = time.time()

    # Use the freshest fact
    newest_age = min(
        now - f.attribution.fetched_at.timestamp()
        for f in bundle.facts
    )

    if newest_age <= 0:
        return 1.0
    if newest_age >= max_age:
        return 0.0

    # Linear decay
    return 1.0 - (newest_age / max_age)


def _agreement_score(bundle: FactBundle) -> float:
    """Score based on agreement across multiple sources.

    If only one source: 0.5 (neutral)
    If multiple sources agree: up to 1.0
    If sources disagree: lower score
    """
    if len(bundle.facts) < 2:
        return 0.5

    # Group by key, check numeric agreement
    by_key: Dict[str, List[float]] = {}
    for fact in bundle.facts:
        try:
            by_key.setdefault(fact.key, []).append(float(fact.value))
        except (ValueError, TypeError):
            pass

    if not by_key:
        return 0.5

    # Average agreement across keys
    agreements = []
    for key, values in by_key.items():
        if len(values) < 2:
            continue
        mean = sum(values) / len(values)
        if mean == 0:
            continue
        max_dev = max(abs(v - mean) / abs(mean) for v in values)
        # 0% deviation = 1.0 agreement, 10% = 0.5, 20%+ = 0.0
        agreement = max(0.0, 1.0 - (max_dev / 0.20))
        agreements.append(agreement)

    if not agreements:
        return 0.5

    return sum(agreements) / len(agreements)
