# Model Audit Module

"""
Module Name: Model Audit & Drift Detection
Version: 1.0.0
Description: Computes Brier score, CLV, ROI, and drift flags for model health checks.
Functions:
    - brier_score(outcomes: list[int], probs: list[float]) -> float
    - clv(bets: list[dict]) -> float
    - drift_flags(recent_metrics: dict) -> dict
    - run_model_health_check(bet_log: list[dict]) -> dict
Usage Notes:
    - `bets` entries require keys: open_line, close_line, stake, result.
    - Drift flags trigger Minimal Exposure mode when negative CLV or ROI drop.
"""

```python
from __future__ import annotations
from typing import List, Dict
from statistics import mean

from odds_eval import implied_probability

def brier_score(outcomes: List[int], probs: List[float]) -> float:
    if not outcomes:
        return 0.0
    return sum((p - o) ** 2 for p, o in zip(probs, outcomes)) / len(outcomes)

def clv(bets: List[Dict]) -> float:
    if not bets:
        return 0.0
    diffs = []
    for bet in bets:
        open_imp = implied_probability(bet["open_line"])
        close_imp = implied_probability(bet["close_line"])
        diffs.append(close_imp - open_imp)
    return mean(diffs)

def drift_flags(recent_metrics: Dict) -> Dict:
    flags = {}
    if recent_metrics.get("clv", 0) < -0.01:
        flags["clv_drift"] = "Negative CLV trend detected."
    if recent_metrics.get("roi", 0) < 0:
        flags["roi_drift"] = "Negative ROI over sample."
    if recent_metrics.get("brier", 0) > 0.25:
        flags["calibration_issue"] = "Brier score exceeds tolerance."
    return flags

def run_model_health_check(bet_log: List[Dict]) -> Dict:
    if not bet_log:
        return {"message": "No settled bets.", "flags": {}}
    outcomes = [bet["result"] for bet in bet_log]
    probs = [bet["true_prob"] for bet in bet_log]
    pnl = [bet["pnl"] for bet in bet_log]
    stakes = [bet["stake"] for bet in bet_log]
    roi = mean(p / s if s else 0 for p, s in zip(pnl, stakes))
    metrics = {
        "brier": brier_score(outcomes, probs),
        "clv": clv(bet_log),
        "roi": roi
    }
    metrics["flags"] = drift_flags(metrics)
    return metrics
```

