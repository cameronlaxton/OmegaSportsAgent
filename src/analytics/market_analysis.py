"""
Market Analysis & Confidence Assessment Module

Evaluates market sharpness, line movement, public betting patterns, and sharp action
to assess market confidence for bet recommendations.
"""

from __future__ import annotations
from typing import Dict, Optional


def _implied_probability(odds: float, odds_type: str = "american") -> float:
    """
    Calculates implied probability from odds.
    
    Args:
        odds: Odds value
        odds_type: Type of odds ("american" or "decimal")
    
    Returns:
        Implied probability (0.0 to 1.0)
    """
    if odds_type == "decimal":
        return 1 / float(odds) if odds > 0 else 0.0
    if odds > 0:
        return 1 / (1 + odds / 100)
    return 1 / (1 + 100 / abs(odds)) if odds != 0 else 0.0


def calculate_line_movement_score(open_line: float, current_line: float, movement_direction: str) -> float:
    """
    Calculates a score based on line movement magnitude and direction.
    
    Args:
        open_line: Opening line value
        current_line: Current line value
        movement_direction: Direction of movement
    
    Returns:
        A value between 0.0 (no movement) and 1.0 (significant movement)
    """
    movement = abs(current_line - open_line)
    if movement == 0:
        return 0.0
    if abs(open_line) < 1000:
        score = min(1.0, movement * 0.1)
    else:
        open_imp = _implied_probability(open_line)
        curr_imp = _implied_probability(current_line)
        score = min(1.0, abs(curr_imp - open_imp) * 10)
    return score


def evaluate_sharp_contrarian_signal(public_pct: float, sharp_action: str, line_movement: Dict) -> Dict:
    """
    Detects if sharp money is fading public action.
    
    Args:
        public_pct: Percentage of public bets (0.0 to 1.0)
        sharp_action: Type of sharp action ("fade_public", "opposite_side", etc.)
        line_movement: Dict with movement information
    
    Returns:
        Dict with 'is_contrarian' flag and 'strength' score
    """
    sharp_on_opposite = sharp_action in {"fade_public", "opposite_side"}
    public_heavy = public_pct > 0.60
    line_moved_against_public = line_movement.get("direction") == "against_public"
    
    is_contrarian = sharp_on_opposite and public_heavy
    strength = 0.0
    if is_contrarian:
        strength += 0.4 if public_heavy else 0.0
        strength += 0.3 if line_moved_against_public else 0.0
        strength += 0.3 if public_pct > 0.70 else 0.0
    
    return {
        "is_contrarian": is_contrarian,
        "strength": min(1.0, strength),
        "public_pct": public_pct,
        "sharp_action": sharp_action
    }


def assess_market_confidence(
    odds: float,
    line_movement: Dict,
    public_pct: float,
    sharp_indicators: Dict,
    market_efficiency: Dict
) -> Dict:
    """
    Assesses overall market confidence based on multiple factors.
    
    Args:
        odds: Current betting odds (American format)
        line_movement: Dict with keys 'open_line', 'current_line', 'direction'
            (str: 'toward_us', 'away_from_us', 'against_public', 'with_public')
        public_pct: Percentage of public bets on our side (0.0 to 1.0)
        sharp_indicators: Dict with keys 'sharp_action'
            (str: 'on_our_side', 'fade_public', 'opposite_side', 'neutral'),
            'sharp_volume' (float: 0.0 to 1.0)
        market_efficiency: Dict with keys 'efficiency_score' (float: 0.0 to 1.0),
            'market_type' (str: 'sharp', 'square', 'mixed')
    
    Returns:
        Dict with 'confidence_level' (str: 'high', 'medium', 'low', 'contrarian'),
        'score' (float: 0.0 to 1.0), 'factors' (dict), 'recommendation' (str)
    """
    movement_score = calculate_line_movement_score(
        line_movement.get("open_line", odds),
        line_movement.get("current_line", odds),
        line_movement.get("direction", "neutral")
    )
    
    contrarian = evaluate_sharp_contrarian_signal(
        public_pct,
        sharp_indicators.get("sharp_action", "neutral"),
        line_movement
    )
    
    confidence_score = 0.5
    
    efficiency = market_efficiency.get("efficiency_score", 0.5)
    market_type = market_efficiency.get("market_type", "mixed")
    if market_type == "sharp":
        confidence_score += 0.15
    elif market_type == "square":
        confidence_score += 0.1
    else:
        confidence_score += 0.05
    
    if line_movement.get("direction") == "toward_us":
        confidence_score += 0.15
    elif line_movement.get("direction") == "away_from_us":
        confidence_score -= 0.15
    elif line_movement.get("direction") == "against_public" and public_pct > 0.60:
        confidence_score += 0.1
    
    sharp_action = sharp_indicators.get("sharp_action", "neutral")
    sharp_volume = sharp_indicators.get("sharp_volume", 0.0)
    if sharp_action == "on_our_side":
        confidence_score += 0.15 * sharp_volume
    elif sharp_action == "fade_public" and public_pct > 0.60:
        confidence_score -= 0.2
    elif sharp_action == "opposite_side":
        confidence_score -= 0.15 * sharp_volume
    
    if public_pct > 0.70:
        confidence_score -= 0.1
    elif public_pct < 0.40:
        confidence_score += 0.05
    
    confidence_score = max(0.0, min(1.0, confidence_score))
    
    if contrarian["is_contrarian"] and contrarian["strength"] > 0.6:
        confidence_level = "contrarian"
        recommendation = "Require edge ≥ 5% to proceed; sharp money fading public position."
    elif confidence_score >= 0.7:
        confidence_level = "high"
        recommendation = "Market conditions favorable; standard tier assignment applies."
    elif confidence_score >= 0.4:
        confidence_level = "medium"
        recommendation = "Standard tier assignment applies."
    else:
        confidence_level = "low"
        recommendation = "Downgrade tier by one level unless edge ≥ 10%."
    
    return {
        "confidence_level": confidence_level,
        "confidence_score": round(confidence_score, 3),
        "factors": {
            "line_movement_score": round(movement_score, 3),
            "public_percentage": round(public_pct, 3),
            "sharp_action": sharp_action,
            "sharp_volume": round(sharp_volume, 3),
            "market_type": market_type,
            "contrarian_signal": contrarian
        },
        "recommendation": recommendation
    }
