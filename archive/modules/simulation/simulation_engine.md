# Simulation Engine Module

"""
Module Name: Simulation Engine
Version: 2.0.0
Description: Runs Monte Carlo simulations for team markets (spreads, totals, ML) and player props, selecting Normal vs Poisson automatically.
Functions:
    - select_distribution(metric_key: str, league: str) -> str
    - run_game_simulation(projection: dict, n_iter: int = 10000, seed: int | None = None, league: str | None = None) -> dict
    - simulate_totals(mean: float, variance: float, market_total: float, dist: str, n_iter: int = 10000) -> dict
    - simulate_totals_auto(mean: float, variance: float, market_total: float, metric_key: str, league: str, n_iter: int = 10000, seed: int | None = None) -> dict
    - run_player_simulation(player_proj: dict, n_iter: int = 10000, seed: int | None = None) -> dict
Usage Notes:
    - Requires ≥10,000 iterations; escalate when edge is thin.
    - Accepts `variance_scalar` from projection_model.
    - Use `simulate_totals_auto` for totals; it auto-selects distribution via `select_distribution`.
    - Use `run_player_simulation` for player props (points, rebounds, yards, etc.).
"""

```python
from __future__ import annotations
import random
from typing import Dict, Optional

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None

def select_distribution(metric_key: str, league: str) -> str:
    """
    Selects appropriate distribution (Normal vs Poisson) based on metric and league.
    
    Args:
        metric_key: Stat identifier (e.g., "score", "pts", "reb", "pass_yds", "rush_yds", "run_rate", "goal_rate")
        league: League identifier (e.g., "NBA", "NFL", "MLB", "NHL")
    
    Returns:
        "poisson" for discrete/count stats, "normal" for continuous stats
    """
    league = league.upper()
    metric_key = metric_key.lower()
    
    # Always Poisson for run/goal rates and MLB/NHL team scoring
    if metric_key in {"run_rate", "goal_rate"} or league in {"MLB", "NHL"}:
        return "poisson"
    
    # NFL/NCAAF team scoring uses Poisson
    if league in {"NFL", "NCAAF"} and metric_key == "score":
        return "poisson"
    
    # Player props: discrete stats use Poisson, continuous use Normal
    # Discrete: points (for low-scoring sports), goals, touchdowns, receptions
    discrete_stats = {"goals", "td", "touchdowns", "receptions", "rec", "sog"}  # shots on goal
    if metric_key in discrete_stats:
        return "poisson"
    
    # Continuous: points (NBA), rebounds, assists, yards, etc.
    # Default to Normal for most player props
    return "normal"

def _poisson_sample(lam: float, size: int) -> list:
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

def _normal_sample(mu: float, sigma: float, size: int) -> list:
    sigma = max(0.1, sigma)
    if np is not None:
        return np.random.normal(mu, sigma, size).tolist()
    return [random.gauss(mu, sigma) for _ in range(size)]

def run_game_simulation(projection: Dict, n_iter: int = 10000, seed: Optional[int] = None, league: Optional[str] = None) -> Dict:
    """
    Simulates a game between two teams, returning win probabilities and score distributions.
    
    Args:
        projection: Dict with keys:
            - "off_rating": dict mapping team names to offensive ratings
            - "league": str (e.g., "NBA", "NFL") - used if league kwarg not provided
            - "variance_scalar": float (optional, default 1.0)
        n_iter: Number of simulation iterations
        seed: Random seed for reproducibility
        league: Optional league override; if provided, takes precedence over projection["league"]
    
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
    
    # Resolve league: kwarg takes precedence, then projection dict, then default to NFL
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

def simulate_totals(mean: float, variance: float, market_total: float, dist: str, n_iter: int = 10000) -> Dict:
    """
    Simulates totals (over/under) with explicit distribution selection.
    For automatic distribution selection, use simulate_totals_auto instead.
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

def simulate_totals_auto(mean: float, variance: float, market_total: float, metric_key: str, league: str, n_iter: int = 10000, seed: Optional[int] = None) -> Dict:
    """
    Automatically selects distribution (Normal vs Poisson) and simulates totals.
    
    Args:
        mean: Expected total (e.g., combined team scores)
        variance: Variance of the total
        market_total: The betting line (over/under)
        metric_key: Stat key (e.g., "score", "run_rate", "goal_rate") for distribution selection
        league: League identifier (e.g., "NBA", "NFL", "MLB")
        n_iter: Number of simulation iterations
        seed: Random seed for reproducibility
    
    Returns:
        Dict with keys: "over_prob", "under_prob", "push_prob", "mean", "std"
    """
    if seed is not None:
        random.seed(seed)
        if np is not None:
            np.random.seed(seed)
    dist = select_distribution(metric_key, league)
    return simulate_totals(mean, variance, market_total, dist, n_iter)

def run_player_simulation(player_proj: Dict, n_iter: int = 10000, seed: Optional[int] = None) -> Dict:
    """
    Simulates a single player stat (e.g., points, rebounds, passing yards) vs a market line.
    
    Expected player_proj schema:
      {
        "league": "NBA" or "NFL" or other,
        "player_name": "Tyrese Haliburton",
        "team": "IND",
        "opp_team": "DET",
        "stat_key": "pts",   # or "reb", "ast", "pass_yds", "rush_yds", "sog", etc.
        "mean": 25.3,        # context & injury adjusted
        "variance": 12.1,
        "market_line": 24.5,
      }
    
    Behavior:
      1) Uses select_distribution(stat_key, league) to choose distribution family.
      2) Draws n_iter samples from that distribution.
      3) Computes:
           - over_prob = P(sample > market_line)
           - under_prob = P(sample < market_line)
           - push_prob if integer lines and pushes matter.
           - empirical mean and std of samples.
    
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
    
    # Select distribution based on stat and league
    dist = select_distribution(stat_key, league)
    
    # Generate samples
    sigma = max(0.1, variance ** 0.5)
    if dist == "poisson":
        samples = _poisson_sample(mean, n_iter)
    else:
        samples = _normal_sample(mean, sigma, n_iter)
    
    # Compute probabilities
    over_hits = sum(1 for x in samples if x > market_line)
    under_hits = sum(1 for x in samples if x < market_line)
    push_hits = sum(1 for x in samples if abs(x - market_line) < 0.5)
    
    # Compute empirical statistics
    sample_mean = sum(samples) / n_iter
    sample_variance = sum((x - sample_mean) ** 2 for x in samples) / n_iter
    sample_std = sample_variance ** 0.5
    
    return {
        "over_prob": over_hits / n_iter,
        "under_prob": under_hits / n_iter,
        "push_prob": push_hits / n_iter,
        "mean": sample_mean,
        "std": sample_std,
        "samples": samples[:100] if len(samples) > 100 else samples  # Return sample for inspection
    }
```

