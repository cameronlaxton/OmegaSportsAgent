# Odds Evaluation Module

"""
Module Name: Odds & EV Evaluation
Version: 1.0.0
Description: Converts odds to implied probabilities and computes EV/edge metrics.
Functions:
    - american_to_decimal(odds: float) -> float
    - implied_probability(odds: float, odds_type: str = "american") -> float
    - expected_value(true_prob: float, odds: float, stake: float = 1.0, odds_type: str = "american") -> float
    - expected_value_percent(true_prob: float, odds: float, odds_type: str = "american") -> float
    - edge_percentage(true_prob: float, implied_prob: float) -> float
Usage Notes:
    - Supports American and Decimal odds.
    - Returns EV in currency units and percent.
"""

```python
from __future__ import annotations

def american_to_decimal(odds: float) -> float:
    odds = float(odds)
    if odds > 0:
        return 1 + odds / 100
    return 1 + 100 / abs(odds)

def implied_probability(odds: float, odds_type: str = "american") -> float:
    if odds_type == "decimal":
        return 1 / float(odds)
    return 1 / american_to_decimal(odds)

def expected_value(true_prob: float, odds: float, stake: float = 1.0, odds_type: str = "american") -> float:
    dec = odds if odds_type == "decimal" else american_to_decimal(odds)
    win_return = stake * (dec - 1)
    lose = stake
    return true_prob * win_return - (1 - true_prob) * lose

def expected_value_percent(true_prob: float, odds: float, odds_type: str = "american") -> float:
    stake = 1.0
    return expected_value(true_prob, odds, stake, odds_type) / stake * 100

def edge_percentage(true_prob: float, implied_prob: float) -> float:
    return (true_prob - implied_prob) * 100
```

