"""
Model Audit & Drift Detection Module

Computes Brier score, CLV, ROI, and drift flags for model health checks.

Functions:
    - brier_score: Calculate Brier score for probability calibration
    - clv: Calculate Closing Line Value
    - drift_flags: Generate drift warning flags
    - run_model_health_check: Run comprehensive model health check
"""

from __future__ import annotations
from typing import List, Dict, Any
from statistics import mean

from src.betting.odds_eval import implied_probability


def brier_score(outcomes: List[int], probs: List[float]) -> float:
    """
    Calculate Brier score for probability calibration.
    
    Brier = (1/n) * Σ(p_i - o_i)²
    where p_i is predicted probability and o_i is outcome (0 or 1).
    
    Lower is better (0 = perfect, 1 = worst).
    
    Args:
        outcomes: List of outcomes (1 for win, 0 for loss)
        probs: List of predicted probabilities
    
    Returns:
        Brier score (0.0 to 1.0)
    """
    if not outcomes:
        return 0.0
    return sum((p - o) ** 2 for p, o in zip(probs, outcomes)) / len(outcomes)


def clv(bets: List[Dict[str, Any]]) -> float:
    """
    Calculate average Closing Line Value (CLV) across bets.
    
    CLV measures whether the line moved in your favor after betting.
    Positive CLV indicates consistently betting on the right side of movement.
    
    Args:
        bets: List of bet dictionaries with keys:
            - open_line: Opening odds (American format)
            - close_line: Closing odds (American format)
    
    Returns:
        Average CLV as probability difference
    """
    if not bets:
        return 0.0
    diffs: List[float] = []
    for bet in bets:
        open_imp = implied_probability(bet["open_line"])
        close_imp = implied_probability(bet["close_line"])
        diffs.append(close_imp - open_imp)
    return mean(diffs)


def drift_flags(recent_metrics: Dict[str, Any]) -> Dict[str, str]:
    """
    Generate drift warning flags based on recent metrics.
    
    Flags trigger Minimal Exposure mode when:
    - CLV is negative (betting wrong side of line movement)
    - ROI is negative (losing money)
    - Brier score exceeds tolerance (poor calibration)
    
    Args:
        recent_metrics: Dictionary with keys:
            - clv: float (average CLV)
            - roi: float (return on investment)
            - brier: float (Brier score)
    
    Returns:
        Dictionary of flag names to warning messages
    """
    flags: Dict[str, str] = {}
    if recent_metrics.get("clv", 0) < -0.01:
        flags["clv_drift"] = "Negative CLV trend detected."
    if recent_metrics.get("roi", 0) < 0:
        flags["roi_drift"] = "Negative ROI over sample."
    if recent_metrics.get("brier", 0) > 0.25:
        flags["calibration_issue"] = "Brier score exceeds tolerance."
    return flags


def run_model_health_check(bet_log: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Run comprehensive model health check on settled bets.
    
    Computes Brier score, CLV, ROI, and generates drift flags.
    
    Args:
        bet_log: List of settled bet dictionaries with keys:
            - result: int (1 for win, 0 for loss)
            - true_prob: float (predicted probability)
            - pnl: float (profit/loss)
            - stake: float (amount wagered)
            - open_line: float (opening odds)
            - close_line: float (closing odds)
    
    Returns:
        Dictionary with metrics and flags:
            - brier: float
            - clv: float
            - roi: float
            - flags: Dict[str, str]
    """
    if not bet_log:
        return {"message": "No settled bets.", "flags": {}}
    
    outcomes = [bet["result"] for bet in bet_log]
    probs = [bet["true_prob"] for bet in bet_log]
    pnl = [bet["pnl"] for bet in bet_log]
    stakes = [bet["stake"] for bet in bet_log]
    
    roi = mean(p / s if s else 0 for p, s in zip(pnl, stakes))
    
    metrics: Dict[str, Any] = {
        "brier": brier_score(outcomes, probs),
        "clv": clv(bet_log),
        "roi": roi
    }
    metrics["flags"] = drift_flags(metrics)
    
    return metrics
