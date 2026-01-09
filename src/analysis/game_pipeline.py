"""
GameAnalysisPipeline - Professional Sports Betting Analysis

This pipeline wraps all existing omega modules to produce structured
betting recommendations with proper edge/EV calculations.

Flow: context → odds → simulation → calibrate → edge/EV → filter → output
"""

import json
import sys
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

sys.path.insert(0, '.')

from src.simulation.simulation_engine import OmegaSimulationEngine
from src.betting.odds_eval import (
    implied_probability,
    expected_value_percent,
    edge_percentage,
    american_to_decimal
)
from src.betting.kelly_staking import recommend_stake
from src.modeling.probability_calibration import calibrate_probability
from src.foundation.model_config import (
    get_edge_thresholds,
    get_confidence_tier_caps,
    get_simulation_params
)
from src.data.injury_api import get_matchup_injuries
from src.data.odds_scraper import get_upcoming_games as get_odds_data
from src.data.cache_service import DataCacheService

logger = logging.getLogger(__name__)

DEFAULT_ODDS = -110
BANKROLL = 1000.0


class GameAnalysisPipeline:
    """
    Professional game analysis pipeline that outputs structured betting recommendations.
    
    Uses:
    - OmegaSimulationEngine for Monte Carlo simulations
    - Probability calibration (shrinkage toward 0.5)
    - Edge/EV calculations from odds_eval
    - Kelly staking recommendations
    - Threshold filtering (3% edge min, 2.5% EV min)
    """
    
    def __init__(self, n_iterations: int = 1000, calibration_method: str = "shrinkage"):
        self.engine = OmegaSimulationEngine()
        self.n_iterations = n_iterations
        self.calibration_method = calibration_method
        self.thresholds = get_edge_thresholds()
        self.tier_caps = get_confidence_tier_caps()
        self.cache = DataCacheService()
    
    def analyze(
        self,
        team_a: str,
        team_b: str,
        league: str = "NBA",
        include_player_props: bool = True
    ) -> Dict[str, Any]:
        """
        Run full analysis pipeline for a matchup.
        
        Args:
            team_a: First team name (will be determined as home/away)
            team_b: Second team name
            league: League code (NBA, NFL, etc.)
            include_player_props: Whether to include player prop analysis
        
        Returns:
            Structured JSON with game_bets, player_props, context_drivers,
            simulation_summary, risk_assessment, rejected_bets
        """
        try:
            home_team, away_team = self._determine_home_away(team_a, team_b, league)
            
            injuries = self._get_injuries(home_team, away_team, league)
            
            odds_data = self._get_odds(home_team, away_team, league)
            
            home_context, away_context = self._get_cached_team_stats(home_team, away_team, league)
            
            sim_result = self.engine.run_fast_game_simulation(
                home_team=home_team,
                away_team=away_team,
                league=league,
                n_iterations=self.n_iterations,
                home_context=home_context,
                away_context=away_context
            )
            
            if sim_result.get("skipped") or not sim_result.get("success", True):
                sim_result = self._run_fallback_simulation(home_team, away_team, league)
            
            game_bets, rejected_game_bets = self._evaluate_game_bets(
                sim_result, odds_data, home_team, away_team, league
            )
            
            player_props = []
            rejected_prop_bets = []
            if include_player_props:
                player_props, rejected_prop_bets = self._evaluate_player_props(
                    home_team, away_team, league, odds_data
                )
            
            context_drivers = self._build_context_drivers(
                home_team, away_team, injuries, sim_result
            )
            
            simulation_summary = self._build_simulation_summary(
                sim_result, home_team, away_team, odds_data
            )
            
            all_bets = game_bets + player_props
            risk_assessment = self._build_risk_assessment(all_bets)
            
            rejected_bets = rejected_game_bets + rejected_prop_bets
            
            return {
                "success": True,
                "matchup": f"{home_team} vs {away_team}",
                "league": league.upper(),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "game_bets": game_bets,
                "player_props": player_props,
                "context_drivers": context_drivers,
                "simulation_summary": simulation_summary,
                "risk_assessment": risk_assessment,
                "rejected_bets": rejected_bets
            }
        
        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "matchup": f"{team_a} vs {team_b}",
                "league": league.upper(),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
    
    def _determine_home_away(self, team_a: str, team_b: str, league: str) -> tuple:
        """
        Determine which team is home vs away.
        For now, assumes team_a is home. In production, would check schedule API.
        """
        return team_a, team_b
    
    def _get_cached_team_stats(
        self, home_team: str, away_team: str, league: str
    ) -> tuple:
        """
        Get cached team stats for both teams if available.
        
        Returns:
            Tuple of (home_context, away_context) dicts, or (None, None) if not cached
        """
        cache_key = f"team_stats:{league.upper()}:all"
        
        try:
            cached_data = self.cache.get_cached(cache_key)
            if cached_data and "teams" in cached_data:
                teams_data = cached_data["teams"]
                home_context = None
                away_context = None
                
                for team_name, team_data in teams_data.items():
                    team_lower = team_name.lower()
                    home_lower = home_team.lower()
                    away_lower = away_team.lower()
                    
                    if team_lower == home_lower or home_lower in team_lower or team_lower in home_lower:
                        home_context = team_data
                    elif team_lower == away_lower or away_lower in team_lower or team_lower in away_lower:
                        away_context = team_data
                
                if home_context and away_context:
                    logger.debug(f"Using cached team stats for {home_team} vs {away_team}")
                    return home_context, away_context
            
            return None, None
        except Exception as e:
            logger.warning(f"Could not get cached team stats: {e}")
            return None, None
    
    def close(self) -> None:
        """Close the cache connection pool."""
        if self.cache:
            self.cache.close()
            logger.debug("GameAnalysisPipeline cache connection closed")
    
    def _run_fallback_simulation(self, home_team: str, away_team: str, league: str) -> Dict[str, Any]:
        """
        Run a simple Monte Carlo simulation when real data isn't available.
        Uses baseline league averages instead of team-specific data.
        """
        import random
        
        league = league.upper()
        if league == "NBA":
            base_ppg, std_dev = 112.0, 10.0
            home_adv = 3.0
        elif league == "NFL":
            base_ppg, std_dev = 23.0, 8.0
            home_adv = 2.5
        elif league == "MLB":
            base_ppg, std_dev = 4.5, 2.5
            home_adv = 0.3
        else:
            base_ppg, std_dev = 100.0, 10.0
            home_adv = 2.0
        
        home_scores = []
        away_scores = []
        
        for _ in range(self.n_iterations):
            home_score = max(0, random.gauss(base_ppg + home_adv, std_dev))
            away_score = max(0, random.gauss(base_ppg, std_dev))
            home_scores.append(home_score)
            away_scores.append(away_score)
        
        home_wins = sum(1 for h, a in zip(home_scores, away_scores) if h > a)
        
        return {
            "success": True,
            "home_scores": home_scores,
            "away_scores": away_scores,
            "home_win_prob": home_wins / self.n_iterations,
            "away_win_prob": 1 - (home_wins / self.n_iterations),
            "home_mean": sum(home_scores) / len(home_scores),
            "away_mean": sum(away_scores) / len(away_scores),
            "fallback": True,
            "note": "Using league baseline simulation (real data unavailable)"
        }
    
    def _get_injuries(self, home_team: str, away_team: str, league: str) -> Dict[str, Any]:
        """Fetch injury data for both teams, using cache first."""
        today_date = datetime.now().strftime("%Y-%m-%d")
        cache_key = f"injuries:{league.upper()}:{today_date}"
        
        try:
            cached_data = self.cache.get_cached(cache_key)
            if cached_data:
                injured_players = cached_data.get("injured_players", [])
                logger.debug(f"Using cached injuries for {league} ({len(injured_players)} players)")
                injuries = {home_team: {}, away_team: {}}
                for player in injured_players:
                    player_team = player.get("team", "")
                    if player_team.lower() in home_team.lower() or home_team.lower() in player_team.lower():
                        injuries[home_team][player.get("name", "Unknown")] = player.get("status", "Out")
                    elif player_team.lower() in away_team.lower() or away_team.lower() in player_team.lower():
                        injuries[away_team][player.get("name", "Unknown")] = player.get("status", "Out")
                return injuries
            
            injuries = get_matchup_injuries(home_team, away_team, league)
            return injuries
        except Exception as e:
            logger.warning(f"Could not fetch injuries: {e}")
            return {home_team: {}, away_team: {}}
    
    def _get_odds(self, home_team: str, away_team: str, league: str) -> Dict[str, Any]:
        """Fetch current odds for the matchup, using cache first."""
        today_date = datetime.now().strftime("%Y-%m-%d")
        cache_key = f"odds:{league.upper()}:{today_date}"
        
        try:
            cached_data = self.cache.get_cached(cache_key)
            if cached_data:
                all_odds = cached_data.get("games", [])
                logger.debug(f"Using cached odds for {league} ({len(all_odds)} games)")
            else:
                all_odds = get_odds_data(league)
            
            home_lower = home_team.lower()
            away_lower = away_team.lower()
            
            for game in all_odds:
                game_home = game.get("home_team", "").lower()
                game_away = game.get("away_team", "").lower()
                
                if (home_lower in game_home or game_home in home_lower or
                    away_lower in game_away or game_away in away_lower):
                    return self._extract_odds_from_game(game)
            
            return self._default_odds()
        except Exception as e:
            logger.warning(f"Could not fetch odds: {e}")
            return self._default_odds()
    
    def _extract_odds_from_game(self, game: Dict) -> Dict[str, Any]:
        """Extract relevant odds from a game object."""
        odds = {
            "spread": {"line": None, "home_odds": DEFAULT_ODDS, "away_odds": DEFAULT_ODDS},
            "total": {"line": None, "over_odds": DEFAULT_ODDS, "under_odds": DEFAULT_ODDS},
            "moneyline": {"home_odds": DEFAULT_ODDS, "away_odds": DEFAULT_ODDS}
        }
        
        for bookmaker in game.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                market_key = market.get("key", "")
                outcomes = market.get("outcomes", [])
                
                if market_key == "h2h" and len(outcomes) >= 2:
                    for outcome in outcomes:
                        if outcome.get("name") == game.get("home_team"):
                            odds["moneyline"]["home_odds"] = outcome.get("price", DEFAULT_ODDS)
                        elif outcome.get("name") == game.get("away_team"):
                            odds["moneyline"]["away_odds"] = outcome.get("price", DEFAULT_ODDS)
                
                elif market_key == "spreads" and len(outcomes) >= 2:
                    for outcome in outcomes:
                        if outcome.get("name") == game.get("home_team"):
                            odds["spread"]["line"] = outcome.get("point", 0)
                            odds["spread"]["home_odds"] = outcome.get("price", DEFAULT_ODDS)
                        else:
                            odds["spread"]["away_odds"] = outcome.get("price", DEFAULT_ODDS)
                
                elif market_key == "totals" and len(outcomes) >= 2:
                    for outcome in outcomes:
                        if outcome.get("name") == "Over":
                            odds["total"]["line"] = outcome.get("point", 0)
                            odds["total"]["over_odds"] = outcome.get("price", DEFAULT_ODDS)
                        elif outcome.get("name") == "Under":
                            odds["total"]["under_odds"] = outcome.get("price", DEFAULT_ODDS)
            break
        
        return odds
    
    def _default_odds(self) -> Dict[str, Any]:
        """Return default odds when API unavailable."""
        return {
            "spread": {"line": -5.5, "home_odds": DEFAULT_ODDS, "away_odds": DEFAULT_ODDS},
            "total": {"line": 220.5, "over_odds": DEFAULT_ODDS, "under_odds": DEFAULT_ODDS},
            "moneyline": {"home_odds": -200, "away_odds": 170}
        }
    
    def _evaluate_game_bets(
        self,
        sim_result: Dict,
        odds_data: Dict,
        home_team: str,
        away_team: str,
        league: str
    ) -> tuple:
        """
        Evaluate game-level bets (spread, total, moneyline).
        Returns (qualified_bets, rejected_bets)
        """
        qualified = []
        rejected = []
        
        home_scores = sim_result.get("home_scores", [])
        away_scores = sim_result.get("away_scores", [])
        
        if not home_scores or not away_scores:
            home_win_prob_raw = sim_result.get("home_win_prob", 0.5)
            home_mean = sim_result.get("home_mean", 110)
            away_mean = sim_result.get("away_mean", 105)
        else:
            home_wins = sum(1 for h, a in zip(home_scores, away_scores) if h > a)
            home_win_prob_raw = home_wins / len(home_scores)
            home_mean = sum(home_scores) / len(home_scores)
            away_mean = sum(away_scores) / len(away_scores)
        
        home_calibrated = calibrate_probability(
            home_win_prob_raw,
            method=self.calibration_method
        )["calibrated"]
        
        away_win_prob_raw = 1 - home_win_prob_raw
        away_calibrated = 1 - home_calibrated
        
        home_ml_odds = odds_data["moneyline"]["home_odds"]
        home_implied = implied_probability(home_ml_odds)
        home_edge = edge_percentage(home_calibrated, home_implied)
        home_ev = expected_value_percent(home_calibrated, home_ml_odds)
        
        home_ml_bet = self._create_bet_object(
            pick=f"{home_team} ML",
            bet_type="moneyline",
            odds=home_ml_odds,
            model_prob=home_calibrated,
            implied_prob=home_implied,
            edge_pct=home_edge,
            ev_pct=home_ev,
            factors=[
                f"Simulation shows {home_win_prob_raw*100:.1f}% raw win probability",
                f"Calibrated to {home_calibrated*100:.1f}% after shrinkage",
                f"Projected score: {home_mean:.1f} - {away_mean:.1f}"
            ]
        )
        
        if self._is_qualified(home_edge, home_ev):
            qualified.append(home_ml_bet)
        else:
            home_ml_bet["reason"] = f"Edge {home_edge:.1f}% below threshold or EV {home_ev:.1f}% too low"
            rejected.append(home_ml_bet)
        
        away_ml_odds = odds_data["moneyline"]["away_odds"]
        away_implied = implied_probability(away_ml_odds)
        away_edge = edge_percentage(away_calibrated, away_implied)
        away_ev = expected_value_percent(away_calibrated, away_ml_odds)
        
        away_ml_bet = self._create_bet_object(
            pick=f"{away_team} ML",
            bet_type="moneyline",
            odds=away_ml_odds,
            model_prob=away_calibrated,
            implied_prob=away_implied,
            edge_pct=away_edge,
            ev_pct=away_ev,
            factors=[
                f"Simulation shows {away_win_prob_raw*100:.1f}% raw win probability",
                f"Calibrated to {away_calibrated*100:.1f}% after shrinkage",
                f"Underdog value analysis"
            ]
        )
        
        if self._is_qualified(away_edge, away_ev):
            qualified.append(away_ml_bet)
        else:
            away_ml_bet["reason"] = f"Edge {away_edge:.1f}% below threshold"
            rejected.append(away_ml_bet)
        
        spread_line = odds_data["spread"]["line"]
        if spread_line is not None and home_scores and away_scores:
            margins = [h - a for h, a in zip(home_scores, away_scores)]
            spread_cover_count = sum(1 for m in margins if m > -spread_line)
            spread_cover_prob_raw = spread_cover_count / len(margins)
            
            spread_calibrated = calibrate_probability(
                spread_cover_prob_raw,
                method=self.calibration_method
            )["calibrated"]
            
            spread_odds = odds_data["spread"]["home_odds"]
            spread_implied = implied_probability(spread_odds)
            spread_edge = edge_percentage(spread_calibrated, spread_implied)
            spread_ev = expected_value_percent(spread_calibrated, spread_odds)
            
            spread_bet = self._create_bet_object(
                pick=f"{home_team} {spread_line:+.1f}",
                bet_type="spread",
                odds=spread_odds,
                model_prob=spread_calibrated,
                implied_prob=spread_implied,
                edge_pct=spread_edge,
                ev_pct=spread_ev,
                factors=[
                    f"Spread coverage rate: {spread_cover_prob_raw*100:.1f}%",
                    f"Projected margin: {sum(margins)/len(margins):.1f}",
                    f"Line set at {spread_line}"
                ]
            )
            
            if self._is_qualified(spread_edge, spread_ev):
                qualified.append(spread_bet)
            else:
                spread_bet["reason"] = f"Edge {spread_edge:.1f}% below minimum {self.thresholds['min_edge_pct']}%"
                rejected.append(spread_bet)
        
        total_line = odds_data["total"]["line"]
        if total_line is not None and home_scores and away_scores:
            totals = [h + a for h, a in zip(home_scores, away_scores)]
            over_count = sum(1 for t in totals if t > total_line)
            over_prob_raw = over_count / len(totals)
            
            over_calibrated = calibrate_probability(
                over_prob_raw,
                method=self.calibration_method
            )["calibrated"]
            
            under_prob_raw = 1 - over_prob_raw
            under_calibrated = 1 - over_calibrated
            
            over_odds = odds_data["total"]["over_odds"]
            over_implied = implied_probability(over_odds)
            over_edge = edge_percentage(over_calibrated, over_implied)
            over_ev = expected_value_percent(over_calibrated, over_odds)
            
            projected_total = sum(totals) / len(totals)
            
            if over_calibrated > under_calibrated:
                total_bet = self._create_bet_object(
                    pick=f"OVER {total_line}",
                    bet_type="total",
                    odds=over_odds,
                    model_prob=over_calibrated,
                    implied_prob=over_implied,
                    edge_pct=over_edge,
                    ev_pct=over_ev,
                    factors=[
                        f"Projected total: {projected_total:.1f}",
                        f"Over probability: {over_prob_raw*100:.1f}%",
                        f"Line set at {total_line}"
                    ]
                )
            else:
                under_odds = odds_data["total"]["under_odds"]
                under_implied = implied_probability(under_odds)
                under_edge = edge_percentage(under_calibrated, under_implied)
                under_ev = expected_value_percent(under_calibrated, under_odds)
                
                total_bet = self._create_bet_object(
                    pick=f"UNDER {total_line}",
                    bet_type="total",
                    odds=under_odds,
                    model_prob=under_calibrated,
                    implied_prob=under_implied,
                    edge_pct=under_edge,
                    ev_pct=under_ev,
                    factors=[
                        f"Projected total: {projected_total:.1f}",
                        f"Under probability: {under_prob_raw*100:.1f}%",
                        f"Line set at {total_line}"
                    ]
                )
                over_edge = under_edge
                over_ev = under_ev
            
            if self._is_qualified(over_edge, over_ev):
                qualified.append(total_bet)
            else:
                total_bet["reason"] = f"Edge {over_edge:.1f}% below threshold"
                rejected.append(total_bet)
        
        return qualified, rejected
    
    def _evaluate_player_props(
        self,
        home_team: str,
        away_team: str,
        league: str,
        odds_data: Dict
    ) -> tuple:
        """
        Evaluate player props using simulation engine.
        Returns (qualified_props, rejected_props)
        """
        qualified = []
        rejected = []
        
        prop_types = ["pts", "reb", "ast"] if league == "NBA" else ["pass_yds", "rush_yds", "rec_yds"]
        
        try:
            from src.data.stats_ingestion import get_game_context
            
            game_ctx = get_game_context(home_team, away_team, league)
            home_players = game_ctx.get("home_players", [])
            away_players = game_ctx.get("away_players", [])
            
            all_players = []
            for p in home_players[:3]:
                all_players.append((p, home_team, away_team))
            for p in away_players[:3]:
                all_players.append((p, away_team, home_team))
            
            for player_data, team, opponent in all_players:
                player_name = player_data.get("name", "")
                if not player_name:
                    continue
                
                for prop_type in prop_types[:2]:
                    try:
                        prop_result = self.engine.run_player_prop_simulation(
                            player_name=player_name,
                            team=team,
                            opponent=opponent,
                            league=league,
                            prop_type=prop_type,
                            line=player_data.get(f"{prop_type}_mean", 15.0),
                            n_iterations=500
                        )
                        
                        if prop_result.get("success", True):
                            over_prob_raw = prop_result.get("over_prob", 0.5)
                            projected = prop_result.get("projected", prop_result.get("mean", 15))
                            line = prop_result.get("line", projected)
                            
                            over_calibrated = calibrate_probability(
                                over_prob_raw,
                                method=self.calibration_method
                            )["calibrated"]
                            
                            prop_odds = DEFAULT_ODDS
                            prop_implied = implied_probability(prop_odds)
                            prop_edge = edge_percentage(over_calibrated, prop_implied)
                            prop_ev = expected_value_percent(over_calibrated, prop_odds)
                            
                            stat_name = prop_type.upper().replace("_", " ")
                            
                            prop_bet = {
                                "player": player_name,
                                "prop": f"{stat_name} OVER {line}",
                                "odds": prop_odds,
                                "model_prob": round(over_calibrated, 3),
                                "implied_prob": round(prop_implied, 3),
                                "edge_pct": round(prop_edge, 1),
                                "ev_pct": round(prop_ev, 1),
                                "confidence_tier": self._get_confidence_tier(prop_edge, prop_ev),
                                "factors": [
                                    f"Projected {stat_name.lower()}: {projected:.1f}",
                                    f"Line: {line}",
                                    f"Over probability: {over_prob_raw*100:.1f}%"
                                ]
                            }
                            
                            if self._is_qualified(prop_edge, prop_ev):
                                qualified.append(prop_bet)
                            else:
                                prop_bet["reason"] = f"Edge {prop_edge:.1f}% or EV {prop_ev:.1f}% below threshold"
                                rejected.append(prop_bet)
                    except Exception as e:
                        logger.debug(f"Could not evaluate prop for {player_name}: {e}")
                        continue
        
        except Exception as e:
            logger.warning(f"Could not fetch players for prop analysis: {e}")
        
        return qualified, rejected
    
    def _create_bet_object(
        self,
        pick: str,
        bet_type: str,
        odds: int,
        model_prob: float,
        implied_prob: float,
        edge_pct: float,
        ev_pct: float,
        factors: List[str]
    ) -> Dict[str, Any]:
        """Create a standardized bet object."""
        confidence_tier = self._get_confidence_tier(edge_pct, ev_pct)
        
        stake_rec = recommend_stake(
            true_prob=model_prob,
            odds=odds,
            bankroll=BANKROLL,
            confidence_tier=confidence_tier[0] if confidence_tier else "C"
        )
        
        return {
            "pick": pick,
            "bet_type": bet_type,
            "odds": odds,
            "model_prob": round(model_prob, 3),
            "implied_prob": round(implied_prob, 3),
            "edge_pct": round(edge_pct, 1),
            "ev_pct": round(ev_pct, 1),
            "confidence_tier": confidence_tier,
            "stake_units": stake_rec.get("units", 0),
            "factors": factors
        }
    
    def _get_confidence_tier(self, edge_pct: float, ev_pct: float) -> str:
        """Determine confidence tier based on edge and EV."""
        tier_a = self.tier_caps["tier_a"]
        tier_b = self.tier_caps["tier_b"]
        tier_c = self.tier_caps["tier_c"]
        
        if edge_pct >= tier_a["min_edge_pct"] and ev_pct >= tier_a["min_ev_pct"]:
            return "High"
        elif edge_pct >= tier_b["min_edge_pct"] and ev_pct >= tier_b["min_ev_pct"]:
            return "Medium"
        elif edge_pct >= tier_c["min_edge_pct"] and ev_pct >= tier_c["min_ev_pct"]:
            return "Low"
        else:
            return "Pass"
    
    def _is_qualified(self, edge_pct: float, ev_pct: float) -> bool:
        """Check if bet meets minimum thresholds."""
        return (
            edge_pct >= self.thresholds["min_edge_pct"] and
            ev_pct >= self.thresholds["min_ev_pct"]
        )
    
    def _build_context_drivers(
        self,
        home_team: str,
        away_team: str,
        injuries: Dict,
        sim_result: Dict
    ) -> Dict[str, Any]:
        """Build context drivers section."""
        home_scores = sim_result.get("home_scores", [])
        away_scores = sim_result.get("away_scores", [])
        
        if home_scores and away_scores:
            home_mean = sum(home_scores) / len(home_scores)
            away_mean = sum(away_scores) / len(away_scores)
        else:
            home_mean = sim_result.get("home_mean", 110)
            away_mean = sim_result.get("away_mean", 105)
        
        narrative = (
            f"{home_team} projected to score {home_mean:.1f} points against {away_team}'s "
            f"{away_mean:.1f} points based on {self.n_iterations} Monte Carlo simulations. "
        )
        
        home_injuries = injuries.get(home_team, {})
        away_injuries = injuries.get(away_team, {})
        
        if home_injuries or away_injuries:
            narrative += "Key injuries may impact projections."
        
        return {
            "narrative": narrative,
            "injuries": {
                home_team: home_injuries,
                away_team: away_injuries
            }
        }
    
    def _build_simulation_summary(
        self,
        sim_result: Dict,
        home_team: str,
        away_team: str,
        odds_data: Dict
    ) -> Dict[str, Any]:
        """Build simulation summary section."""
        home_scores = sim_result.get("home_scores", [])
        away_scores = sim_result.get("away_scores", [])
        
        if home_scores and away_scores:
            home_mean = sum(home_scores) / len(home_scores)
            away_mean = sum(away_scores) / len(away_scores)
            home_std = (sum((s - home_mean)**2 for s in home_scores) / len(home_scores)) ** 0.5
            away_std = (sum((s - away_mean)**2 for s in away_scores) / len(away_scores)) ** 0.5
            home_wins = sum(1 for h, a in zip(home_scores, away_scores) if h > a)
            home_win_prob = home_wins / len(home_scores)
            
            spread_line = odds_data["spread"]["line"] or 0
            margins = [h - a for h, a in zip(home_scores, away_scores)]
            spread_coverage = sum(1 for m in margins if m > -spread_line) / len(margins)
            
            total_line = odds_data["total"]["line"] or 220
            totals = [h + a for h, a in zip(home_scores, away_scores)]
            over_prob = sum(1 for t in totals if t > total_line) / len(totals)
        else:
            home_mean = sim_result.get("home_mean", 110)
            away_mean = sim_result.get("away_mean", 105)
            home_std = 7.0
            away_std = 7.0
            home_win_prob = sim_result.get("home_win_prob", 0.5)
            spread_coverage = home_win_prob
            over_prob = 0.5
            total_line = 220
        
        return {
            "iterations": self.n_iterations,
            f"{home_team.split()[-1].lower()}_score_mean": round(home_mean, 1),
            f"{home_team.split()[-1].lower()}_score_std": round(home_std, 1),
            f"{away_team.split()[-1].lower()}_score_mean": round(away_mean, 1),
            f"{away_team.split()[-1].lower()}_score_std": round(away_std, 1),
            f"{home_team.split()[-1].lower()}_win_prob": round(home_win_prob, 3),
            "spread_coverage": round(spread_coverage, 3),
            "total_over_prob": round(over_prob, 3),
            "over_under_line": total_line
        }
    
    def _build_risk_assessment(self, all_bets: List[Dict]) -> Dict[str, Any]:
        """Build risk assessment section."""
        total_units = sum(bet.get("stake_units", 0) for bet in all_bets)
        max_single = max((bet.get("stake_units", 0) for bet in all_bets), default=0)
        
        if all_bets:
            avg_edge = sum(bet.get("edge_pct", 0) for bet in all_bets) / len(all_bets)
            confidence = "High" if avg_edge >= 7 else "Medium" if avg_edge >= 4 else "Low"
        else:
            confidence = "N/A"
        
        return {
            "total_units_recommended": round(total_units, 1),
            "max_single_bet": round(max_single, 1),
            "bankroll_percentage": round(total_units * 0.5, 2),
            "confidence_level": confidence,
            "note": f"All bets meet minimum thresholds (edge >= {self.thresholds['min_edge_pct']}%, EV >= {self.thresholds['min_ev_pct']}%)"
        }


def run_analysis(team_a: str, team_b: str, league: str = "NBA", include_props: bool = True) -> Dict:
    """Convenience function to run the analysis pipeline."""
    pipeline = GameAnalysisPipeline(n_iterations=1000)
    return pipeline.analyze(team_a, team_b, league, include_props)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run game analysis pipeline")
    parser.add_argument("--team_a", required=True, help="First team (home)")
    parser.add_argument("--team_b", required=True, help="Second team (away)")
    parser.add_argument("--league", default="NBA", help="League (NBA, NFL, etc.)")
    parser.add_argument("--include_props", action="store_true", default=True, help="Include player props")
    parser.add_argument("--no_props", action="store_true", help="Exclude player props")
    
    args = parser.parse_args()
    
    include_props = not args.no_props
    
    result = run_analysis(args.team_a, args.team_b, args.league, include_props)
    print(json.dumps(result, indent=2, default=str))
