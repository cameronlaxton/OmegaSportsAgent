"""
Simulation Engine Module

Runs Monte Carlo simulations for team markets (spreads, totals, ML) and player props,
selecting Normal vs Poisson automatically.
"""

from __future__ import annotations
import random
from typing import Dict, Optional, List, Union

try:
    import numpy as np
except ImportError:
    np = None

from omega.data.nfl_stats import NFLTeamContext, NFLPlayerContext


def select_distribution(metric_key: str, league: str) -> str:
    """
    Selects appropriate distribution (Normal vs Poisson) based on metric and league.
    
    Args:
        metric_key: Stat identifier (e.g., "score", "pts", "reb", "pass_yds")
        league: League identifier (e.g., "NBA", "NFL", "MLB", "NHL")
    
    Returns:
        "poisson" for discrete/count stats, "normal" for continuous stats
    """
    league = league.upper()
    metric_key = metric_key.lower()
    
    if metric_key in {"run_rate", "goal_rate"} or league in {"MLB", "NHL"}:
        return "poisson"
    
    if league in {"NFL", "NCAAF"} and metric_key == "score":
        return "poisson"
    
    discrete_stats = {"goals", "td", "touchdowns", "receptions", "rec", "sog"}
    if metric_key in discrete_stats:
        return "poisson"
    
    return "normal"


def _poisson_sample(lam: float, size: int) -> List[float]:
    """Generate Poisson samples."""
    lam = max(0.01, lam)
    if np is not None:
        return np.random.poisson(lam=lam, size=size).tolist()
    samples = []
    for _ in range(size):
        L = pow(2.718281828459045, -lam)
        k, p = 0, 1.0
        while p > L:
            k += 1
            p *= random.random()
        samples.append(k - 1)
    return samples


def _normal_sample(mu: float, sigma: float, size: int) -> List[float]:
    """Generate Normal samples."""
    sigma = max(0.1, sigma)
    if np is not None:
        return np.random.normal(mu, sigma, size).tolist()
    return [random.gauss(mu, sigma) for _ in range(size)]


def run_game_simulation(
    projection: Dict,
    n_iter: int = 10000,
    seed: Optional[int] = None,
    league: Optional[str] = None
) -> Dict:
    """
    Simulates a game between two teams, returning win probabilities and score distributions.
    
    Args:
        projection: Dict with keys:
            - "off_rating": dict mapping team names to offensive ratings
            - "league": str (e.g., "NBA", "NFL")
            - "variance_scalar": float (optional, default 1.0)
        n_iter: Number of simulation iterations
        seed: Random seed for reproducibility
        league: Optional league override
    
    Returns:
        Dict with keys: "team_a_wins", "team_b_wins", "true_prob_a", "true_prob_b", "a_scores", "b_scores"
    """
    if seed is not None:
        random.seed(seed)
        if np is not None:
            np.random.seed(seed)
    
    teams = list(projection.get("off_rating", {}).keys())
    if len(teams) != 2:
        raise ValueError("Projection requires exactly two teams.")
    
    resolved_league = league if league is not None else projection.get("league", "NFL")
    variance_scalar = projection.get("variance_scalar", 1.0)
    team_a, team_b = teams
    off_a = projection["off_rating"][team_a]
    off_b = projection["off_rating"][team_b]
    dist = select_distribution("score", resolved_league)
    
    results = {"team_a_wins": 0, "team_b_wins": 0, "a_scores": [], "b_scores": []}
    
    for _ in range(n_iter):
        if dist == "poisson":
            score_a = _poisson_sample(off_a * variance_scalar, 1)[0]
            score_b = _poisson_sample(off_b * variance_scalar, 1)[0]
        else:
            sigma = max(1.5, 5 * variance_scalar)
            score_a = _normal_sample(off_a, sigma, 1)[0]
            score_b = _normal_sample(off_b, sigma, 1)[0]
        
        results["a_scores"].append(score_a)
        results["b_scores"].append(score_b)
        
        if score_a > score_b:
            results["team_a_wins"] += 1
        elif score_b > score_a:
            results["team_b_wins"] += 1
    
    results["true_prob_a"] = results["team_a_wins"] / n_iter
    results["true_prob_b"] = results["team_b_wins"] / n_iter
    return results


