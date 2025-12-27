# Parlay Tools Module

"""
Module Name: Parlay & Correlation Tools
Version: 1.0.0
Description: Computes joint probabilities, correlation adjustments, and EV for parlays/Same-Game Parlays.
Functions:
    - validate_correlation_matrix(matrix: list[list[float]]) -> None
    - joint_probability(leg_probs: list[float], corr_matrix: list[list[float]] | None = None) -> float
    - adjusted_ev(leg_probs: list[float], odds: float, corr_matrix: list[list[float]] | None = None, odds_type: str = "american") -> dict
Usage Notes:
    - Reject parlays when |ρ| > 0.35 or adjusted EV < 0.
    - Works with odds_eval for implied conversions.
"""

```python
from __future__ import annotations
from typing import List, Optional
from math import prod

from odds_eval import implied_probability, expected_value_percent, american_to_decimal

def validate_correlation_matrix(matrix: List[List[float]]) -> None:
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

def joint_probability(leg_probs: List[float], corr_matrix: Optional[List[List[float]]] = None) -> float:
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

def adjusted_ev(leg_probs: List[float], odds: float, corr_matrix: Optional[List[List[float]]] = None, odds_type: str = "american") -> dict:
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
```

