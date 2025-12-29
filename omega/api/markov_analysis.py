"""
Markov Simulation Analysis API

Strategic analysis engine for player props and betting suggestions using
Markov chain play-by-play simulation. This API provides high-level functions
for analyzing player performance and generating betting recommendations based
on detailed game state modeling.

Key Features:
- Play-by-play Markov simulation for player props
- Strategic bet analysis with edge calculation
- Multi-player correlation modeling
- Injury-adjusted projections
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from omega.simulation.markov_engine import (
    MarkovSimulator,
    MarkovState,
    TransitionMatrix,
    run_markov_player_prop_simulation,
    validate_team_context,
    validate_player_context,
    validate_game_for_simulation
)
from omega.betting.odds_eval import (
    implied_probability,
    edge_percentage,
    expected_value_percent
)
from omega.betting.kelly_staking import recommend_stake
from omega.foundation.model_config import get_edge_thresholds

logger = logging.getLogger(__name__)


def analyze_player_prop_markov(
    player: Dict[str, Any],
    teammates: List[Dict[str, Any]],
    opponents: List[Dict[str, Any]],
    prop_type: str,
    market_line: float,
    over_odds: float,
    under_odds: float,
    league: str = "NBA",
    n_iter: int = 10000,
    home_context: Optional[Any] = None,
    away_context: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Analyze a player prop using Markov play-by-play simulation.
    
    This function runs detailed game simulations to model player performance
    at the play level, accounting for usage rates, team context, and matchup
    dynamics.
    
    Args:
        player: Player dict with name, team, usage_rate, and statistical averages
        teammates: List of teammate dicts with similar structure
        opponents: List of opponent player dicts
        prop_type: Stat type (e.g., "pts", "reb", "ast", "rec_yds", "rush_yds")
        market_line: The betting line (e.g., 25.5 points)
        over_odds: American odds for over (e.g., -110)
        under_odds: American odds for under (e.g., -110)
        league: League identifier (NBA, NFL, MLB, NHL, NCAAB, NCAAF)
        n_iter: Number of Monte Carlo iterations (default: 10000)
        home_context: Optional home team context with off_rating, def_rating, pace
        away_context: Optional away team context
    
    Returns:
        Dict containing:
        - over_prob: Model probability of going over the line
        - under_prob: Model probability of going under the line
        - over_edge_pct: Edge percentage for over bet
        - under_edge_pct: Edge percentage for under bet
        - over_ev_pct: Expected value percentage for over
        - under_ev_pct: Expected value percentage for under
        - recommended_bet: "over", "under", or "pass"
        - confidence_tier: "A", "B", "C", or "Pass"
        - stake_recommendation: Kelly-optimal stake info
        - simulation_summary: Statistical summary of simulations
    """
    logger.info(f"Analyzing {player.get('name', 'Unknown')} {prop_type} prop (line: {market_line})")
    
    # Validate player data
    is_valid, issues = validate_player_context(player)
    if not is_valid:
        logger.warning(f"Player validation issues: {issues}")
        return {
            "error": "Insufficient player data",
            "issues": issues,
            "recommended_bet": "pass",
            "reason": "Data quality check failed"
        }
    
    # Run Markov simulation
    sim_result = run_markov_player_prop_simulation(
        player=player,
        teammates=teammates,
        opponents=opponents,
        stat_key=prop_type,
        market_line=market_line,
        league=league,
        n_iter=n_iter
    )
    
    if "error" in sim_result:
        logger.error(f"Simulation failed: {sim_result['error']}")
        return {
            "error": sim_result["error"],
            "recommended_bet": "pass",
            "reason": "Simulation error"
        }
    
    # Extract probabilities
    over_prob = sim_result.get("over_prob", 0.5)
    under_prob = sim_result.get("under_prob", 0.5)
    
    # Calculate implied probabilities and edges
    over_implied = implied_probability(over_odds)
    under_implied = implied_probability(under_odds)
    
    over_edge = edge_percentage(over_prob, over_implied)
    under_edge = edge_percentage(under_prob, under_implied)
    
    over_ev = expected_value_percent(over_prob, over_odds)
    under_ev = expected_value_percent(under_prob, under_odds)
    
    # Get thresholds
    thresholds = get_edge_thresholds()
    prop_threshold = thresholds.get("prop", 5.0)
    
    # Determine recommendation
    recommended_bet = "pass"
    confidence_tier = "Pass"
    best_edge = 0.0
    best_ev = 0.0
    selected_prob = 0.5
    selected_odds = 0
    
    if over_edge >= prop_threshold and over_edge > under_edge:
        recommended_bet = "over"
        best_edge = over_edge
        best_ev = over_ev
        selected_prob = over_prob
        selected_odds = over_odds
    elif under_edge >= prop_threshold:
        recommended_bet = "under"
        best_edge = under_edge
        best_ev = under_ev
        selected_prob = under_prob
        selected_odds = under_odds
    
    # Determine confidence tier
    if best_edge >= 8.0:
        confidence_tier = "A"
    elif best_edge >= 5.0:
        confidence_tier = "B"
    elif best_edge >= 3.0:
        confidence_tier = "C"
    
    # Calculate stake recommendation
    stake_info = {}
    if recommended_bet != "pass":
        stake_info = recommend_stake(
            true_prob=selected_prob,
            odds=selected_odds,
            bankroll=1000.0,
            confidence_tier=confidence_tier
        )
    
    return {
        "player_name": sim_result.get("player_name", player.get("name", "Unknown")),
        "prop_type": prop_type,
        "market_line": market_line,
        "league": league,
        "simulation_iterations": n_iter,
        
        # Simulation results
        "projected_mean": sim_result.get("mean", 0),
        "projected_std": sim_result.get("std", 0),
        "projected_min": sim_result.get("min", 0),
        "projected_max": sim_result.get("max", 0),
        
        # Probabilities
        "over_prob": over_prob,
        "under_prob": under_prob,
        "push_prob": sim_result.get("push_prob", 0),
        "over_implied_prob": over_implied,
        "under_implied_prob": under_implied,
        
        # Edge and EV
        "over_edge_pct": over_edge,
        "under_edge_pct": under_edge,
        "over_ev_pct": over_ev,
        "under_ev_pct": under_ev,
        
        # Recommendation
        "recommended_bet": recommended_bet,
        "confidence_tier": confidence_tier,
        "best_edge_pct": best_edge,
        "best_ev_pct": best_ev,
        
        # Staking
        "stake_recommendation": stake_info,
        
        # Metadata
        "analysis_timestamp": datetime.now().isoformat(),
        "threshold_used": prop_threshold
    }