def simulate_totals(
    mean: float,
    variance: float,
    market_total: float,
    dist: str,
    n_iter: int = 10000
) -> Dict:
    """
    Simulates totals (over/under) with explicit distribution selection.
    """
    sigma = max(0.1, variance ** 0.5)
    samples = _normal_sample(mean, sigma, n_iter) if dist == "normal" else _poisson_sample(mean, n_iter)
    
    over_hits = sum(1 for x in samples if x > market_total)
    under_hits = sum(1 for x in samples if x < market_total)
    push_hits = sum(1 for x in samples if abs(x - market_total) < 0.5)
    
    return {
        "over_prob": over_hits / n_iter,
        "under_prob": under_hits / n_iter,
        "push_prob": push_hits / n_iter,
        "mean": sum(samples) / n_iter,
        "std": sigma
    }


def simulate_totals_auto(
    mean: float,
    variance: float,
    market_total: float,
    metric_key: str,
    league: str,
    n_iter: int = 10000,
    seed: Optional[int] = None
) -> Dict:
    """
    Automatically selects distribution (Normal vs Poisson) and simulates totals.
    """
    if seed is not None:
        random.seed(seed)
        if np is not None:
            np.random.seed(seed)
    
    dist = select_distribution(metric_key, league)
    return simulate_totals(mean, variance, market_total, dist, n_iter)


def run_player_simulation(
    player_proj: Dict,
    n_iter: int = 10000,
    seed: Optional[int] = None
) -> Dict:
    """
    Simulates a single player stat (e.g., points, rebounds, passing yards) vs a market line.
    
    Args:
        player_proj: Dict with keys:
            - "league": str
            - "player_name": str
            - "stat_key": str (e.g., "pts", "reb", "pass_yds")
            - "mean": float
            - "variance": float
            - "market_line": float
        n_iter: Number of simulation iterations
        seed: Random seed for reproducibility
    
    Returns:
        Dict with keys: "over_prob", "under_prob", "push_prob", "mean", "std", "samples"
    """
    if seed is not None:
        random.seed(seed)
        if np is not None:
            np.random.seed(seed)
    
    league = player_proj.get("league", "NBA").upper()
    stat_key = player_proj.get("stat_key", "pts")
    mean = player_proj.get("mean", 0.0)
    variance = player_proj.get("variance", 1.0)
    market_line = player_proj.get("market_line", mean)
    
    dist = select_distribution(stat_key, league)
    sigma = max(0.1, variance ** 0.5)
    
    if dist == "poisson":
        samples = _poisson_sample(mean, n_iter)
    else:
        samples = _normal_sample(mean, sigma, n_iter)
    
    over_hits = sum(1 for x in samples if x > market_line)
    under_hits = sum(1 for x in samples if x < market_line)
    push_hits = sum(1 for x in samples if abs(x - market_line) < 0.5)
    
    sample_mean = sum(samples) / n_iter
    sample_variance = sum((x - sample_mean) ** 2 for x in samples) / n_iter
    sample_std = sample_variance ** 0.5
    
    return {
        "over_prob": over_hits / n_iter,
        "under_prob": under_hits / n_iter,
        "push_prob": push_hits / n_iter,
        "mean": sample_mean,
        "std": sample_std,
        "samples": samples[:100] if len(samples) > 100 else samples
    }


