#!/usr/bin/env python
"""
Comprehensive Game Analysis Module

Aggregates all analysis for a game:
- Narrative intelligence (storylines, matchup breakdowns)
- Game bets (ML, spread, totals with edge calculations)
- Player props (simulation-based recommendations)
- SGP correlation data
"""

import json
import sys
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

sys.path.insert(0, '.')

from omega.narratives.narrative_engine import NarrativeEngine, generate_narrative
from omega.data.schedule_api import get_todays_games
from omega.chat.prop_recommendations import PropRecommendationService

logger = logging.getLogger(__name__)


SGP_CORRELATIONS = {
    ("team_ml", "team_spread"): 0.85,
    ("team_ml", "team_over"): 0.45,
    ("team_ml", "player_points_over"): 0.35,
    ("team_ml", "player_assists_over"): 0.25,
    ("team_spread", "team_over"): 0.30,
    ("team_spread", "player_points_over"): 0.30,
    ("team_over", "player_points_over"): 0.55,
    ("team_over", "player_rebounds_over"): 0.40,
    ("player_points_over", "player_rebounds_over"): 0.15,
    ("player_points_over", "player_assists_over"): 0.20,
    ("team_ml", "opp_player_points_under"): 0.25,
    ("team_ml", "opp_player_assists_under"): 0.20,
}