def analyze_multiple_props(
    props: List[Dict[str, Any]],
    league: str = "NBA",
    n_iter: int = 10000,
    min_edge: Optional[float] = None
) -> Dict[str, Any]:
    """
    Analyze multiple player props using Markov simulation.
    
    This is useful for generating a slate of betting recommendations
    across multiple players and games.
    
    Args:
        props: List of prop dicts, each containing:
            - player: Player info dict
            - teammates: List of teammate dicts
            - opponents: List of opponent dicts
            - prop_type: Stat type
            - market_line: Betting line
            - over_odds: Odds for over
            - under_odds: Odds for under
        league: League identifier
        n_iter: Simulation iterations per prop
        min_edge: Minimum edge threshold (overrides default)
    
    Returns:
        Dict with qualified bets and analysis summary
    """
    logger.info(f"Analyzing {len(props)} props using Markov simulation")
    
    results = []
    qualified_bets = []
    
    thresholds = get_edge_thresholds()
    edge_threshold = min_edge if min_edge is not None else thresholds.get("prop", 5.0)
    
    for i, prop_data in enumerate(props):
        try:
            result = analyze_player_prop_markov(
                player=prop_data["player"],
                teammates=prop_data.get("teammates", []),
                opponents=prop_data.get("opponents", []),
                prop_type=prop_data["prop_type"],
                market_line=prop_data["market_line"],
                over_odds=prop_data["over_odds"],
                under_odds=prop_data["under_odds"],
                league=prop_data.get("league", league),
                n_iter=n_iter,
                home_context=prop_data.get("home_context"),
                away_context=prop_data.get("away_context")
            )
            
            results.append(result)
            
            # Check if it qualifies
            if result["recommended_bet"] != "pass" and result["best_edge_pct"] >= edge_threshold:
                qualified_bets.append(result)
            
            logger.info(f"Analyzed prop {i+1}/{len(props)}: {result['player_name']} {result['prop_type']} - {result['recommended_bet']}")
            
        except Exception as e:
            logger.error(f"Failed to analyze prop {i+1}: {e}")
            results.append({
                "error": str(e),
                "prop_index": i
            })
    
    # Sort qualified bets by edge
    qualified_bets.sort(key=lambda x: x.get("best_edge_pct", 0), reverse=True)
    
    return {
        "total_props_analyzed": len(props),
        "qualified_bets_count": len(qualified_bets),
        "qualified_bets": qualified_bets,
        "all_results": results,
        "analysis_timestamp": datetime.now().isoformat(),
        "simulation_params": {
            "iterations_per_prop": n_iter,
            "edge_threshold": edge_threshold,
            "league": league
        }
    }