def run_nfl_game_simulation(
    home_team: str,
    away_team: str,
    home_context: Union[NFLTeamContext, Dict],
    away_context: Union[NFLTeamContext, Dict],
    n_iter: int = 1000
) -> Dict:
    """
    Run NFL-specific game simulation using team context.
    
    Uses points_per_game and points_allowed_per_game for scoring projections.
    Models NFL scoring with ~21 points average per team and Normal distribution.
    
    Args:
        home_team: Home team name
        away_team: Away team name
        home_context: NFLTeamContext or dict with team stats
        away_context: NFLTeamContext or dict with team stats
        n_iter: Number of simulation iterations (default 1000)
    
    Returns:
        Dict with win probabilities, predicted scores, spread, total
    """
    if isinstance(home_context, NFLTeamContext):
        home_ppg = home_context.points_per_game
        home_papg = home_context.points_allowed_per_game
    else:
        home_ppg = home_context.get("points_per_game", 21.0)
        home_papg = home_context.get("points_allowed_per_game", 21.0)
    
    if isinstance(away_context, NFLTeamContext):
        away_ppg = away_context.points_per_game
        away_papg = away_context.points_allowed_per_game
    else:
        away_ppg = away_context.get("points_per_game", 21.0)
        away_papg = away_context.get("points_allowed_per_game", 21.0)
    
    home_expected = (home_ppg + away_papg) / 2.0
    away_expected = (away_ppg + home_papg) / 2.0
    
    home_std = 10.0
    away_std = 10.0
    
    home_scores = _normal_sample(home_expected, home_std, n_iter)
    away_scores = _normal_sample(away_expected, away_std, n_iter)
    
    home_scores = [max(0, s) for s in home_scores]
    away_scores = [max(0, s) for s in away_scores]
    
    home_wins = sum(1 for h, a in zip(home_scores, away_scores) if h > a)
    away_wins = sum(1 for h, a in zip(home_scores, away_scores) if a > h)
    ties = n_iter - home_wins - away_wins
    
    home_mean = sum(home_scores) / n_iter
    away_mean = sum(away_scores) / n_iter
    
    sorted_home = sorted(home_scores)
    sorted_away = sorted(away_scores)
    
    return {
        "success": True,
        "home_team": home_team,
        "away_team": away_team,
        "league": "NFL",
        "iterations": n_iter,
        "home_win_prob": round(home_wins / n_iter * 100, 1),
        "away_win_prob": round(away_wins / n_iter * 100, 1),
        "tie_prob": round(ties / n_iter * 100, 1),
        "predicted_home_score": round(home_mean, 1),
        "predicted_away_score": round(away_mean, 1),
        "predicted_spread": round(home_mean - away_mean, 1),
        "predicted_total": round(home_mean + away_mean, 1),
        "home_score_p10": round(sorted_home[int(n_iter * 0.1)], 1),
        "home_score_p90": round(sorted_home[int(n_iter * 0.9)], 1),
        "away_score_p10": round(sorted_away[int(n_iter * 0.1)], 1),
        "away_score_p90": round(sorted_away[int(n_iter * 0.9)], 1)
    }


