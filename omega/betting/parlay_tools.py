"""
Parlay & Correlation Tools Module

Computes joint probabilities, correlation adjustments, and EV for parlays/Same-Game Parlays.

Functions:
    - validate_correlation_matrix: Validate correlation matrix structure and values
    - joint_probability: Calculate joint probability with optional correlation adjustment
    - adjusted_ev: Calculate EV metrics for a parlay with acceptance criteria
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any
from math import prod

from omega.betting.odds_eval import (
    implied_probability,
    expected_value_percent,
    american_to_decimal,
)


def validate_correlation_matrix(matrix: List[List[float]]) -> None:
    """
    Validate a correlation matrix for parlay calculations.
    
    Requirements:
        - Matrix must be square
        - Diagonal must be 1.0
        - All correlations must be within [-0.35, 0.35]
    
    Args:
        matrix: Square correlation matrix
    
    Raises:
        ValueError: If matrix is invalid or correlations exceed threshold
    """
    size = len(matrix)
    for row in matrix:
        if len(row) != size:
            raise ValueError("Correlation matrix must be square.")
    for i in range(size):
        if matrix[i][i] != 1:
            raise ValueError("Diagonal must be 1.")
        for j in range(size):
            if abs(matrix[i][j]) > 0.35:
                raise ValueError(f"Correlation {matrix[i][j]} exceeds allowed threshold.")


def joint_probability(
    leg_probs: List[float],
    corr_matrix: Optional[List[List[float]]] = None
) -> float:
    """
    Calculate joint probability for parlay legs with optional correlation adjustment.
    
    Args:
        leg_probs: List of individual leg probabilities
        corr_matrix: Optional correlation matrix (validated if provided)
    
    Returns:
        Joint probability (0.0 to 1.0)
    """
    baseline = prod(leg_probs)
    if not corr_matrix:
        return baseline
    validate_correlation_matrix(corr_matrix)
    size = len(leg_probs)
    corr_adjustment = 0.0
    for i in range(size):
        for j in range(i + 1, size):
            corr_adjustment += corr_matrix[i][j]
    corr_factor = 1 + corr_adjustment / max(1, size - 1)
    return max(0.0, min(1.0, baseline * corr_factor))


def adjusted_ev(
    leg_probs: List[float],
    odds: float,
    corr_matrix: Optional[List[List[float]]] = None,
    odds_type: str = "american"
) -> Dict[str, Any]:
    """
    Calculate EV metrics for a parlay and determine acceptance.
    
    Acceptance criteria:
        - Edge >= 3%
        - EV >= 2.5%
    
    Args:
        leg_probs: List of individual leg probabilities
        odds: Parlay odds
        corr_matrix: Optional correlation matrix
        odds_type: Either "american" or "decimal"
    
    Returns:
        Dict with joint_prob, implied_prob, ev_percent, edge_percent, and accept flag
    """
    joint_prob = joint_probability(leg_probs, corr_matrix)
    implied = implied_probability(odds, odds_type)
    ev_pct = expected_value_percent(joint_prob, odds, odds_type)
    edge_pct = (joint_prob - implied) * 100
    return {
        "joint_prob": joint_prob,
        "implied_prob": implied,
        "ev_percent": ev_pct,
        "edge_percent": edge_pct,
        "accept": edge_pct >= 3 and ev_pct >= 2.5
    }
