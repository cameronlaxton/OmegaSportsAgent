"""
Odds normalizer — convert between American, decimal, and implied probability.
"""

from __future__ import annotations

from typing import Any


def american_to_decimal(american: int) -> float:
    """Convert American odds to decimal odds.

    Examples:
        -150 → 1.667
        +130 → 2.300
    """
    if american > 0:
        return 1.0 + (american / 100.0)
    elif american < 0:
        return 1.0 + (100.0 / abs(american))
    else:
        return 1.0


def american_to_implied_prob(american: int) -> float:
    """Convert American odds to implied probability (includes vig).

    Examples:
        -150 → 0.600
        +130 → 0.435
    """
    if american < 0:
        return abs(american) / (abs(american) + 100.0)
    elif american > 0:
        return 100.0 / (american + 100.0)
    else:
        return 0.5


def decimal_to_american(decimal_odds: float) -> int:
    """Convert decimal odds to American odds.

    Examples:
        1.667 → -150
        2.300 → +130
    """
    if decimal_odds <= 1.0:
        return 0
    if decimal_odds < 2.0:
        return int(round(-100.0 / (decimal_odds - 1.0)))
    else:
        return int(round((decimal_odds - 1.0) * 100.0))


def normalize_odds_value(value: Any) -> Any:
    """Normalize an odds value to a consistent format.

    Handles string inputs like "+130", "-150", "1.5", etc.
    Returns int for American odds, float for decimal/probability.
    """
    if isinstance(value, (int, float)):
        return value

    if isinstance(value, str):
        value = value.strip()
        # American odds: "+130", "-150"
        if value.startswith("+") or value.startswith("-"):
            try:
                return int(value)
            except ValueError:
                try:
                    return int(float(value))
                except ValueError:
                    pass
        # Decimal odds or probability
        try:
            return float(value)
        except ValueError:
            pass

    return value
