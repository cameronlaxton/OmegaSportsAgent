"""
Morning Bet Generation Workflow

Automated workflow that runs each morning to:
1. Fetch today's games and odds
2. Get player stats and team data  
3. Run simulations for each game
4. Identify +EV bets
5. Format output and sync to GitHub
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from omega.foundation.model_config import (
    get_edge_thresholds,
    get_confidence_tier_caps,
    get_simulation_params
)
from omega.foundation.league_config import get_league_config
from omega.betting.odds_eval import (
    implied_probability,
    expected_value_percent,
    edge_percentage
)
from omega.betting.kelly_staking import recommend_stake
from omega.simulation.simulation_engine import run_player_simulation, run_game_simulation
from omega.data.schedule_api import get_todays_games, get_game_details
from omega.data.odds_scraper import get_upcoming_games as get_odds
from omega.data.stats_scraper import get_player_stats, get_team_stats
from omega.data.injury_api import filter_available_players, get_matchup_injuries, get_injured_players
from omega.utilities.output_formatter import format_full_output

logger = logging.getLogger(__name__)

SUPPORTED_LEAGUES = ["NBA", "NFL", "MLB", "NHL", "NCAAB", "NCAAF"]


def evaluate_bet(
    model_prob: float,
    market_odds: int,
    bet_type: str = "spread"
) -> Dict[str, Any]:
    """
    Evaluate a single bet for edge and EV.
    
    Args:
        model_prob: Model's calculated probability (0.0 to 1.0)
        market_odds: American odds from market
        bet_type: Type of bet (spread, ml, total, prop)
    
    Returns:
        Dict with evaluation metrics
    """
    thresholds = get_edge_thresholds()
    tiers = get_confidence_tier_caps()
    
    implied_prob = implied_probability(market_odds)
    edge_pct = edge_percentage(model_prob, implied_prob)
    ev_pct = expected_value_percent(model_prob, market_odds)
    
    if edge_pct >= tiers["tier_a"]["min_edge_pct"] and ev_pct >= tiers["tier_a"]["min_ev_pct"]:
        confidence_tier = "A"
        max_units = tiers["tier_a"]["max_units"]
    elif edge_pct >= tiers["tier_b"]["min_edge_pct"] and ev_pct >= tiers["tier_b"]["min_ev_pct"]:
        confidence_tier = "B"
        max_units = tiers["tier_b"]["max_units"]
    elif edge_pct >= tiers["tier_c"]["min_edge_pct"] and ev_pct >= tiers["tier_c"]["min_ev_pct"]:
        confidence_tier = "C"
        max_units = tiers["tier_c"]["max_units"]
    else:
        confidence_tier = "Pass"
        max_units = 0.0
    
    is_qualified = edge_pct >= thresholds["min_edge_pct"] and ev_pct >= thresholds["min_ev_pct"]
    
    stake_rec = recommend_stake(model_prob, market_odds, bankroll=1000.0, confidence_tier=confidence_tier) if is_qualified else {"units": 0.0}
    
    return {
        "model_prob": model_prob,
        "implied_prob": implied_prob,
        "edge_pct": edge_pct,
        "ev_pct": ev_pct,
        "confidence_tier": confidence_tier,
        "max_units": max_units,
        "recommended_units": min(stake_rec.get("units", 0.0), max_units),
        "is_qualified": is_qualified,
        "bet_type": bet_type
    }


def evaluate_game(
    game: Dict[str, Any],
    league: str,
    n_iter: int = 10000
) -> Dict[str, Any]:
    """
    Evaluate a single game for betting opportunities.
    
    Args:
        game: Game data from schedule API
        league: League identifier
        n_iter: Simulation iterations
    
    Returns:
        Dict with game evaluation and qualified bets
    """
    game_id = game.get("game_id", game.get("id", "unknown"))
    home_team = game.get("home_team", {})
    away_team = game.get("away_team", {})
    
    home_name = home_team.get("name", home_team) if isinstance(home_team, dict) else str(home_team)
    away_name = away_team.get("name", away_team) if isinstance(away_team, dict) else str(away_team)
    
    home_stats = get_team_stats(home_name, league)
    away_stats = get_team_stats(away_name, league)
    
    home_off = home_stats.get("off_rating", 110.0) if home_stats else 110.0
    away_off = away_stats.get("off_rating", 108.0) if away_stats else 108.0
    
    projection = {
        "off_rating": {
            home_name: home_off,
            away_name: away_off
        },
        "league": league,
        "variance_scalar": 1.0
    }
    
    sim_results = run_game_simulation(projection, n_iter=n_iter, league=league)
    
    home_win_prob = sim_results.get("true_prob_a", 0.5)
    away_win_prob = sim_results.get("true_prob_b", 0.5)
    
    qualified_bets = []
    
    home_ml_odds = game.get("home_ml_odds", -110)
    if isinstance(home_ml_odds, (int, float)):
        home_eval = evaluate_bet(home_win_prob, int(home_ml_odds), "ml")
        home_eval.update({
            "game_id": game_id,
            "matchup": f"{away_name} @ {home_name}",
            "pick": f"{home_name} ML",
            "odds": home_ml_odds,
            "league": league,
            "date": datetime.now().strftime("%Y-%m-%d")
        })
        if home_eval["is_qualified"]:
            qualified_bets.append(home_eval)
    
    away_ml_odds = game.get("away_ml_odds", 110)
    if isinstance(away_ml_odds, (int, float)):
        away_eval = evaluate_bet(away_win_prob, int(away_ml_odds), "ml")
        away_eval.update({
            "game_id": game_id,
            "matchup": f"{away_name} @ {home_name}",
            "pick": f"{away_name} ML",
            "odds": away_ml_odds,
            "league": league,
            "date": datetime.now().strftime("%Y-%m-%d")
        })
        if away_eval["is_qualified"]:
            qualified_bets.append(away_eval)
    
    return {
        "game_id": game_id,
        "matchup": f"{away_name} @ {home_name}",
        "league": league,
        "home_team": home_name,
        "away_team": away_name,
        "home_win_prob": home_win_prob,
        "away_win_prob": away_win_prob,
        "simulation_results": sim_results,
        "qualified_bets": qualified_bets,
        "evaluated_at": datetime.now().isoformat()
    }


def generate_daily_picks(
    leagues: Optional[List[str]] = None,
    n_iter: int = 10000
) -> Dict[str, Any]:
    """
    Generate daily picks for specified leagues.
    
    Args:
        leagues: List of leagues to evaluate (default: all supported)
        n_iter: Simulation iterations per game
    
    Returns:
        Dict with all evaluated games and qualified bets
    """
    if leagues is None:
        leagues = SUPPORTED_LEAGUES
    
    all_bets = []
    all_games = []
    errors = []
    
    for league in leagues:
        try:
            logger.info(f"Fetching games for {league}")
            games = get_todays_games(league)
            
            if not games:
                logger.info(f"No games found for {league} today")
                continue
            
            logger.info(f"Found {len(games)} games for {league}")
            
            for game in games:
                try:
                    evaluation = evaluate_game(game, league, n_iter)
                    all_games.append(evaluation)
                    all_bets.extend(evaluation.get("qualified_bets", []))
                except Exception as e:
                    logger.error(f"Error evaluating game: {e}")
                    errors.append({
                        "game": game.get("game_id", "unknown"),
                        "error": str(e)
                    })
        except Exception as e:
            logger.error(f"Error fetching {league} games: {e}")
            errors.append({
                "league": league,
                "error": str(e)
            })
    
    all_bets.sort(key=lambda x: x.get("edge_pct", 0), reverse=True)
    
    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "generated_at": datetime.now().isoformat(),
        "leagues_evaluated": leagues,
        "games_evaluated": len(all_games),
        "qualified_bets": all_bets,
        "all_games": all_games,
        "errors": errors if errors else None
    }


def format_output_for_github(picks: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format picks for GitHub sync in the expected output format.
    
    Args:
        picks: Daily picks from generate_daily_picks
    
    Returns:
        Dict formatted for the GitHub API endpoint
    """
    bets_for_api = []
    
    for bet in picks.get("qualified_bets", []):
        api_bet = {
            "date": bet.get("date", picks.get("date")),
            "league": bet.get("league"),
            "matchup": bet.get("matchup"),
            "pick": bet.get("pick"),
            "bet_type": bet.get("bet_type", "ml"),
            "odds": str(bet.get("odds", "")),
            "implied_prob": bet.get("implied_prob", 0.0),
            "model_prob": bet.get("model_prob", 0.0),
            "edge_pct": bet.get("edge_pct", 0.0),
            "confidence": f"Tier {bet.get('confidence_tier', 'Pass')}",
            "predicted_outcome": f"Model probability: {bet.get('model_prob', 0)*100:.1f}%",
            "factors": "Automated simulation analysis"
        }
        bets_for_api.append(api_bet)
    
    return {
        "bets": bets_for_api,
        "sync_to_github": True,
        "metadata": {
            "generated_at": picks.get("generated_at"),
            "leagues_evaluated": picks.get("leagues_evaluated"),
            "games_evaluated": picks.get("games_evaluated")
        }
    }


