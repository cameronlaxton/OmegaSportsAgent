"""
Stat normalizer — normalize statistical values to consistent formats.
"""

from __future__ import annotations

from typing import Any


def normalize_stat_value(key: str, value: Any, league: str = "") -> Any:
    """Normalize a stat value based on its key and context.

    Handles common issues:
    - Percentages expressed as 0-100 vs 0-1
    - String values that should be numeric
    - Per-game vs total stats
    """
    if value is None:
        return None

    # Convert string to number if possible
    if isinstance(value, str):
        value = value.strip().rstrip("%")
        try:
            value = float(value)
        except ValueError:
            return value

    # Normalize percentage fields
    _PCT_KEYS = {
        "fg_pct", "three_pt_pct", "ft_pct", "ts_pct",
        "efg_pct", "batting_avg", "save_pct",
        "power_play_pct", "penalty_kill_pct",
    }

    if key in _PCT_KEYS and isinstance(value, (int, float)):
        # If value > 1, assume it's already a percentage (e.g., 48.5)
        # Convert to decimal form (0.485) for consistency
        if value > 1.0:
            value = value / 100.0

    return value
