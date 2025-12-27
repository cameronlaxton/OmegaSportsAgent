"""
SGP Correlation Engine Module

Analyzes player prop correlations using Markov simulations to suggest
same-game parlay combinations and flag anti-correlated bets.
"""

from __future__ import annotations
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import random

try:
    import numpy as np
except ImportError:
    np = None


@dataclass
class PropBet:
    player: str
    stat: str
    line: float
    over_under: str
    team: Optional[str] = None


@dataclass
class CorrelationResult:
    prop1: PropBet
    prop2: PropBet
    correlation: float
    co_occurrence_rate: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "prop1": {"player": self.prop1.player, "stat": self.prop1.stat, "line": self.prop1.line, "over_under": self.prop1.over_under},
            "prop2": {"player": self.prop2.player, "stat": self.prop2.stat, "line": self.prop2.line, "over_under": self.prop2.over_under},
            "correlation": round(self.correlation, 3),
            "co_occurrence_rate": round(self.co_occurrence_rate, 3)
        }


SPORT_CORRELATION_RULES = {
    "NBA": {
        "same_team_positive": [
            ("pts", "ast"),
            ("pts", "reb"),
            ("ast", "pts"),
            ("reb", "pts"),
            ("pts", "3pm"),
            ("ast", "reb"),
        ],
        "cross_team_negative": [
            ("pts", "pts"),
        ],
        "pace_correlated": ["pts", "reb", "ast", "stl", "blk"],
        "base_correlations": {
            ("pts", "ast"): 0.35,
            ("pts", "reb"): 0.25,
            ("ast", "reb"): 0.20,
            ("pts", "3pm"): 0.40,
            ("reb", "blk"): 0.30,
            ("stl", "ast"): 0.15,
        }
    },
    "NFL": {
        "same_team_positive": [
            ("pass_yds", "rec_yds"),
            ("pass_tds", "rec_tds"),
            ("pass_yds", "pass_tds"),
            ("rush_yds", "rush_tds"),
        ],
        "cross_team_negative": [
            ("rush_yds", "pass_yds"),
            ("rush_tds", "pass_tds"),
        ],
        "game_script_impact": {
            "leading": {"rush_yds": 1.2, "pass_yds": 0.9},
            "trailing": {"rush_yds": 0.8, "pass_yds": 1.2},
        },
        "base_correlations": {
            ("pass_yds", "rec_yds"): 0.55,
            ("pass_tds", "rec_tds"): 0.50,
            ("pass_yds", "pass_tds"): 0.45,
            ("rush_yds", "rush_tds"): 0.35,
            ("pass_yds", "pass_att"): 0.40,
        }
    },
    "MLB": {
        "same_team_positive": [
            ("hits", "runs"),
            ("runs", "rbi"),
        ],
        "base_correlations": {
            ("hits", "runs"): 0.30,
            ("runs", "rbi"): 0.25,
        }
    },
    "NHL": {
        "same_team_positive": [
            ("goals", "assists"),
            ("shots", "goals"),
        ],
        "base_correlations": {
            ("goals", "assists"): 0.35,
            ("shots", "goals"): 0.25,
        }
    }
}


def get_correlation_strength_label(corr: float) -> str:
    """Convert correlation value to human-readable label."""
    abs_corr = abs(corr)
    if abs_corr >= 0.5:
        return "Strong"
    elif abs_corr >= 0.3:
        return "Moderate"
    elif abs_corr >= 0.15:
        return "Weak"
    else:
        return "Minimal"


def normalize_stat_name(stat: str, league: str) -> str:
    """Normalize stat names for consistent lookup."""
    stat = stat.lower().replace(" ", "_").replace("-", "_")
    
    nba_mappings = {
        "points": "pts",
        "assists": "ast",
        "rebounds": "reb",
        "steals": "stl",
        "blocks": "blk",
        "three_pointers_made": "3pm",
        "threes": "3pm",
        "3_pointers": "3pm",
    }
    
    nfl_mappings = {
        "passing_yards": "pass_yds",
        "passing_touchdowns": "pass_tds",
        "rushing_yards": "rush_yds",
        "rushing_touchdowns": "rush_tds",
        "receiving_yards": "rec_yds",
        "receiving_touchdowns": "rec_tds",
        "receptions": "rec",
        "completions": "comp",
        "passing_attempts": "pass_att",
    }
    
    if league.upper() == "NBA":
        return nba_mappings.get(stat, stat)
    elif league.upper() == "NFL":
        return nfl_mappings.get(stat, stat)
    
    return stat


