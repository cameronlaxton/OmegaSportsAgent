"""
Agreement validator — checks consistency across multiple sources.

When multiple sources provide the same fact, flags disagreements that
exceed a configurable threshold.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Tuple

from src.data.models.facts import SportsFact

logger = logging.getLogger("omega.data.validators.agreement")

# Disagreement thresholds by key type.
# If two sources disagree by more than this fraction of the value, flag it.
_DISAGREEMENT_THRESHOLDS: Dict[str, float] = {
    "off_rating": 0.05,        # 5% disagreement
    "def_rating": 0.05,
    "pace": 0.05,
    "pts_per_game": 0.05,
    "pts_mean": 0.10,
    "moneyline_home": 0.15,    # Odds can vary more across books
    "moneyline_away": 0.15,
    "spread_home": 0.10,
    "total": 0.05,
    "fg_pct": 0.10,
}

_DEFAULT_THRESHOLD = 0.10


def validate_agreement(facts: List[SportsFact]) -> Tuple[List[SportsFact], List[str]]:
    """Check agreement across facts with the same key from different sources.

    Args:
        facts: All facts for a single slot/entity from multiple sources.

    Returns:
        Tuple of (validated facts, list of warning messages).
    """
    warnings: List[str] = []

    # Group facts by key
    by_key: Dict[str, List[SportsFact]] = {}
    for fact in facts:
        by_key.setdefault(fact.key, []).append(fact)

    for key, group in by_key.items():
        if len(group) < 2:
            continue

        # Extract numeric values for comparison
        numeric_values = []
        for f in group:
            try:
                numeric_values.append((f, float(f.value)))
            except (ValueError, TypeError):
                pass

        if len(numeric_values) < 2:
            continue

        # Check pairwise disagreement
        threshold = _DISAGREEMENT_THRESHOLDS.get(key, _DEFAULT_THRESHOLD)
        values = [v for _, v in numeric_values]
        avg = sum(values) / len(values)

        if avg == 0:
            continue

        for fact, val in numeric_values:
            deviation = abs(val - avg) / abs(avg)
            if deviation > threshold:
                warnings.append(
                    f"Disagreement on {key}: {fact.attribution.source_name} "
                    f"reports {val:.2f} vs avg {avg:.2f} (deviation {deviation:.1%})"
                )
                logger.debug(
                    "Agreement check flagged: key=%s source=%s value=%.2f avg=%.2f",
                    key, fact.attribution.source_name, val, avg,
                )

    return facts, warnings
