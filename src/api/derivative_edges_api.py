"""
Derivative Edges API

CLI endpoint for calculating 1Q/1H betting edge opportunities.
Called by server.js to provide derivative edge analysis.
"""

import argparse
import json
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional

sys.path.insert(0, '.')

from src.data.schedule_api import get_todays_games
from src.data.stats_ingestion import get_team_context
from src.analysis.derivative_analyzer import DerivativeEdgeAnalyzer


def calculate_derivative_edges(league: str = "all", game_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Calculate derivative edges for today's games.
    
    Args:
        league: League filter ("NBA", "NFL", or "all")
        game_id: Optional specific game ID to analyze
    
    Returns:
        Dictionary with success status and edges array
    """
    edges = []
    leagues_to_check = ["NBA", "NFL"] if league.lower() == "all" else [league.upper()]
    
    for current_league in leagues_to_check:
        if current_league not in ["NBA", "NFL"]:
            continue
            
        try:
            games = get_todays_games(current_league)
            
            for game in games:
                current_game_id = game.get("game_id", "")
                
                if game_id and current_game_id != game_id:
                    continue
                
                home_team_data = game.get("home_team", {})
                away_team_data = game.get("away_team", {})
                
                home_team = home_team_data.get("name", "") if isinstance(home_team_data, dict) else str(home_team_data)
                away_team = away_team_data.get("name", "") if isinstance(away_team_data, dict) else str(away_team_data)
                
                if not home_team or not away_team:
                    continue
                
                odds_data = game.get("odds", {})
                fg_spread = odds_data.get("spread_home")
                
                if fg_spread is None:
                    spread_str = odds_data.get("spread", "")
                    if spread_str:
                        try:
                            parts = spread_str.split()
                            for part in parts:
                                if part.startswith("-") or part.startswith("+"):
                                    fg_spread = float(part)
                                    break
                        except:
                            pass
                
                if fg_spread is None:
                    fg_spread = 0.0
                
                try:
                    home_context = get_team_context(home_team, current_league)
                    away_context = get_team_context(away_team, current_league)
                    
                    analyzer = DerivativeEdgeAnalyzer(
                        league=current_league,
                        n_simulations=200,
                        home_context=home_context.to_dict() if home_context else None,
                        away_context=away_context.to_dict() if away_context else None
                    )
                    
                    game_id_formatted = f"{datetime.now().strftime('%Y-%m-%d')}_{current_league}_{home_team.split()[-1][:3].upper()}_{away_team.split()[-1][:3].upper()}"
                    
                    derivative_edge = analyzer.calculate_derivative_edges(
                        game_id=game_id_formatted,
                        home_team=home_team,
                        away_team=away_team,
                        fg_spread=float(fg_spread)
                    )
                    
                    game_time = game.get("status_detail", "") or game.get("date", "")
                    
                    if abs(derivative_edge.edge_1q) >= 0.5:
                        edge_direction = "under" if derivative_edge.edge_1q < 0 else "over"
                        edges.append({
                            "game_id": game_id_formatted,
                            "home_team": home_team,
                            "away_team": away_team,
                            "league": current_league,
                            "game_time": game_time,
                            "fg_spread": float(fg_spread),
                            "derivative": "1Q",
                            "book_line": derivative_edge.book_1q_spread,
                            "model_line": derivative_edge.model_1q_spread,
                            "edge": abs(derivative_edge.edge_1q),
                            "edge_raw": derivative_edge.edge_1q,
                            "edge_direction": edge_direction,
                            "confidence": derivative_edge.confidence,
                            "factors": derivative_edge.factors[:4]
                        })
                    
                    if abs(derivative_edge.edge_1h) >= 0.5:
                        edge_direction = "under" if derivative_edge.edge_1h < 0 else "over"
                        edges.append({
                            "game_id": game_id_formatted,
                            "home_team": home_team,
                            "away_team": away_team,
                            "league": current_league,
                            "game_time": game_time,
                            "fg_spread": float(fg_spread),
                            "derivative": "1H",
                            "book_line": derivative_edge.book_1h_spread,
                            "model_line": derivative_edge.model_1h_spread,
                            "edge": abs(derivative_edge.edge_1h),
                            "edge_raw": derivative_edge.edge_1h,
                            "edge_direction": edge_direction,
                            "confidence": derivative_edge.confidence,
                            "factors": derivative_edge.factors[:4]
                        })
                        
                except Exception as e:
                    continue
                    
        except Exception as e:
            continue
    
    edges.sort(key=lambda x: x["edge"], reverse=True)
    
    return {
        "success": True,
        "league": league.upper() if league.lower() != "all" else "ALL",
        "generated_at": datetime.now().isoformat() + "Z",
        "total_edges": len(edges),
        "edges": edges
    }


def main():
    parser = argparse.ArgumentParser(description="Calculate derivative betting edges")
    parser.add_argument("--league", default="all", help="League filter (NBA, NFL, or all)")
    parser.add_argument("--game-id", default=None, help="Specific game ID to analyze")
    
    args = parser.parse_args()
    
    result = calculate_derivative_edges(
        league=args.league,
        game_id=args.game_id
    )
    
    print(json.dumps(result))


if __name__ == "__main__":
    main()