class GameAnalysisService:
    """Comprehensive game analysis aggregator."""
    
    def __init__(self, league: str = "NBA"):
        self.league = league
        self.narrative_engine = NarrativeEngine()
        self.prop_service = PropRecommendationService(league=league, n_simulations=500)
    
    def get_game_bets(self, game: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate game-level bet recommendations (ML, Spread, Total)."""
        home_team = game.get("home_team", {})
        away_team = game.get("away_team", {})
        
        if isinstance(home_team, dict):
            home_name = home_team.get("name", str(home_team))
        else:
            home_name = str(home_team)
        
        if isinstance(away_team, dict):
            away_name = away_team.get("name", str(away_team))
        else:
            away_name = str(away_team)
        
        home_form = self.narrative_engine.get_team_form(home_name)
        away_form = self.narrative_engine.get_team_form(away_name)
        
        home_net = home_form.net_rating()
        away_net = away_form.net_rating()
        
        net_diff = home_net - away_net
        home_advantage = 3.0
        
        projected_margin = (net_diff + home_advantage) / 2
        
        home_win_prob = 0.5 + (projected_margin / 20)
        home_win_prob = max(0.2, min(0.8, home_win_prob))
        away_win_prob = 1 - home_win_prob
        
        bets = []
        
        ml_implied = 0.524
        ml_edge = (home_win_prob - ml_implied) * 100
        if ml_edge > 3:
            bets.append({
                "bet_type": "moneyline",
                "pick": f"{home_name} ML",
                "team": home_name,
                "odds": "-110",
                "projected_prob": round(home_win_prob * 100, 1),
                "implied_prob": round(ml_implied * 100, 1),
                "edge_pct": round(ml_edge, 1),
                "confidence": "A" if ml_edge >= 8 else "B" if ml_edge >= 5 else "C",
                "narrative": f"Model projects {home_name} with {home_win_prob*100:.0f}% win probability at home."
            })
        elif ml_edge < -3:
            away_edge = (away_win_prob - ml_implied) * 100
            bets.append({
                "bet_type": "moneyline",
                "pick": f"{away_name} ML",
                "team": away_name,
                "odds": "+110",
                "projected_prob": round(away_win_prob * 100, 1),
                "implied_prob": round(ml_implied * 100, 1),
                "edge_pct": round(away_edge, 1),
                "confidence": "A" if away_edge >= 8 else "B" if away_edge >= 5 else "C",
                "narrative": f"Value on {away_name} as road underdog with {away_win_prob*100:.0f}% projected win rate."
            })
        
        spread_line = round(-projected_margin * 0.8, 1)
        if abs(projected_margin) > 2:
            spread_edge = abs(projected_margin - spread_line) / 2
            favorite = home_name if projected_margin > 0 else away_name
            bets.append({
                "bet_type": "spread",
                "pick": f"{favorite} {spread_line:+.1f}",
                "team": favorite,
                "line": spread_line,
                "projected_margin": round(projected_margin, 1),
                "odds": "-110",
                "edge_pct": round(spread_edge, 1),
                "confidence": "A" if spread_edge >= 8 else "B" if spread_edge >= 5 else "C",
                "narrative": f"Model projects {round(projected_margin, 1)} point margin, line is {spread_line}."
            })
        
        projected_total = (home_form.points_per_game + away_form.points_per_game + 
                         home_form.points_allowed + away_form.points_allowed) / 4
        
        pace_factor = (home_form.pace + away_form.pace) / 200
        projected_total *= pace_factor
        
        total_line = round(projected_total * 0.98 * 2) / 2
        total_diff = projected_total - total_line
        total_edge = abs(total_diff) / 2
        
        if abs(total_diff) > 1:
            pick = "OVER" if total_diff > 0 else "UNDER"
            bets.append({
                "bet_type": "total",
                "pick": f"{pick} {total_line}",
                "line": total_line,
                "projected_total": round(projected_total, 1),
                "odds": "-110",
                "edge_pct": round(total_edge, 1),
                "confidence": "A" if total_edge >= 8 else "B" if total_edge >= 5 else "C",
                "narrative": f"Projected total of {projected_total:.1f} suggests {pick.lower()} value."
            })
        
        return bets
    
    def get_prop_recommendations(self, game: Dict[str, Any]) -> Dict[str, Any]:
        """Get player prop recommendations for a game."""
        home_team = game.get("home_team", {})
        away_team = game.get("away_team", {})
        
        if isinstance(home_team, dict):
            home_name = home_team.get("name", "")
        else:
            home_name = str(home_team)
        
        if isinstance(away_team, dict):
            away_name = away_team.get("name", "")
        else:
            away_name = str(away_team)
        
        team_query = home_name.split()[-1] if home_name else away_name.split()[-1]
        
        try:
            result = self.prop_service.get_recommendations(f"props for {team_query}")
            return result
        except Exception as e:
            logger.error(f"Error getting props: {e}")
            return {"success": False, "error": str(e), "recommendations": []}
    
    def get_correlation_data(self) -> Dict[str, Any]:
        """Get SGP correlation matrix data."""
        correlations = []
        
        for (leg1, leg2), corr in SGP_CORRELATIONS.items():
            direction = "positive" if corr > 0 else "negative"
            strength = "strong" if abs(corr) > 0.5 else "moderate" if abs(corr) > 0.3 else "weak"
            
            correlations.append({
                "leg1_type": leg1,
                "leg2_type": leg2,
                "correlation": corr,
                "direction": direction,
                "strength": strength,
                "description": self._describe_correlation(leg1, leg2, corr)
            })
        
        return {
            "correlations": correlations,
            "warning": "SGP odds are often not properly adjusted for correlations. Positive correlations mean legs are more likely to hit together than independent probability suggests."
        }
    
    def _describe_correlation(self, leg1: str, leg2: str, corr: float) -> str:
        """Generate human-readable correlation description."""
        descriptions = {
            ("team_ml", "team_spread"): "Teams that win usually cover the spread",
            ("team_ml", "team_over"): "Winning teams often score more, pushing totals higher",
            ("team_ml", "player_points_over"): "Star players on winning teams often score more",
            ("team_over", "player_points_over"): "High-scoring games mean more player points",
            ("team_over", "player_rebounds_over"): "More possessions mean more rebounding opportunities",
            ("player_points_over", "player_rebounds_over"): "Active players get more stats across the board",
        }
        return descriptions.get((leg1, leg2), f"Correlation coefficient: {corr:.2f}")
    
    def calculate_sgp_ev(self, legs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate adjusted EV for a same-game parlay."""
        if len(legs) < 2:
            return {"error": "Need at least 2 legs for SGP"}
        
        naive_prob = 1.0
        for leg in legs:
            naive_prob *= leg.get("model_prob", 0.5)
        
        total_correlation = 0
        correlation_count = 0
        warnings = []
        
        for i, leg1 in enumerate(legs):
            for leg2 in legs[i+1:]:
                leg1_type = leg1.get("type", "unknown")
                leg2_type = leg2.get("type", "unknown")
                
                corr = SGP_CORRELATIONS.get((leg1_type, leg2_type), 0)
                if corr == 0:
                    corr = SGP_CORRELATIONS.get((leg2_type, leg1_type), 0)
                
                total_correlation += corr
                correlation_count += 1
                
                if corr < -0.2:
                    warnings.append(f"Negative correlation between {leg1_type} and {leg2_type}")
        
        avg_correlation = total_correlation / max(correlation_count, 1)
        
        correlation_factor = 1 + (avg_correlation * 0.3)
        adjusted_prob = naive_prob * correlation_factor
        adjusted_prob = min(adjusted_prob, 0.95)
        
        implied_odds = 1 / naive_prob if naive_prob > 0 else 999
        
        ev = (adjusted_prob * implied_odds) - 1
        
        return {
            "naive_probability": round(naive_prob * 100, 2),
            "adjusted_probability": round(adjusted_prob * 100, 2),
            "average_correlation": round(avg_correlation, 3),
            "implied_odds": f"+{int((implied_odds - 1) * 100)}" if implied_odds > 2 else f"{int(-100 / (implied_odds - 1))}",
            "expected_value": round(ev * 100, 1),
            "recommendation": "Favorable" if ev > 0.05 else "Neutral" if ev > -0.05 else "Avoid",
            "warnings": warnings
        }
    
    def analyze_game(self, game: Dict[str, Any]) -> Dict[str, Any]:
        """Generate complete analysis for a single game."""
        narrative_data = generate_narrative(game)
        
        game_bets = self.get_game_bets(game)
        
        props_data = self.get_prop_recommendations(game)
        
        correlation_data = self.get_correlation_data()
        
        home_team = game.get("home_team", {})
        away_team = game.get("away_team", {})
        if isinstance(home_team, dict):
            home_name = home_team.get("name", str(home_team))
        else:
            home_name = str(home_team)
        if isinstance(away_team, dict):
            away_name = away_team.get("name", str(away_team))
        else:
            away_name = str(away_team)
        
        return {
            "game_id": game.get("game_id", ""),
            "home_team": home_name,
            "away_team": away_name,
            "game_time": game.get("status_detail", "") or game.get("date", ""),
            "venue": game.get("venue", ""),
            "status": game.get("status", ""),
            "narrative": narrative_data,
            "game_bets": game_bets,
            "player_props": props_data,
            "sgp_correlations": correlation_data,
            "generated_at": datetime.now().isoformat()
        }
    
    def analyze_all_games(self) -> Dict[str, Any]:
        """Analyze all games for today."""
        games = get_todays_games(self.league)
        
        analyses = []
        players_to_watch = []
        
        for game in games:
            try:
                analysis = self.analyze_game(game)
                analyses.append(analysis)
                
                if analysis.get("player_props", {}).get("success"):
                    for prop in analysis["player_props"].get("recommendations", [])[:2]:
                        if prop.get("edge_pct", 0) >= 5:
                            players_to_watch.append({
                                "player": prop.get("player"),
                                "team": prop.get("team"),
                                "matchup": f"{analysis['away_team']} @ {analysis['home_team']}",
                                "prop": f"{prop.get('market')} {prop.get('recommendation')} {prop.get('line')}",
                                "edge_pct": prop.get("edge_pct"),
                                "confidence": prop.get("confidence"),
                                "reason": f"{prop.get('edge_pct')}% edge on {prop.get('market').lower()}"
                            })
            except Exception as e:
                logger.error(f"Error analyzing game: {e}")
                continue
        
        players_to_watch.sort(key=lambda x: x.get("edge_pct", 0), reverse=True)
        
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "league": self.league,
            "total_games": len(analyses),
            "games": analyses,
            "players_to_watch": players_to_watch[:5],
            "generated_at": datetime.now().isoformat()
        }


def get_game_analysis(game_id: Optional[str] = None, team: Optional[str] = None) -> Dict[str, Any]:
    """Get analysis for a specific game or all games."""
    service = GameAnalysisService()
    
    if game_id or team:
        games = get_todays_games("NBA")
        for game in games:
            if game.get("game_id") == game_id:
                return service.analyze_game(game)
            
            if team:
                team_lower = team.lower()
                home = game.get("home_team", {})
                away = game.get("away_team", {})
                home_name = home.get("name", str(home)) if isinstance(home, dict) else str(home)
                away_name = away.get("name", str(away)) if isinstance(away, dict) else str(away)
                
                if team_lower in home_name.lower() or team_lower in away_name.lower():
                    return service.analyze_game(game)
        
        return {"error": f"Game not found for {game_id or team}"}
    
    return service.analyze_all_games()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--game-id", help="Specific game ID")
    parser.add_argument("--team", help="Team name to find game")
    args = parser.parse_args()
    
    result = get_game_analysis(game_id=args.game_id, team=args.team)
    print(json.dumps(result, indent=2, default=str))