class CorrelationEngine:
    """
    Engine for computing player prop correlations using simulation data
    and sport-specific correlation rules.
    """
    
    def __init__(self, league: str = "NBA"):
        self.league = league.upper()
        self.rules = SPORT_CORRELATION_RULES.get(self.league, {})
        self._correlation_cache: Dict[str, Dict] = {}
    
    def compute_correlations(
        self,
        game_id: str,
        league: str,
        n_iterations: int = 500,
        home_team: Optional[str] = None,
        away_team: Optional[str] = None,
        player_props: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Compute correlations between player props using Markov simulations.
        
        Args:
            game_id: Unique game identifier
            league: League code (NBA, NFL, etc.)
            n_iterations: Number of simulation iterations
            home_team: Home team name (optional, for simulation)
            away_team: Away team name (optional, for simulation)
            player_props: List of player prop dicts to analyze
        
        Returns:
            Dict with correlation matrix, prop outcomes, and co-occurrence rates
        """
        self.league = league.upper()
        self.rules = SPORT_CORRELATION_RULES.get(self.league, {})
        
        cache_key = f"{game_id}_{league}_{n_iterations}"
        if cache_key in self._correlation_cache:
            return self._correlation_cache[cache_key]
        
        simulation_results = self._run_simulations(
            home_team or "Home",
            away_team or "Away",
            player_props or [],
            n_iterations
        )
        
        correlations = self._build_correlation_matrix(simulation_results, player_props or [])
        
        result = {
            "game_id": game_id,
            "league": league,
            "n_iterations": n_iterations,
            "correlations": correlations,
            "prop_outcomes": simulation_results.get("prop_hit_rates", {}),
            "co_occurrences": simulation_results.get("co_occurrences", {})
        }
        
        self._correlation_cache[cache_key] = result
        return result
    
    def _run_simulations(
        self,
        home_team: str,
        away_team: str,
        player_props: List[Dict],
        n_iterations: int
    ) -> Dict[str, Any]:
        """Run Monte Carlo simulations using OmegaSimulationEngine to track prop outcomes."""
        prop_hits: Dict[str, List[bool]] = {}
        prop_values: Dict[str, List[float]] = {}
        
        for prop in player_props:
            key = self._prop_key(prop)
            prop_hits[key] = []
            prop_values[key] = []
        
        try:
            from omega.simulation.simulation_engine import OmegaSimulationEngine
            engine = OmegaSimulationEngine()
            
            sim_result = engine.run_game_simulation(
                home_team=home_team,
                away_team=away_team,
                league=self.league,
                n_iterations=n_iterations
            )
            
            player_projections = sim_result.get("player_projections", {})
            
            for prop in player_props:
                key = self._prop_key(prop)
                player = prop.get("player", "")
                stat = normalize_stat_name(prop.get("stat", "pts"), self.league)
                line = float(prop.get("line", 0))
                over_under = prop.get("over_under", "over").lower()
                
                player_name_lower = player.lower()
                matched_player = None
                for sim_player in player_projections.keys():
                    if player_name_lower in sim_player.lower() or sim_player.lower() in player_name_lower:
                        matched_player = sim_player
                        break
                
                if matched_player and stat in player_projections.get(matched_player, {}):
                    stat_data = player_projections[matched_player][stat]
                    mean_val = stat_data.get("mean", line)
                    std_val = stat_data.get("std", mean_val * 0.25)
                    
                    if np is not None:
                        samples = np.random.normal(mean_val, max(0.1, std_val), n_iterations).tolist()
                    else:
                        samples = [random.gauss(mean_val, max(0.1, std_val)) for _ in range(n_iterations)]
                    
                    prop_values[key] = [max(0, s) for s in samples]
                    
                    if over_under == "over":
                        prop_hits[key] = [v > line for v in prop_values[key]]
                    else:
                        prop_hits[key] = [v < line for v in prop_values[key]]
                else:
                    for _ in range(n_iterations):
                        game_state = self._simulate_single_game_fallback([prop])
                        simulated_value = game_state.get(player, {}).get(stat, 0)
                        prop_values[key].append(simulated_value)
                        
                        if over_under == "over":
                            prop_hits[key].append(simulated_value > line)
                        else:
                            prop_hits[key].append(simulated_value < line)
        
        except Exception as e:
            for _ in range(n_iterations):
                game_state = self._simulate_single_game_fallback(player_props)
                
                for prop in player_props:
                    key = self._prop_key(prop)
                    player = prop.get("player", "")
                    stat = normalize_stat_name(prop.get("stat", "pts"), self.league)
                    line = float(prop.get("line", 0))
                    over_under = prop.get("over_under", "over").lower()
                    
                    simulated_value = game_state.get(player, {}).get(stat, 0)
                    prop_values[key].append(simulated_value)
                    
                    if over_under == "over":
                        prop_hits[key].append(simulated_value > line)
                    else:
                        prop_hits[key].append(simulated_value < line)
        
        prop_hit_rates = {}
        for key, hits in prop_hits.items():
            prop_hit_rates[key] = sum(hits) / len(hits) if hits else 0.5
        
        co_occurrences = self._calculate_co_occurrences(prop_hits)
        
        return {
            "prop_hits": prop_hits,
            "prop_values": prop_values,
            "prop_hit_rates": prop_hit_rates,
            "co_occurrences": co_occurrences
        }
    
    def _simulate_single_game_fallback(self, player_props: List[Dict]) -> Dict[str, Dict[str, float]]:
        """Fallback simulation for a single game when OmegaSimulationEngine is unavailable."""
        game_state: Dict[str, Dict[str, float]] = {}
        
        pace_factor = random.gauss(1.0, 0.1)
        
        for prop in player_props:
            player = prop.get("player", "")
            stat = normalize_stat_name(prop.get("stat", "pts"), self.league)
            line = float(prop.get("line", 0))
            team = prop.get("team", "")
            
            if player not in game_state:
                game_state[player] = {"team": team}
            
            base_mean = line
            base_std = self._get_stat_std(stat, line)
            
            adjusted_mean = base_mean * pace_factor
            
            if self.league == "NBA" and stat in ["pts", "reb", "ast"]:
                adjusted_mean *= pace_factor
            
            simulated = max(0, random.gauss(adjusted_mean, base_std))
            game_state[player][stat] = simulated
        
        self._apply_stat_correlations(game_state)
        
        return game_state
    
    def _apply_stat_correlations(self, game_state: Dict[str, Dict[str, float]]) -> None:
        """Apply intra-player stat correlations."""
        base_corrs = self.rules.get("base_correlations", {})
        
        for player, stats in game_state.items():
            if player == "team":
                continue
            for (stat1, stat2), corr in base_corrs.items():
                if stat1 in stats and stat2 in stats:
                    noise = random.gauss(0, 0.1)
                    adjustment = 1 + (corr + noise) * 0.1
                    stats[stat2] = stats.get(stat2, 0) * adjustment
    
    def _get_stat_std(self, stat: str, line: float) -> float:
        """Get standard deviation for a stat based on typical variance."""
        std_ratios = {
            "pts": 0.30,
            "reb": 0.35,
            "ast": 0.40,
            "stl": 0.50,
            "blk": 0.55,
            "3pm": 0.45,
            "pass_yds": 0.25,
            "rush_yds": 0.35,
            "rec_yds": 0.40,
            "pass_tds": 0.50,
            "rush_tds": 0.60,
            "rec_tds": 0.65,
        }
        ratio = std_ratios.get(stat, 0.30)
        return max(1.0, line * ratio)
    
    def _calculate_co_occurrences(self, prop_hits: Dict[str, List[bool]]) -> Dict[str, float]:
        """Calculate co-occurrence rates between all prop pairs."""
        co_occurrences = {}
        keys = list(prop_hits.keys())
        
        for i, key1 in enumerate(keys):
            for key2 in keys[i+1:]:
                hits1 = prop_hits[key1]
                hits2 = prop_hits[key2]
                
                both_hit = sum(1 for h1, h2 in zip(hits1, hits2) if h1 and h2)
                co_rate = both_hit / len(hits1) if hits1 else 0
                
                pair_key = f"{key1}|{key2}"
                co_occurrences[pair_key] = co_rate
        
        return co_occurrences
    
    def _build_correlation_matrix(
        self,
        simulation_results: Dict[str, Any],
        player_props: List[Dict]
    ) -> Dict[str, Dict[str, float]]:
        """Build correlation matrix from simulation results."""
        prop_values = simulation_results.get("prop_values", {})
        correlations: Dict[str, Dict[str, float]] = {}
        
        keys = list(prop_values.keys())
        
        for key1 in keys:
            correlations[key1] = {}
            for key2 in keys:
                if key1 == key2:
                    correlations[key1][key2] = 1.0
                else:
                    corr = self._calculate_correlation(
                        prop_values.get(key1, []),
                        prop_values.get(key2, [])
                    )
                    correlations[key1][key2] = corr
        
        return correlations
    
    def _calculate_correlation(self, values1: List[float], values2: List[float]) -> float:
        """Calculate Pearson correlation between two value series."""
        if not values1 or not values2 or len(values1) != len(values2):
            return 0.0
        
        n = len(values1)
        if n < 2:
            return 0.0
        
        mean1 = sum(values1) / n
        mean2 = sum(values2) / n
        
        cov = sum((v1 - mean1) * (v2 - mean2) for v1, v2 in zip(values1, values2)) / n
        std1 = (sum((v - mean1) ** 2 for v in values1) / n) ** 0.5
        std2 = (sum((v - mean2) ** 2 for v in values2) / n) ** 0.5
        
        if std1 < 0.001 or std2 < 0.001:
            return 0.0
        
        return cov / (std1 * std2)
    
    def _prop_key(self, prop: Dict) -> str:
        """Generate a unique key for a prop."""
        return f"{prop.get('player', '')}_{prop.get('stat', '')}_{prop.get('line', '')}_{prop.get('over_under', 'over')}"
    
    def get_correlated_props(
        self,
        base_prop: Dict,
        available_props: List[Dict],
        correlations: Optional[Dict] = None,
        top_n: int = 5
    ) -> List[Dict]:
        """
        Find props positively correlated with the base prop.
        
        Args:
            base_prop: The base prop to find correlations for
            available_props: List of available props to suggest
            correlations: Pre-computed correlation data (optional)
            top_n: Number of suggestions to return
        
        Returns:
            List of suggested props with correlation info
        """
        base_key = self._prop_key(base_prop)
        base_stat = normalize_stat_name(base_prop.get("stat", ""), self.league)
        base_team = base_prop.get("team", "")
        base_over_under = base_prop.get("over_under", "over").lower()
        
        suggestions = []
        
        for prop in available_props:
            if self._prop_key(prop) == base_key:
                continue
            
            prop_stat = normalize_stat_name(prop.get("stat", ""), self.league)
            prop_team = prop.get("team", "")
            prop_over_under = prop.get("over_under", "over").lower()
            
            correlation, rationale = self._estimate_correlation(
                base_stat, prop_stat,
                base_team, prop_team,
                base_over_under, prop_over_under,
                correlations
            )
            
            if correlation > 0.1:
                suggestions.append({
                    "player": prop.get("player", ""),
                    "stat": prop.get("stat", ""),
                    "line": prop.get("line", 0),
                    "over_under": prop.get("over_under", "over"),
                    "team": prop_team,
                    "correlation": round(correlation, 3),
                    "correlation_strength": get_correlation_strength_label(correlation),
                    "rationale": rationale
                })
        
        suggestions.sort(key=lambda x: x["correlation"], reverse=True)
        return suggestions[:top_n]
    
    def _estimate_correlation(
        self,
        stat1: str,
        stat2: str,
        team1: str,
        team2: str,
        direction1: str,
        direction2: str,
        correlations: Optional[Dict] = None
    ) -> Tuple[float, str]:
        """Estimate correlation between two props based on rules and simulation."""
        base_corrs = self.rules.get("base_correlations", {})
        same_team = team1.lower() == team2.lower() if team1 and team2 else False
        
        base_corr = base_corrs.get((stat1, stat2), 0.0)
        if base_corr == 0:
            base_corr = base_corrs.get((stat2, stat1), 0.0)
        
        same_team_pairs = self.rules.get("same_team_positive", [])
        if same_team and (stat1, stat2) in same_team_pairs:
            base_corr = max(base_corr, 0.25)
        
        rationale = ""
        
        if same_team:
            if direction1 == direction2:
                base_corr = abs(base_corr) * 1.2
                rationale = f"Same team {stat1.upper()} and {stat2.upper()} tend to move together"
            else:
                base_corr = -abs(base_corr) * 0.5
                rationale = f"Opposite directions on same team stats may conflict"
        else:
            cross_team_neg = self.rules.get("cross_team_negative", [])
            if (stat1, stat2) in cross_team_neg or (stat2, stat1) in cross_team_neg:
                base_corr = -0.15
                rationale = f"Cross-team {stat1.upper()} and {stat2.upper()} may be inversely related"
            else:
                base_corr = base_corr * 0.7
                rationale = f"Game pace can link {stat1.upper()} and {stat2.upper()}"
        
        if not rationale:
            if base_corr > 0.3:
                rationale = f"Strong historical correlation between {stat1.upper()} and {stat2.upper()}"
            elif base_corr > 0.15:
                rationale = f"Moderate statistical relationship"
            else:
                rationale = f"Weak correlation based on typical game patterns"
        
        return max(-1.0, min(1.0, base_corr)), rationale
    
    def build_sgp_suggestion(
        self,
        props_in_slip: List[Dict],
        available_props: List[Dict],
        game_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Suggest additional legs for an SGP based on current slip.
        
        Args:
            props_in_slip: Current props in the bet slip
            available_props: All available props for the game
            game_id: Optional game identifier
        
        Returns:
            Dict with suggestions and warnings
        """
        suggestions = []
        warnings = []
        
        warnings.extend(self._check_anti_correlations(props_in_slip))
        
        all_suggestions = []
        for prop in props_in_slip:
            correlated = self.get_correlated_props(
                prop,
                available_props,
                top_n=3
            )
            for sugg in correlated:
                sugg_key = self._prop_key(sugg)
                if not any(self._prop_key(p) == sugg_key for p in props_in_slip):
                    if not any(s.get("player") == sugg.get("player") and 
                              s.get("stat") == sugg.get("stat") for s in all_suggestions):
                        all_suggestions.append(sugg)
        
        all_suggestions.sort(key=lambda x: x.get("correlation", 0), reverse=True)
        suggestions = all_suggestions[:5]
        
        return {
            "suggestions": suggestions,
            "warnings": warnings,
            "slip_count": len(props_in_slip),
            "total_suggestions": len(all_suggestions)
        }
    
    def _check_anti_correlations(self, props: List[Dict]) -> List[Dict]:
        """Check for anti-correlated props in the slip."""
        warnings = []
        cross_team_neg = self.rules.get("cross_team_negative", [])
        
        for i, prop1 in enumerate(props):
            for prop2 in props[i+1:]:
                stat1 = normalize_stat_name(prop1.get("stat", ""), self.league)
                stat2 = normalize_stat_name(prop2.get("stat", ""), self.league)
                team1 = prop1.get("team", "")
                team2 = prop2.get("team", "")
                dir1 = prop1.get("over_under", "over").lower()
                dir2 = prop2.get("over_under", "over").lower()
                
                is_anti = False
                reason = ""
                
                if team1 and team2 and team1.lower() != team2.lower():
                    if (stat1, stat2) in cross_team_neg or (stat2, stat1) in cross_team_neg:
                        is_anti = True
                        reason = f"Cross-team conflict: {prop1.get('player', '')}'s {stat1} may hurt {prop2.get('player', '')}'s {stat2}"
                
                if team1 and team2 and team1.lower() == team2.lower():
                    if dir1 != dir2 and stat1 == stat2:
                        is_anti = True
                        reason = f"Same stat opposite directions: {prop1.get('player', '')} vs {prop2.get('player', '')} on {stat1}"
                
                if is_anti:
                    warnings.append({
                        "type": "anti_correlation",
                        "props": [
                            {"player": prop1.get("player", ""), "stat": stat1},
                            {"player": prop2.get("player", ""), "stat": stat2}
                        ],
                        "reason": reason,
                        "severity": "warning"
                    })
        
        return warnings


def compute_sgp_correlations(
    game_id: str,
    league: str,
    current_props: List[Dict],
    available_props: Optional[List[Dict]] = None,
    n_iterations: int = 500
) -> Dict[str, Any]:
    """
    Main entry point for SGP correlation analysis.
    
    Args:
        game_id: Game identifier
        league: League code
        current_props: Props currently in the slip
        available_props: All available props for suggestions
        n_iterations: Simulation iterations
    
    Returns:
        Dict with suggestions, warnings, and correlation data
    """
    engine = CorrelationEngine(league)
    
    all_props = current_props + (available_props or [])
    
    if all_props:
        engine.compute_correlations(
            game_id=game_id,
            league=league,
            n_iterations=n_iterations,
            player_props=all_props
        )
    
    result = engine.build_sgp_suggestion(
        props_in_slip=current_props,
        available_props=available_props or [],
        game_id=game_id
    )
    
    return result
