"""
Completeness validator — checks if all critical keys are present.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Set

from src.data.models.facts import FactBundle

logger = logging.getLogger("omega.data.validators.completeness")

# Critical keys by data type — if these are missing, the slot is incomplete.
_CRITICAL_KEYS: Dict[str, Set[str]] = {
    "team_stat": {"off_rating", "def_rating"},
    "player_stat": {"pts_mean"},
    "odds": {"moneyline_home", "moneyline_away"},
    "schedule": {"home_team", "away_team"},
    "injury": {"status"},
    "player_game_log": {"pts_mean"},
}


def validate_completeness(bundle: FactBundle) -> float:
    """Check how complete a FactBundle is relative to critical keys.

    Args:
        bundle: The fact bundle to check.

    Returns:
        Completeness score 0.0–1.0 (1.0 = all critical keys present).
    """
    critical = _CRITICAL_KEYS.get(bundle.data_type, set())
    if not critical:
        return 1.0  # No critical keys defined → always complete

    present_keys = {f.key for f in bundle.facts}
    matched = critical & present_keys

    score = len(matched) / len(critical) if critical else 1.0

    if score < 1.0:
        missing = critical - present_keys
        logger.debug(
            "Completeness check: slot=%s missing=%s score=%.2f",
            bundle.slot_key, missing, score,
        )

    return score