def simulate_game_with_markov(
    home_team: str,
    away_team: str,
    home_players: List[Dict[str, Any]],
    away_players: List[Dict[str, Any]],
    league: str = "NBA",
    n_iter: int = 10000,
    home_context: Optional[Any] = None,
    away_context: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Simulate a full game using Markov chains and return aggregated statistics.
    
    This provides play-by-play modeling for both teams, useful for understanding
    game flow, player involvement, and potential prop outcomes.
    
    Args:
        home_team: Home team name
        away_team: Away team name
        home_players: List of home player dicts with usage rates
        away_players: List of away player dicts
        league: League identifier
        n_iter: Number of game simulations
        home_context: Home team context (off_rating, def_rating, pace)
        away_context: Away team context
    
    Returns:
        Dict with game simulation results and player stat distributions
    """
    logger.info(f"Simulating {away_team} @ {home_team} with Markov chains ({n_iter} iterations)")
    
    # Validate team contexts
    if home_context and away_context:
        is_valid, skip_reason, issues = validate_game_for_simulation(home_context, away_context)
        if not is_valid:
            logger.warning(f"Game validation issues: {skip_reason}")
            return {
                "error": "Insufficient team data",
                "skip_reason": skip_reason,
                "issues": issues
            }
    
    # Prepare players with team side indicators
    all_players = []
    for player in home_players:
        player_copy = dict(player)
        player_copy["team_side"] = "home"
        player_copy["team"] = home_team
        all_players.append(player_copy)
    
    for player in away_players:
        player_copy = dict(player)
        player_copy["team_side"] = "away"
        player_copy["team"] = away_team
        all_players.append(player_copy)
    
    # Create simulator
    simulator = MarkovSimulator(
        league=league,
        players=all_players,
        home_context=home_context,
        away_context=away_context
    )
    
    # Run simulation
    results = simulator.run_simulation(n_iter=n_iter)
    
    # Calculate team scores from player stats
    home_score_samples = []
    away_score_samples = []
    
    for _ in range(min(n_iter, 1000)):  # Sample subset for efficiency
        state = simulator.simulate_game()
        home_score_samples.append(state.home_score)
        away_score_samples.append(state.away_score)
    
    avg_home_score = sum(home_score_samples) / len(home_score_samples) if home_score_samples else 0
    avg_away_score = sum(away_score_samples) / len(away_score_samples) if away_score_samples else 0
    
    home_wins = sum(1 for h, a in zip(home_score_samples, away_score_samples) if h > a)
    away_wins = len(home_score_samples) - home_wins
    
    return {
        "game": f"{away_team} @ {home_team}",
        "league": league,
        "simulation_iterations": n_iter,
        
        # Team results
        "home_team": home_team,
        "away_team": away_team,
        "home_win_prob": home_wins / len(home_score_samples) if home_score_samples else 0.5,
        "away_win_prob": away_wins / len(home_score_samples) if home_score_samples else 0.5,
        "avg_home_score": avg_home_score,
        "avg_away_score": avg_away_score,
        "projected_total": avg_home_score + avg_away_score,
        "projected_spread": avg_home_score - avg_away_score,
        
        # Player results
        "player_stats": results,
        
        # Metadata
        "analysis_timestamp": datetime.now().isoformat()
    }


def get_markov_prop_recommendations(
    league: str = "NBA",
    n_iter: int = 10000,
    min_edge: float = 5.0,
    top_n: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get top player prop recommendations using Markov simulation.
    
    This is a convenience function that can be called by automated workflows
    to generate daily prop recommendations.
    
    Args:
        league: League to analyze
        n_iter: Simulation iterations
        min_edge: Minimum edge threshold
        top_n: Return only top N recommendations (None = all qualified)
    
    Returns:
        Dict with top recommendations and metadata
    """
    logger.info(f"Generating Markov prop recommendations for {league}")
    
    # This would typically fetch live props from an API
    # For now, return structure with placeholder
    return {
        "league": league,
        "recommendations": [],
        "message": "Connect to props API to get live recommendations",
        "analysis_timestamp": datetime.now().isoformat(),
        "params": {
            "iterations": n_iter,
            "min_edge": min_edge,
            "top_n": top_n
        }
    }
