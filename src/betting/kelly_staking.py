"""
Kelly Staking Module

Applies quarter-Kelly with bankroll caps, drawdown controls, and $5 unit conversion.

Functions:
    - kelly_fraction: Calculate raw Kelly fraction
    - recommend_stake: Get stake recommendation with all adjustments
"""

from __future__ import annotations
from typing import Dict

from src.betting.odds_eval import american_to_decimal


UNIT_SIZE: float = 5.0
MAX_BANKROLL_ALLOC: float = 0.025  # 2.5%


def kelly_fraction(
    true_prob: float,
    odds: float,
    odds_type: str = "american"
) -> float:
    """
    Calculate raw Kelly fraction for a bet.
    
    Args:
        true_prob: True probability of winning (0.0 to 1.0)
        odds: Odds value
        odds_type: Either "american" or "decimal"
    
    Returns:
        Kelly fraction (0.0 or positive)
    """
    dec = odds if odds_type == "decimal" else american_to_decimal(odds)
    edge = true_prob * (dec - 1) - (1 - true_prob)
    denom = dec - 1
    if denom == 0:
        return 0.0
    frac = edge / denom
    return max(0.0, frac)


def recommend_stake(
    true_prob: float,
    odds: float,
    bankroll: float,
    confidence_tier: str,
    drawdown: float = 0.0,
    losing_streak: int = 0
) -> Dict[str, float | str]:
    """
    Get stake recommendation with quarter-Kelly and all adjustments.
    
    Applies:
        - Quarter Kelly fraction
        - Tier-based unit caps (A: 2.0, B: 1.5, C: 1.0)
        - Losing streak penalty (5% per loss after 2)
        - Drawdown penalty (50% reduction if drawdown >= 10%)
        - Hard cap of 2.5% of bankroll
    
    Args:
        true_prob: True probability of winning (0.0 to 1.0)
        odds: Odds value (American format)
        bankroll: Current bankroll amount
        confidence_tier: "A", "B", or "C"
        drawdown: Current drawdown percentage (0.0 to 1.0)
        losing_streak: Number of consecutive losses
    
    Returns:
        Dict with kelly_fraction, stake_amount, units, unit_size, and notes
    """
    frac = kelly_fraction(true_prob, odds) * 0.25  # quarter Kelly
    tier_caps: Dict[str, float] = {"A": 2.0, "B": 1.5, "C": 1.0}
    cap_units = tier_caps.get(confidence_tier, 0.5)
    streak_penalty = max(0.5, 1 - 0.05 * max(0, losing_streak - 2))
    drawdown_penalty = 0.5 if drawdown >= 0.1 else 1.0
    frac *= streak_penalty * drawdown_penalty
    stake = min(frac * bankroll, MAX_BANKROLL_ALLOC * bankroll)
    max_units = cap_units * UNIT_SIZE
    stake = min(stake, max_units)
    units = stake / UNIT_SIZE if UNIT_SIZE else 0
    return {
        "kelly_fraction": round(frac, 4),
        "stake_amount": round(stake, 2),
        "units": round(units, 2),
        "unit_size": UNIT_SIZE,
        "notes": f"Tier {confidence_tier}, drawdown {drawdown:.2%}, streak {losing_streak}"
    }
