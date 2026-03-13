"""
Feature builders for web/scraped data.

Transforms raw team/player/weather signals into simulation-ready inputs:
- Pace/off/def adjustments
- Injury/usage impacts
- Weather modifiers (for outdoor leagues)
"""

from __future__ import annotations

from typing import Dict, Any


def compute_team_ratings(raw: Dict[str, Any]) -> Dict[str, float]:
    """
    Derive offensive/defensive ratings and pace from scraped stats.
    Uses simple heuristics; replace with league-specific models as needed.
    """
    off = raw.get("off_rating")
    defense = raw.get("def_rating")
    pace = raw.get("pace")

    # Fallbacks using points per game/allowed if provided.
    ppg = raw.get("points_per_game")
    papg = raw.get("points_allowed_per_game")
    if off is None and ppg is not None:
        off = float(ppg)
    if defense is None and papg is not None:
        defense = float(papg)

    # Pace fallback using possessions or tempo
    if pace is None:
        possessions = raw.get("possessions_per_game") or raw.get("tempo")
        if possessions:
            pace = float(possessions)

    return {
        "off_rating": off if off is not None else 0.0,
        "def_rating": defense if defense is not None else 0.0,
        "pace": pace if pace is not None else 0.0,
    }


def apply_injury_adjustment(ratings: Dict[str, float], injury_factor: float) -> Dict[str, float]:
    """
    Apply a simple injury penalty to offensive and pace metrics.
    injury_factor: 0.0-1.0 where higher = more severe injury impact.
    """
    factor = max(0.0, min(1.0, injury_factor))
    adjusted = ratings.copy()
    adjusted["off_rating"] *= (1.0 - 0.5 * factor)
    adjusted["pace"] *= (1.0 - 0.3 * factor)
    return adjusted


def apply_weather_adjustment(ratings: Dict[str, float], weather: Dict[str, Any]) -> Dict[str, float]:
    """
    Adjust pace and scoring variance for outdoor leagues based on weather.
    """
    wind = weather.get("wind_mph", 0.0) or 0.0
    precip = (weather.get("precipitation") or "none").lower()
    adjusted = ratings.copy()

    wind_penalty = 0.0
    if wind >= 15:
        wind_penalty = min(0.10, wind / 200.0)

    precip_penalty = 0.0
    if precip in {"rain", "snow"}:
        precip_penalty = 0.08

    pace_penalty = wind_penalty + precip_penalty
    adjusted["pace"] *= (1.0 - pace_penalty)
    adjusted["off_rating"] *= (1.0 - 0.5 * precip_penalty)
    return adjusted