def run_nfl_player_prop_simulation(
    player_context: Union[NFLPlayerContext, Dict],
    prop_type: str,
    line: float,
    n_iter: int = 1000
) -> Dict:
    """
    Run NFL player prop simulation for various stat types.
    
    Handles:
        - pass_yards: Normal distribution with game variance
        - rush_yards: Normal distribution with game variance
        - receiving_yards: Normal distribution with game variance
        - receptions: Poisson distribution (discrete count)
        - pass_td: Poisson distribution
        - rush_td: Poisson distribution
        - receiving_td: Poisson distribution
    
    Args:
        player_context: NFLPlayerContext or dict with player stats
        prop_type: Type of prop (pass_yards, rush_yards, receiving_yards, receptions, pass_td, rush_td, receiving_td)
        line: Betting line for the prop
        n_iter: Number of simulation iterations (default 1000)
    
    Returns:
        Dict with hit probability, mean projection, percentiles (10th, 25th, 50th, 75th, 90th)
    """
    if isinstance(player_context, NFLPlayerContext):
        player_name = player_context.name
        ctx = player_context
    else:
        player_name = player_context.get("name", "Unknown")
        ctx = NFLPlayerContext.from_dict(player_context) if player_context else NFLPlayerContext(name=player_name, team="Unknown", position="Unknown")
    
    prop_type_lower = prop_type.lower()
    
    prop_config = {
        "pass_yards": {"mean_attr": "pass_yards", "dist": "normal", "std_factor": 0.35},
        "rush_yards": {"mean_attr": "rush_yards", "dist": "normal", "std_factor": 0.40},
        "receiving_yards": {"mean_attr": "receiving_yards", "dist": "normal", "std_factor": 0.45},
        "receptions": {"mean_attr": "receptions", "dist": "poisson"},
        "pass_td": {"mean_attr": "pass_td", "dist": "poisson"},
        "rush_td": {"mean_attr": "rush_td", "dist": "poisson"},
        "receiving_td": {"mean_attr": "receiving_td", "dist": "poisson"},
    }
    
    if prop_type_lower not in prop_config:
        return {
            "success": False,
            "error": f"Unknown prop type: {prop_type}",
            "player": player_name,
            "prop_type": prop_type,
            "line": line
        }
    
    config = prop_config[prop_type_lower]
    mean_attr = config["mean_attr"]
    dist_type = config["dist"]
    
    mean_value = getattr(ctx, mean_attr, 0.0)
    if mean_value <= 0:
        mean_value = line * 0.95
    
    if dist_type == "normal":
        std_factor = config.get("std_factor", 0.35)
        std_value = max(5.0, mean_value * std_factor)
        samples = _normal_sample(mean_value, std_value, n_iter)
        samples = [max(0, s) for s in samples]
    else:
        samples = _poisson_sample(mean_value, n_iter)
    
    sorted_samples = sorted(samples)
    n = len(sorted_samples)
    mean_proj = sum(samples) / n
    
    over_count = sum(1 for v in samples if v > line)
    under_count = sum(1 for v in samples if v < line)
    push_count = sum(1 for v in samples if abs(v - line) < 0.5)
    
    hit_prob = over_count / n * 100
    
    return {
        "success": True,
        "player": player_name,
        "prop_type": prop_type,
        "line": line,
        "hit_probability": round(hit_prob, 1),
        "mean_projection": round(mean_proj, 1),
        "over_prob": round(over_count / n * 100, 1),
        "under_prob": round(under_count / n * 100, 1),
        "push_prob": round(push_count / n * 100, 1),
        "p10": round(sorted_samples[int(n * 0.1)], 1),
        "p25": round(sorted_samples[int(n * 0.25)], 1),
        "p50": round(sorted_samples[int(n * 0.5)], 1),
        "p75": round(sorted_samples[int(n * 0.75)], 1),
        "p90": round(sorted_samples[int(n * 0.9)], 1),
        "iterations": n_iter
    }


