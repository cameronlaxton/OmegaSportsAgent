"""
Odds & EV Evaluation Module

Converts odds to implied probabilities and computes EV/edge metrics.

Functions:
    - american_to_decimal: Convert American odds to decimal format
    - implied_probability: Calculate implied probability from odds
    - expected_value: Calculate EV in currency units
    - expected_value_percent: Calculate EV as percentage
    - edge_percentage: Calculate edge between true and implied probability
"""

from __future__ import annotations


def american_to_decimal(odds: float) -> float:
    """
    Convert American odds to decimal odds.
    
    Args:
        odds: American odds value (positive or negative)
    
    Returns:
        Decimal odds equivalent
    """
    odds = float(odds)
    if odds > 0:
        return 1 + odds / 100
    return 1 + 100 / abs(odds)


def implied_probability(odds: float, odds_type: str = "american") -> float:
    """
    Calculate implied probability from odds.
    
    Args:
        odds: Odds value
        odds_type: Either "american" or "decimal"
    
    Returns:
        Implied probability (0.0 to 1.0)
    """
    if odds_type == "decimal":
        return 1 / float(odds)
    return 1 / american_to_decimal(odds)


def expected_value(
    true_prob: float,
    odds: float,
    stake: float = 1.0,
    odds_type: str = "american"
) -> float:
    """
    Calculate expected value in currency units.
    
    Args:
        true_prob: True probability of winning (0.0 to 1.0)
        odds: Odds value
        stake: Bet amount
        odds_type: Either "american" or "decimal"
    
    Returns:
        Expected value in same units as stake
    """
    dec = odds if odds_type == "decimal" else american_to_decimal(odds)
    win_return = stake * (dec - 1)
    lose = stake
    return true_prob * win_return - (1 - true_prob) * lose


def expected_value_percent(
    true_prob: float,
    odds: float,
    odds_type: str = "american"
) -> float:
    """
    Calculate expected value as a percentage of stake.
    
    Args:
        true_prob: True probability of winning (0.0 to 1.0)
        odds: Odds value
        odds_type: Either "american" or "decimal"
    
    Returns:
        Expected value percentage
    """
    stake = 1.0
    return expected_value(true_prob, odds, stake, odds_type) / stake * 100


def edge_percentage(true_prob: float, implied_prob: float) -> float:
    """
    Calculate edge percentage between true and implied probability.
    
    Args:
        true_prob: True probability (0.0 to 1.0)
        implied_prob: Implied probability from odds (0.0 to 1.0)
    
    Returns:
        Edge as percentage points
    """
    return (true_prob - implied_prob) * 100