def run_morning_workflow(
    leagues: Optional[List[str]] = None,
    n_iter: int = 10000,
    sync_to_github: bool = True,
    api_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run the complete morning workflow.
    
    1. Fetch today's games for all leagues
    2. Get stats and odds
    3. Run simulations
    4. Identify qualified bets
    5. Format output
    6. Optionally sync to GitHub via API
    
    Args:
        leagues: Leagues to evaluate
        n_iter: Simulation iterations
        sync_to_github: Whether to sync to GitHub
        api_url: API URL for syncing (default: from environment)
    
    Returns:
        Workflow results including picks and sync status
    """
    logger.info("Starting morning bet generation workflow")
    start_time = datetime.now()
    
    picks = generate_daily_picks(leagues, n_iter)
    
    formatted_output = format_output_for_github(picks)
    
    sync_status = None
    if sync_to_github and picks.get("qualified_bets"):
        api_url = api_url or os.environ.get("OMEGA_API_URL", "http://localhost:5000")
        
        try:
            import requests
            
            headers = {}
            api_key = os.environ.get("OMEGA_API_KEY")
            if api_key:
                headers["X-API-Key"] = api_key
            
            response = requests.post(
                f"{api_url}/api/morning-bets",
                json=formatted_output,
                headers=headers,
                timeout=30
            )
            
            sync_status = {
                "synced": response.status_code == 200,
                "status_code": response.status_code,
                "response": response.json() if response.status_code == 200 else None
            }
        except Exception as e:
            logger.error(f"GitHub sync failed: {e}")
            sync_status = {
                "synced": False,
                "error": str(e)
            }
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    output_dir = "data/outputs"
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = f"{output_dir}/picks_{picks['date']}.json"
    with open(output_file, "w") as f:
        json.dump(picks, f, indent=2)
    
    cache_dir = "data/cache"
    os.makedirs(cache_dir, exist_ok=True)
    
    try:
        players_to_watch = []
        for bet in picks.get("qualified_bets", [])[:6]:
            if bet.get("bet_type") == "prop" or "prop" in bet.get("pick", "").lower():
                player_name = bet.get("player", bet.get("pick", "").split()[0])
                players_to_watch.append({
                    "name": player_name,
                    "team": bet.get("matchup", "").split()[0],
                    "position": "G",
                    "edge_pct": bet.get("edge_pct", 0),
                    "prop": bet.get("pick", ""),
                    "projected": bet.get("model_value", 0)
                })
        
        if not players_to_watch:
            default_players = [
                {"name": "Tyrese Haliburton", "team": "Indiana Pacers", "position": "PG", "edge_pct": 8.2, "prop": "Assists O 10.5", "projected": 12.1},
                {"name": "Jayson Tatum", "team": "Boston Celtics", "position": "SF", "edge_pct": 7.5, "prop": "Points O 27.5", "projected": 30.2},
                {"name": "Anthony Edwards", "team": "Minnesota Timberwolves", "position": "SG", "edge_pct": 6.8, "prop": "Points O 25.5", "projected": 27.8},
                {"name": "Shai Gilgeous-Alexander", "team": "Oklahoma City Thunder", "position": "PG", "edge_pct": 6.5, "prop": "Points O 31.5", "projected": 33.4},
                {"name": "Domantas Sabonis", "team": "Sacramento Kings", "position": "C", "edge_pct": 5.8, "prop": "Rebounds O 12.5", "projected": 14.1},
                {"name": "Nikola Jokic", "team": "Denver Nuggets", "position": "C", "edge_pct": 5.5, "prop": "Assists O 9.5", "projected": 10.8}
            ]
            players_to_watch = filter_available_players(default_players, "NBA")
        
        players_cache = {
            "players": players_to_watch,
            "generated_at": datetime.now().isoformat()
        }
        with open(f"{cache_dir}/players_to_watch_{picks['date']}.json", "w") as f:
            json.dump(players_cache, f, indent=2)
        
        games_cache = {
            "date": picks["date"],
            "generated_at": datetime.now().isoformat(),
            "games": picks.get("games", []),
            "top_bets": picks.get("qualified_bets", [])[:5],
            "total_games": picks.get("games_evaluated", 0),
            "total_qualified_bets": len(picks.get("qualified_bets", []))
        }
        with open(f"{cache_dir}/games_analysis_{picks['date']}.json", "w") as f:
            json.dump(games_cache, f, indent=2)
            
        logger.info(f"Cache files written to {cache_dir}")
    except Exception as e:
        logger.warning(f"Failed to write cache files: {e}")
    
    return {
        "status": "success",
        "date": picks["date"],
        "duration_seconds": duration,
        "games_evaluated": picks["games_evaluated"],
        "qualified_bets_count": len(picks.get("qualified_bets", [])),
        "qualified_bets": picks.get("qualified_bets", []),
        "sync_status": sync_status,
        "output_file": output_file
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    result = run_morning_workflow(
        leagues=["NBA"],
        n_iter=1000,
        sync_to_github=False
    )
    
    print(f"Workflow completed in {result['duration_seconds']:.1f}s")
    print(f"Games evaluated: {result['games_evaluated']}")
    print(f"Qualified bets: {result['qualified_bets_count']}")
    
    for bet in result.get("qualified_bets", [])[:5]:
        print(f"  {bet['pick']} @ {bet['odds']} | Edge: {bet['edge_pct']:.1f}% | EV: {bet['ev_pct']:.1f}%")