class OmegaSimulationEngine:
    """
    High-level simulation engine that uses real stats from StatsIngestionService
    to run Markov chain simulations with team context.
    """
    
    def __init__(self):
        """Initialize the simulation engine."""
        pass
    
    def run_fast_game_simulation(
        self,
        home_team: str,
        away_team: str,
        league: str = "NBA",
        n_iterations: int = 100,
        home_context: Optional[Dict] = None,
        away_context: Optional[Dict] = None
    ) -> Dict:
        """
        Run a fast game simulation using only team stats (no player roster).
        Much faster than full simulation - suitable for dashboard edges.
        
        Args:
            home_team: Home team name
            away_team: Away team name  
            league: League code (NBA, NFL, etc.)
            n_iterations: Number of simulation iterations
            home_context: Optional pre-fetched home team context dict (skips API call if provided)
            away_context: Optional pre-fetched away team context dict (skips API call if provided)
        
        Returns:
            Dict with score distributions and winner probabilities
        """
        from omega.data.stats_ingestion import get_team_context, TeamContext
        from omega.simulation.markov_engine import validate_team_context
        from omega.data.nfl_stats import get_nfl_team_context
        
        league = league.upper()
        
        if league == "NFL":
            home_ctx = get_nfl_team_context(home_team)
            away_ctx = get_nfl_team_context(away_team)
            
            if home_ctx is None:
                return {
                    "success": False,
                    "skipped": True,
                    "skip_reason": f"Missing NFL data for home team: {home_team}",
                    "home_team": home_team,
                    "away_team": away_team,
                    "league": league
                }
            
            if away_ctx is None:
                return {
                    "success": False,
                    "skipped": True,
                    "skip_reason": f"Missing NFL data for away team: {away_team}",
                    "home_team": home_team,
                    "away_team": away_team,
                    "league": league
                }
            
            result = run_nfl_game_simulation(
                home_team=home_team,
                away_team=away_team,
                home_context=home_ctx,
                away_context=away_ctx,
                n_iter=n_iterations
            )
            
            result["home_context"] = home_ctx.to_dict() if hasattr(home_ctx, 'to_dict') else {}
            result["away_context"] = away_ctx.to_dict() if hasattr(away_ctx, 'to_dict') else {}
            
            return result
        
        if home_context is not None:
            home_ctx = TeamContext.from_dict(home_context)
        else:
            home_ctx = get_team_context(home_team, league)
        
        if away_context is not None:
            away_ctx = TeamContext.from_dict(away_context)
        else:
            away_ctx = get_team_context(away_team, league)
        
        if home_ctx is None:
            return {
                "success": False,
                "skipped": True,
                "skip_reason": f"Missing data for home team: {home_team}",
                "home_team": home_team,
                "away_team": away_team,
                "league": league
            }
        
        if away_ctx is None:
            return {
                "success": False,
                "skipped": True,
                "skip_reason": f"Missing data for away team: {away_team}",
                "home_team": home_team,
                "away_team": away_team,
                "league": league
            }
        
        home_valid, home_issues = validate_team_context(home_ctx)
        away_valid, away_issues = validate_team_context(away_ctx)
        
        if not home_valid:
            return {
                "success": False,
                "skipped": True,
                "skip_reason": f"Invalid data for home team {home_team}: {', '.join(home_issues)}",
                "home_team": home_team,
                "away_team": away_team,
                "league": league
            }
        
        if not away_valid:
            return {
                "success": False,
                "skipped": True,
                "skip_reason": f"Invalid data for away team {away_team}: {', '.join(away_issues)}",
                "home_team": home_team,
                "away_team": away_team,
                "league": league
            }
        
        home_off = home_ctx.off_rating
        home_def = home_ctx.def_rating
        home_pace = home_ctx.pace
        
        away_off = away_ctx.off_rating
        away_def = away_ctx.def_rating
        away_pace = away_ctx.pace
        
        game_pace = (home_pace + away_pace) / 2.0
        
        if league == "NBA":
            possessions = game_pace
            home_expected = (home_off * (100 / away_def)) * (possessions / 100)
            away_expected = (away_off * (100 / home_def)) * (possessions / 100)
            home_std = 12.0
            away_std = 12.0
        else:
            home_expected = home_off if home_off else 110
            away_expected = away_off if away_off else 110
            home_std = 12.0
            away_std = 12.0
        
        home_scores = _normal_sample(home_expected, home_std, n_iterations)
        away_scores = _normal_sample(away_expected, away_std, n_iterations)
        
        home_wins = sum(1 for h, a in zip(home_scores, away_scores) if h > a)
        away_wins = sum(1 for h, a in zip(home_scores, away_scores) if a > h)
        
        home_mean = sum(home_scores) / n_iterations
        away_mean = sum(away_scores) / n_iterations
        
        return {
            "success": True,
            "home_team": home_team,
            "away_team": away_team,
            "league": league,
            "iterations": n_iterations,
            "home_win_prob": round(home_wins / n_iterations * 100, 1),
            "away_win_prob": round(away_wins / n_iterations * 100, 1),
            "predicted_home_score": round(home_mean, 1),
            "predicted_away_score": round(away_mean, 1),
            "predicted_spread": round(home_mean - away_mean, 1),
            "predicted_total": round(home_mean + away_mean, 1),
            "home_context": home_ctx.to_dict() if home_ctx and hasattr(home_ctx, 'to_dict') else {},
            "away_context": away_ctx.to_dict() if away_ctx and hasattr(away_ctx, 'to_dict') else {}
        }
    
    def run_game_simulation(
        self,
        home_team: str,
        away_team: str,
        league: str = "NBA",
        n_iterations: int = 1000
    ) -> Dict:
        """
        Run a full game simulation using real team stats.
        
        Args:
            home_team: Home team name
            away_team: Away team name  
            league: League code (NBA, NFL, etc.)
            n_iterations: Number of simulation iterations
        
        Returns:
            Dict with score distributions, winner probabilities, player projections
        """
        from omega.data.stats_ingestion import get_game_context
        from omega.simulation.markov_engine import MarkovSimulator
        
        game_ctx = get_game_context(home_team, away_team, league)
        
        home_context = game_ctx.get("home_context", {})
        away_context = game_ctx.get("away_context", {})
        home_players = game_ctx.get("home_players", [])
        away_players = game_ctx.get("away_players", [])
        
        all_players = []
        for p in home_players:
            player = dict(p)
            player["team_side"] = "home"
            all_players.append(player)
        for p in away_players:
            player = dict(p)
            player["team_side"] = "away"
            all_players.append(player)
        
        simulator = MarkovSimulator(
            league=league,
            players=all_players,
            home_context=home_context,
            away_context=away_context
        )
        
        home_scores = []
        away_scores = []
        all_player_stats: Dict[str, Dict[str, List]] = {}
        
        n_possessions = simulator._base_n_possessions
        
        for _ in range(n_iterations):
            game_state = simulator.simulate_game(n_possessions)
            home_scores.append(game_state.home_score)
            away_scores.append(game_state.away_score)
            
            for player_name, stats in game_state.player_stats.items():
                if player_name not in all_player_stats:
                    all_player_stats[player_name] = {}
                for stat_key, value in stats.items():
                    if stat_key not in all_player_stats[player_name]:
                        all_player_stats[player_name][stat_key] = []
                    all_player_stats[player_name][stat_key].append(value)
        
        home_mean = sum(home_scores) / len(home_scores)
        away_mean = sum(away_scores) / len(away_scores)
        
        home_wins = sum(1 for h, a in zip(home_scores, away_scores) if h > a)
        away_wins = sum(1 for h, a in zip(home_scores, away_scores) if a > h)
        
        player_projections = {}
        for player_name, stats in all_player_stats.items():
            player_projections[player_name] = {}
            for stat_key, values in stats.items():
                sorted_vals = sorted(values)
                n = len(sorted_vals)
                player_projections[player_name][stat_key] = {
                    "mean": sum(values) / n if n > 0 else 0,
                    "std": (sum((v - sum(values)/n)**2 for v in values) / n) ** 0.5 if n > 1 else 0,
                    "min": min(values) if values else 0,
                    "max": max(values) if values else 0,
                    "p10": sorted_vals[int(n * 0.1)] if n > 10 else min(values) if values else 0,
                    "p25": sorted_vals[int(n * 0.25)] if n > 4 else min(values) if values else 0,
                    "p50": sorted_vals[int(n * 0.5)] if n > 2 else sum(values)/n if values else 0,
                    "p75": sorted_vals[int(n * 0.75)] if n > 4 else max(values) if values else 0,
                    "p90": sorted_vals[int(n * 0.9)] if n > 10 else max(values) if values else 0
                }
        
        def get_histogram(scores, n_bins=10):
            if not scores:
                return []
            min_s, max_s = min(scores), max(scores)
            if max_s == min_s:
                return [{"bin": min_s, "count": len(scores)}]
            bin_width = (max_s - min_s) / n_bins
            bins = []
            for i in range(n_bins):
                bin_start = min_s + i * bin_width
                bin_end = bin_start + bin_width
                count = sum(1 for s in scores if bin_start <= s < bin_end)
                bins.append({"bin": round(bin_start, 1), "count": count})
            return bins
        
        return {
            "success": True,
            "home_team": home_team,
            "away_team": away_team,
            "league": league,
            "iterations": n_iterations,
            "home_win_prob": round(home_wins / n_iterations * 100, 1),
            "away_win_prob": round(away_wins / n_iterations * 100, 1),
            "predicted_home_score": round(home_mean, 1),
            "predicted_away_score": round(away_mean, 1),
            "predicted_spread": round(home_mean - away_mean, 1),
            "predicted_total": round(home_mean + away_mean, 1),
            "home_score_std": round((sum((s - home_mean)**2 for s in home_scores) / len(home_scores)) ** 0.5, 1),
            "away_score_std": round((sum((s - away_mean)**2 for s in away_scores) / len(away_scores)) ** 0.5, 1),
            "home_score_histogram": get_histogram(home_scores),
            "away_score_histogram": get_histogram(away_scores),
            "home_context": home_context,
            "away_context": away_context,
            "player_projections": player_projections,
            "home_scores_sample": [round(s, 1) for s in home_scores[:20]],
            "away_scores_sample": [round(s, 1) for s in away_scores[:20]]
        }
    
    def run_player_prop_simulation(
        self,
        player_name: str,
        team: str,
        opponent: str,
        league: str = "NBA",
        prop_type: str = "pts",
        line: float = 20.0,
        n_iterations: int = 500
    ) -> Dict:
        """
        Run player prop simulation focused on a specific player's stats.
        
        Args:
            player_name: Player's full name
            team: Player's team name
            opponent: Opponent team name
            league: League code
            prop_type: Stat type (pts, reb, ast, etc.)
            line: The betting line for the prop
            n_iterations: Number of simulation iterations
        
        Returns:
            Dict with hit probability, projected value, percentiles
        """
        from omega.data.stats_ingestion import get_game_context, get_player_context
        from omega.simulation.markov_engine import MarkovSimulator
        
        game_ctx = get_game_context(team, opponent, league)
        
        player_ctx = get_player_context(player_name, league)
        
        home_context = game_ctx.get("home_context", {})
        away_context = game_ctx.get("away_context", {})
        home_players = game_ctx.get("home_players", [])
        away_players = game_ctx.get("away_players", [])
        
        all_players = []
        player_found = False
        
        for p in home_players:
            player = dict(p)
            player["team_side"] = "home"
            if p.get("name", "").lower() == player_name.lower():
                player_found = True
                player["usage_rate"] = player_ctx.usage_rate
            all_players.append(player)
        
        for p in away_players:
            player = dict(p)
            player["team_side"] = "away"
            if p.get("name", "").lower() == player_name.lower():
                player_found = True
                player["usage_rate"] = player_ctx.usage_rate
            all_players.append(player)
        
        if not player_found:
            all_players.append({
                "name": player_name,
                "team_side": "home",
                "usage_rate": player_ctx.usage_rate,
                "pts_mean": player_ctx.pts_mean,
                "reb_mean": player_ctx.reb_mean,
                "ast_mean": player_ctx.ast_mean
            })
        
        simulator = MarkovSimulator(
            league=league,
            players=all_players,
            home_context=home_context,
            away_context=away_context
        )
        
        stat_values = []
        n_possessions = simulator._base_n_possessions
        
        for _ in range(n_iterations):
            game_state = simulator.simulate_game(n_possessions)
            stat_val = game_state.get_player_stat(player_name, prop_type)
            stat_values.append(stat_val)
        
        if not stat_values:
            return {
                "success": False,
                "error": "No stats generated",
                "player": player_name,
                "prop_type": prop_type,
                "line": line
            }
        
        sorted_vals = sorted(stat_values)
        n = len(sorted_vals)
        mean_val = sum(stat_values) / n
        std_val = (sum((v - mean_val)**2 for v in stat_values) / n) ** 0.5
        
        over_count = sum(1 for v in stat_values if v > line)
        under_count = sum(1 for v in stat_values if v < line)
        push_count = sum(1 for v in stat_values if abs(v - line) < 0.5)
        
        return {
            "success": True,
            "player": player_name,
            "prop_type": prop_type,
            "line": line,
            "projected_value": round(mean_val, 1),
            "std": round(std_val, 1),
            "hit_probability": round(over_count / n * 100, 1),
            "over_prob": round(over_count / n * 100, 1),
            "under_prob": round(under_count / n * 100, 1),
            "push_prob": round(push_count / n * 100, 1),
            "p10": round(sorted_vals[int(n * 0.1)], 1),
            "p25": round(sorted_vals[int(n * 0.25)], 1),
            "p50": round(sorted_vals[int(n * 0.5)], 1),
            "p75": round(sorted_vals[int(n * 0.75)], 1),
            "p90": round(sorted_vals[int(n * 0.9)], 1),
            "min": round(min(stat_values), 1),
            "max": round(max(stat_values), 1),
            "iterations": n_iterations
        }
