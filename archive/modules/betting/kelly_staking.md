# Kelly Staking Module

"""
Module Name: Kelly Staking Logic
Version: 1.0.0
Description: Applies quarter-Kelly with bankroll caps, drawdown controls, and $5 unit conversion.
Functions:
    - kelly_fraction(true_prob: float, odds: float, odds_type: str = "american") -> float
    - recommend_stake(true_prob: float, odds: float, bankroll: float, confidence_tier: str, drawdown: float = 0.0, losing_streak: int = 0) -> dict
Usage Notes:
    - Hard cap: 2.5% of bankroll and tier-based unit limits.
    - Convert stake to units using $5 baseline.
"""

```python
from __future__ import annotations
from typing import Dict
from odds_eval import american_to_decimal

UNIT_SIZE = 5.0
MAX_BANKROLL_ALLOC = 0.025  # 2.5%

def kelly_fraction(true_prob: float, odds: float, odds_type: str = "american") -> float:
    dec = odds if odds_type == "decimal" else american_to_decimal(odds)
    edge = true_prob * (dec - 1) - (1 - true_prob)
    denom = dec - 1
    if denom == 0:
        return 0.0
    frac = edge / denom
    return max(0.0, frac)

def recommend_stake(true_prob: float, odds: float, bankroll: float, confidence_tier: str, drawdown: float = 0.0, losing_streak: int = 0) -> Dict:
    frac = kelly_fraction(true_prob, odds) * 0.25  # quarter Kelly
    tier_caps = {"A": 2.0, "B": 1.5, "C": 1.0}
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
```

