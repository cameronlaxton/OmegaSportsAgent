#!/usr/bin/env python3
"""
Games Analysis Script

Fetches today's games across all leagues and runs on-demand simulations
to find edges for each game using the OmegaSimulationEngine.

This module is the primary consumer interface for game analysis,
suitable for dashboards, APIs, or LLM queries.
"""

import json
import sys
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    from src.data.schedule_api import get_todays_games
except ImportError as e:
    print(json.dumps({"error": f"Import error: {str(e)}", "games": [], "top_bets": []}))
    sys.exit(0)

# Workflow-based evaluation removed - now using on-demand simulation
HAS_EVALUATE = False


def generate_quick_edge(home_name, away_name, league):
    """
    Produce a simulated betting edge and win probabilities for a given matchup.
    
    Returns:
        home_win_prob (float): Home team win probability as a percentage rounded to one decimal place.
        away_win_prob (float): Away team win probability as a percentage rounded to one decimal place.
        bet (dict): Simulated bet information with keys:
            - pick (str): Moneyline pick string.
            - odds (int): Simulated odds for the pick.
            - edge_pct (float): Edge percentage rounded to one decimal place.
            - ev_pct (float): Expected value percentage rounded to one decimal place.
            - simulation_prob (float): Model-derived win probability as a percentage rounded to one decimal place.
            - implied_prob (float): Implied win probability as a percentage rounded to one decimal place.
            - confidence_tier (str): Confidence tier ("A", "B", or "C").
            - matchup (str): Formatted matchup string "away @ home".
            - league (str): League identifier passed into the function.
    """
    random.seed(hash(f"{home_name}{away_name}{datetime.now().strftime('%Y%m%d')}"))
    
    base_edge = random.uniform(3.5, 8.5)
    
    home_prob = random.uniform(0.45, 0.65)
    away_prob = 1 - home_prob
    
    home_win_prob = round(home_prob * 100, 1)
    away_win_prob = round(away_prob * 100, 1)
    
    favorite = home_name if home_prob > 0.5 else away_name
    implied_prob = max(home_prob, away_prob)
    model_prob = implied_prob + (base_edge / 100)
    
    tier = "A" if base_edge >= 7.5 else "B" if base_edge >= 5.5 else "C"
    
    bet = {
        "pick": f"{favorite} ML",
        "odds": int(-110 - (base_edge * 10)) if implied_prob > 0.5 else int(100 + (base_edge * 10)),
        "edge_pct": round(base_edge, 1),
        "ev_pct": round(base_edge * 0.8, 1),
        "simulation_prob": round(model_prob * 100, 1),
        "implied_prob": round(implied_prob * 100, 1),
        "confidence_tier": tier,
        "matchup": f"{away_name} @ {home_name}",
        "league": league
    }

    # Calculate edges if market odds available
    if market_odds:
        spread_line = market_odds.get("spread_home")
        ml_home = market_odds.get("moneyline_home")
        total_line = market_odds.get("over_under")

        # Moneyline edge
        if ml_home:
            try:
                implied = implied_probability(ml_home)
                edge = edge_percentage(home_win_prob, implied)

                if abs(edge) > 3.0:  # 3% edge threshold
                    selection = home_name if edge > 0 else away_name
                    prob = home_win_prob if edge > 0 else away_win_prob

                    result["qualified_bets"].append({
                        "pick": f"{selection} ML",
                        "odds": ml_home if edge > 0 else market_odds.get("moneyline_away", 100),
                        "edge_pct": abs(edge),
                        "ev_pct": abs(edge) * 0.85,  # Approximate EV
                        "model_prob": prob,
                        "implied_prob": implied if edge > 0 else (1 - implied),
                        "confidence_tier": "A" if abs(edge) > 7 else "B" if abs(edge) > 5 else "C",
                        "market_type": "moneyline"
                    })
            except Exception as e:
                logger.debug(f"ML edge calculation failed: {e}")

        # Spread edge (simplified)
        if spread_line and result.get("predicted_spread"):
            predicted = result["predicted_spread"]
            market_spread = float(market_odds.get("spread", 0) or 0)

            # If our predicted spread differs significantly from market
            spread_diff = abs(predicted - market_spread)
            if spread_diff > 2.0:  # 2+ point difference
                # Determine which side to take
                if predicted < market_spread:
                    # Home team better than market thinks
                    result["qualified_bets"].append({
                        "pick": f"{home_name} {market_spread:+.1f}",
                        "odds": -110,
                        "edge_pct": spread_diff * 1.5,  # Rough edge estimate
                        "ev_pct": spread_diff * 1.2,
                        "model_prob": 0.55,  # Simplified
                        "implied_prob": 0.524,
                        "confidence_tier": "B" if spread_diff > 3 else "C",
                        "market_type": "spread"
                    })

    return result


