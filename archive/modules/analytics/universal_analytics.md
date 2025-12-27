# Universal Analytics Module

"""
Module Name: Universal Analytics
Version: 1.0.0
Description: Universal predictive models: Pythagorean expectation, Elo/Glicko rating systems.
Functions:
    - pythagorean_expectation(points_for: float, points_against: float, exponent: float = 2.0) -> float
    - elo_rating_update(rating: float, opponent_rating: float, result: float, k_factor: float = 32.0, home_adjustment: float = 0.0) -> float
    - elo_win_probability(rating: float, opponent_rating: float, home_adjustment: float = 0.0) -> float
    - glicko_rating_update(rating: float, rating_deviation: float, opponent_rating: float, opponent_rd: float, result: float, tau: float = 0.5) -> tuple
Usage Notes:
    - Pythagorean exponent configurable per league via league_config
    - Elo supports K-factor and home-field/court/ice adjustment
    - Glicko includes rating deviation (uncertainty)
    - All functions are league-agnostic
"""

```python
from __future__ import annotations
import math
from typing import Tuple

def pythagorean_expectation(points_for: float, points_against: float, exponent: float = 2.0) -> float:
    """
    Calculates expected win percentage using Pythagorean expectation.
    
    Formula: Win% = (Points_For^exponent) / (Points_For^exponent + Points_Against^exponent)
    
    Args:
        points_for: Average points scored per game
        points_against: Average points allowed per game
        exponent: Exponent for the formula (default 2.0, but varies by league)
                  - NBA: ~14.0
                  - NFL: ~2.37
                  - MLB: ~1.83
                  - NHL: ~2.0
    
    Returns:
        Expected win percentage (0.0 to 1.0)
    """
    if points_against <= 0:
        return 1.0 if points_for > 0 else 0.5
    
    pf_exp = pow(points_for, exponent)
    pa_exp = pow(points_against, exponent)
    
    if pf_exp + pa_exp == 0:
        return 0.5
    
    return pf_exp / (pf_exp + pa_exp)

def elo_win_probability(rating: float, opponent_rating: float, home_adjustment: float = 0.0) -> float:
    """
    Calculates win probability using Elo rating system.
    
    Formula: P = 1 / (1 + 10^((opponent_rating - rating - home_adjustment) / 400))
    
    Args:
        rating: Team's Elo rating
        opponent_rating: Opponent's Elo rating
        home_adjustment: Home field/court/ice advantage in rating points (default 0.0)
                        Typical values: 65-75 points
    
    Returns:
        Win probability (0.0 to 1.0)
    """
    rating_diff = opponent_rating - rating - home_adjustment
    return 1.0 / (1.0 + pow(10.0, rating_diff / 400.0))

def elo_rating_update(rating: float, opponent_rating: float, result: float, k_factor: float = 32.0, home_adjustment: float = 0.0) -> float:
    """
    Updates Elo rating after a game.
    
    Formula: New_Rating = Old_Rating + K * (Result - Expected_Result)
    
    Args:
        rating: Current Elo rating
        opponent_rating: Opponent's Elo rating
        result: Game result (1.0 for win, 0.5 for tie, 0.0 for loss)
        k_factor: K-factor determining rating change magnitude (default 32.0)
                  - Higher K = more volatile ratings
                  - Typical: 20-40 for team sports
        home_adjustment: Home field/court/ice advantage in rating points
    
    Returns:
        Updated Elo rating
    """
    expected = elo_win_probability(rating, opponent_rating, home_adjustment)
    return rating + k_factor * (result - expected)

def glicko_rating_update(
    rating: float,
    rating_deviation: float,
    opponent_rating: float,
    opponent_rd: float,
    result: float,
    tau: float = 0.5
) -> Tuple[float, float]:
    """
    Updates Glicko rating and rating deviation after a game.
    
    Glicko system includes rating deviation (uncertainty) which decreases with more games.
    
    Args:
        rating: Current Glicko rating
        rating_deviation: Current rating deviation (uncertainty)
        opponent_rating: Opponent's Glicko rating
        opponent_rd: Opponent's rating deviation
        result: Game result (1.0 for win, 0.5 for tie, 0.0 for loss)
        tau: System constant controlling rating deviation volatility (default 0.5)
    
    Returns:
        Tuple of (updated_rating, updated_rating_deviation)
    
    Note:
        This is a simplified Glicko implementation. Full Glicko-2 includes volatility.
        TODO: Implement full Glicko-2 with volatility parameter if needed.
    """
    # Glicko constants
    q = math.log(10) / 400.0
    
    # Calculate g(RD) function
    def g(rd: float) -> float:
        return 1.0 / math.sqrt(1.0 + 3.0 * q * q * rd * rd / (math.pi * math.pi))
    
    # Calculate expected outcome
    g_opp = g(opponent_rd)
    expected = 1.0 / (1.0 + pow(10.0, -g_opp * (rating - opponent_rating) / 400.0))
    
    # Calculate d^2
    d_squared = 1.0 / (q * q * g_opp * g_opp * expected * (1.0 - expected))
    
    # Update rating deviation (with time decay)
    # In practice, rating deviation increases between games due to time decay
    # For simplicity, we'll use a fixed decay factor here
    # TODO: Implement proper time decay based on days since last game
    new_rd = math.sqrt(1.0 / (1.0 / (rating_deviation * rating_deviation) + 1.0 / d_squared))
    
    # Update rating
    new_rating = rating + q / (1.0 / (rating_deviation * rating_deviation) + 1.0 / d_squared) * g_opp * (result - expected)
    
    return (new_rating, new_rd)

def get_pythagorean_exponent(league: str) -> float:
    """
    Returns recommended Pythagorean exponent for a league.
    
    Args:
        league: League identifier
    
    Returns:
        Recommended exponent value
    """
    league = league.upper()
    exponents = {
        "NBA": 14.0,
        "NFL": 2.37,
        "MLB": 1.83,
        "NHL": 2.0,
        "NCAAF": 2.5,
        "NCAAB": 11.5
    }
    return exponents.get(league, 2.0)

def get_elo_k_factor(league: str) -> float:
    """
    Returns recommended Elo K-factor for a league.
    
    Args:
        league: League identifier
    
    Returns:
        Recommended K-factor
    """
    league = league.upper()
    k_factors = {
        "NBA": 20.0,
        "NFL": 20.0,
        "MLB": 16.0,
        "NHL": 20.0,
        "NCAAF": 25.0,
        "NCAAB": 20.0
    }
    return k_factors.get(league, 32.0)

def get_elo_home_adjustment(league: str) -> float:
    """
    Returns recommended Elo home advantage adjustment for a league.
    
    Args:
        league: League identifier
    
    Returns:
        Home advantage in Elo rating points
    """
    league = league.upper()
    home_advantages = {
        "NBA": 65.0,
        "NFL": 65.0,
        "MLB": 40.0,  # Lower for baseball
        "NHL": 55.0,
        "NCAAF": 70.0,  # Higher for college
        "NCAAB": 70.0
    }
    return home_advantages.get(league, 65.0)

```