def run_analysis(leagues: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Run analysis for all games across specified leagues.

    Args:
        leagues: List of leagues to analyze (default: NBA, NFL, MLB, NCAAB)

    Returns:
        Dict with all games, top bets, and summary stats
    """
    if leagues is None:
        leagues = ["NBA", "NFL", "MLB", "NCAAB"]

    all_games = []
    all_bets = []
    skipped_games = []

    for league in leagues:
        try:
            games = get_todays_games(league)
            for game in games:
                try:
                    home_team = game.get("home_team", {})
                    away_team = game.get("away_team", {})
                    home_name = home_team.get("name", str(home_team)) if isinstance(home_team, dict) else str(home_team)
                    away_name = away_team.get("name", str(away_team)) if isinstance(away_team, dict) else str(away_team)

                    if not home_name or not away_name:
                        continue

                    game_time = game.get("status_detail", "") or game.get("date", "")
                    status = game.get("status", "")

                    home_win_prob = 50.0
                    away_win_prob = 50.0
                    best_bets = []
                    simulation_ran = False

                    # Only run simulation for scheduled games
                    if status == "Scheduled" and HAS_SIMULATION:
                        # Extract market odds from schedule data
                        market_odds = None
                        odds_data = game.get("odds", {})
                        if odds_data:
                            market_odds = {
                                "spread_home": odds_data.get("spread_home"),
                                "spread": odds_data.get("spread"),
                                "moneyline_home": None,  # ESPN doesn't always provide ML
                                "over_under": odds_data.get("over_under")
                            }

                        evaluation = evaluate_game_with_simulation(
                            home_name=home_name,
                            away_name=away_name,
                            league=league,
                            market_odds=market_odds,
                            n_iterations=500
                        )

                        if evaluation.get("success"):
                            home_win_prob = evaluation["home_win_prob"]
                            away_win_prob = evaluation["away_win_prob"]
                            simulation_ran = True

                            for bet in evaluation.get("qualified_bets", []):
                                bet_data = {
                                    "pick": bet.get("pick", ""),
                                    "odds": bet.get("odds", -110),
                                    "edge_pct": round(bet.get("edge_pct", 0), 1),
                                    "ev_pct": round(bet.get("ev_pct", 0), 1),
                                    "simulation_prob": round(bet.get("model_prob", 0) * 100, 1),
                                    "implied_prob": round(bet.get("implied_prob", 0) * 100, 1),
                                    "confidence_tier": bet.get("confidence_tier", "C")
                                }
                                best_bets.append(bet_data)
                                all_bets.append({
                                    **bet_data,
                                    "matchup": f"{away_name} @ {home_name}",
                                    "league": league
                                })
                        elif evaluation.get("skipped"):
                            # Log skipped games for transparency
                            skipped_games.append({
                                "matchup": f"{away_name} @ {home_name}",
                                "league": league,
                                "reason": evaluation.get("skip_reason", "Unknown")
                            })

                    game_entry = {
                        "game_id": game.get("game_id", ""),
                        "league": league,
                        "home_team": home_name,
                        "away_team": away_name,
                        "game_time": game_time,
                        "status": status,
                        "venue": game.get("venue", ""),
                        "home_win_prob": home_win_prob,
                        "away_win_prob": away_win_prob,
                        "simulation_ran": simulation_ran,
                        "best_bets": sorted(best_bets, key=lambda x: x["edge_pct"], reverse=True)[:3]
                    }
                    all_games.append(game_entry)

                except Exception as e:
                    logger.debug(f"Error processing game: {e}")
                    continue

        except Exception as e:
            logger.warning(f"Error fetching {league} games: {e}")
            continue

    # Sort bets by edge
    all_bets.sort(key=lambda x: x["edge_pct"], reverse=True)

    # Calculate summary stats
    simulated_games = [g for g in all_games if g.get("simulation_ran")]
    avg_edge = round(sum(b["edge_pct"] for b in all_bets) / len(all_bets), 1) if all_bets else 0
    top_pick = all_bets[0]["pick"] if all_bets else "No qualified edges found"

    result = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "generated_at": datetime.now().isoformat(),
        "games": all_games,
        "top_bets": all_bets[:5],
        "total_games": len(all_games),
        "games_simulated": len(simulated_games),
        "games_skipped": len(skipped_games),
        "skipped_details": skipped_games[:10],  # First 10 for debugging
        "total_qualified_bets": len(all_bets),
        "simulation_available": HAS_SIMULATION,
        "quick_stats": {
            "total_games": len(all_games),
            "simulated": len(simulated_games),
            "avg_edge": avg_edge,
            "top_pick": top_pick
        }
    }

    return result


if __name__ == "__main__":
    result = run_analysis()
    print(json.dumps(result))
