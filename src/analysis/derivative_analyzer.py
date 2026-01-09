"""
Derivative Edge Analyzer Module

Identifies 1Q (first quarter) and 1H (first half) betting edges for NBA and NFL.
Uses Markov simulation to model segment-level scoring and compare against book's
fractional lines.

Fractional Line Theory:
- Books typically price 1Q spread = FG spread / 4
- Books typically price 1H spread = FG spread / 2
- Teams with non-linear scoring patterns create edges when actual segment
  performance differs from these fractional expectations.
"""

from __future__ import annotations
import logging
import random
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple

from src.simulation.markov_engine import (
    MarkovSimulator,
    MarkovState,
    TransitionMatrix,
    validate_game_for_simulation
)

try:
    import numpy as np
except ImportError:
    np = None

logger = logging.getLogger(__name__)

LEAGUE_CONFIG = {
    "NBA": {
        "quarter_minutes": 12,
        "total_quarters": 4,
        "possessions_per_minute": 2.0,
        "half_checkpoint": 24,
        "quarter_checkpoint": 12,
    },
    "NFL": {
        "quarter_minutes": 15,
        "total_quarters": 4,
        "plays_per_minute": 2.5,
        "half_checkpoint": 30,
        "quarter_checkpoint": 15,
    }
}


@dataclass
class DerivativeEdge:
    """
    Represents a derivative betting edge for 1Q/1H markets.
    
    Attributes:
        game_id: Unique identifier for the game
        league: League code (NBA, NFL)
        home_team: Home team name
        away_team: Away team name
        fg_spread: Full game spread from book (negative = home favored)
        book_1q_spread: Book's 1Q spread (typically FG/4)
        book_1h_spread: Book's 1H spread (typically FG/2)
        model_1q_spread: Model's projected 1Q spread from simulation
        model_1h_spread: Model's projected 1H spread from simulation
        edge_1q: Edge on 1Q = model_spread - book_spread
        edge_1h: Edge on 1H = model_spread - book_spread
        confidence: "high" if |edge| > 1.5, "medium" if > 0.75, else "low"
        factors: List of qualitative factors driving the edge
    """
    game_id: str
    league: str
    home_team: str
    away_team: str
    fg_spread: float
    book_1q_spread: float
    book_1h_spread: float
    model_1q_spread: float
    model_1h_spread: float
    edge_1q: float
    edge_1h: float
    confidence: str
    factors: List[str] = field(default_factory=list)


@dataclass
class SegmentScores:
    """
    Holds segment-level scores from a single simulation run.
    
    Attributes:
        home_1q: Home team 1st quarter score
        away_1q: Away team 1st quarter score
        home_1h: Home team 1st half score
        away_1h: Away team 1st half score
        home_fg: Home team full game score
        away_fg: Away team full game score
    """
    home_1q: float = 0.0
    away_1q: float = 0.0
    home_1h: float = 0.0
    away_1h: float = 0.0
    home_fg: float = 0.0
    away_fg: float = 0.0


@dataclass
class TeamDerivativeProfile:
    """
    Profile describing a team's segment-level scoring tendencies.
    
    Attributes:
        team_name: Name of the team
        fast_starter: True if team exceeds FG/4 expectation in 1Q
        slow_starter: True if team underperforms in 1Q
        closer: True if team outperforms in 4Q
        frontrunner: True if team builds leads but doesn't extend them
        avg_1q_differential: Average 1Q scoring differential vs FG/4 expectation
        avg_1h_differential: Average 1H scoring differential vs FG/2 expectation
    """
    team_name: str
    fast_starter: bool = False
    slow_starter: bool = False
    closer: bool = False
    frontrunner: bool = False
    avg_1q_differential: float = 0.0
    avg_1h_differential: float = 0.0


class DerivativeEdgeAnalyzer:
    """
    Analyzes 1Q and 1H betting edges using Markov simulation.
    
    Uses the existing MarkovSimulator to run segment-level simulations,
    then compares model spreads against book's fractional lines to
    identify derivative betting edges.
    """
    
    def __init__(
        self,
        league: str = "NBA",
        n_simulations: int = 1000,
        home_context: Optional[Any] = None,
        away_context: Optional[Any] = None
    ):
        """
        Initialize the DerivativeEdgeAnalyzer.
        
        Args:
            league: League code (NBA or NFL)
            n_simulations: Number of Monte Carlo simulations to run
            home_context: TeamContext or dict with home team ratings/pace
            away_context: TeamContext or dict with away team ratings/pace
        """
        self.league = league.upper()
        self.n_simulations = n_simulations
        self.home_context = home_context
        self.away_context = away_context
        
        if self.league not in LEAGUE_CONFIG:
            logger.warning(f"League {self.league} not configured, defaulting to NBA")
            self.league = "NBA"
        
        self.config = LEAGUE_CONFIG[self.league]
        self._team_profiles: Dict[str, TeamDerivativeProfile] = {}
    
    def _get_context_value(self, context: Any, key: str, default: float) -> float:
        """Safely get a value from a context (dict or dataclass)."""
        if context is None:
            return default
        if isinstance(context, dict):
            return context.get(key, default)
        return getattr(context, key, default)
    
    def _calculate_possessions_for_segment(self, segment_minutes: float) -> int:
        """
        Calculate number of possessions/plays for a time segment.
        
        Args:
            segment_minutes: Duration of the segment in minutes
        
        Returns:
            Number of possessions to simulate
        """
        if self.league == "NBA":
            base_rate = self.config["possessions_per_minute"]
            if self.home_context and self.away_context:
                home_pace = self._get_context_value(self.home_context, 'pace', 100.0)
                away_pace = self._get_context_value(self.away_context, 'pace', 100.0)
                pace_factor = ((home_pace + away_pace) / 2) / 100.0
                base_rate *= pace_factor
            return int(segment_minutes * base_rate)
        elif self.league == "NFL":
            base_rate = self.config["plays_per_minute"]
            return int(segment_minutes * base_rate)
        return int(segment_minutes * 2.0)
    
    def simulate_segment(
        self,
        players: List[Dict[str, Any]],
        segment_type: str = "1Q",
        seed: Optional[int] = None
    ) -> SegmentScores:
        """
        Simulate a game segment and return scores at checkpoints.
        
        Runs the MarkovSimulator for the appropriate number of possessions
        based on segment type, capturing scores at 1Q, 1H, and FG.
        
        Args:
            players: List of player dicts with stats and usage rates
            segment_type: "1Q" for first quarter, "1H" for first half, "FG" for full game
            seed: Random seed for reproducibility
        
        Returns:
            SegmentScores with scores at each checkpoint
        """
        if seed is not None:
            random.seed(seed)
            if np is not None:
                np.random.seed(seed)
        
        simulator = MarkovSimulator(
            league=self.league,
            players=players,
            home_context=self.home_context,
            away_context=self.away_context
        )
        
        quarter_minutes = self.config["quarter_minutes"]
        
        q1_possessions = self._calculate_possessions_for_segment(quarter_minutes)
        q2_possessions = self._calculate_possessions_for_segment(quarter_minutes)
        h2_possessions = self._calculate_possessions_for_segment(quarter_minutes * 2)
        
        scores = SegmentScores()
        
        state = MarkovState(league=self.league)
        home_players = [p for p in players if p.get("team_side") == "home" or p.get("is_home", False)]
        away_players = [p for p in players if p.get("team_side") == "away" or not p.get("is_home", True)]
        
        if not home_players:
            home_players = players[:len(players)//2]
        if not away_players:
            away_players = players[len(players)//2:]
        
        for _ in range(q1_possessions):
            if self.league == "NBA":
                state = simulator._simulate_nba_possession(state, home_players, away_players)
            elif self.league == "NFL":
                state = simulator._simulate_nfl_play(state, home_players, away_players)
        
        scores.home_1q = state.home_score
        scores.away_1q = state.away_score
        
        if segment_type == "1Q":
            scores.home_1h = scores.home_1q
            scores.away_1h = scores.away_1q
            scores.home_fg = scores.home_1q
            scores.away_fg = scores.away_1q
            return scores
        
        for _ in range(q2_possessions):
            if self.league == "NBA":
                state = simulator._simulate_nba_possession(state, home_players, away_players)
            elif self.league == "NFL":
                state = simulator._simulate_nfl_play(state, home_players, away_players)
        
        scores.home_1h = state.home_score
        scores.away_1h = state.away_score
        
        if segment_type == "1H":
            scores.home_fg = scores.home_1h
            scores.away_fg = scores.away_1h
            return scores
        
        for _ in range(h2_possessions):
            if self.league == "NBA":
                state = simulator._simulate_nba_possession(state, home_players, away_players)
            elif self.league == "NFL":
                state = simulator._simulate_nfl_play(state, home_players, away_players)
        
        scores.home_fg = state.home_score
        scores.away_fg = state.away_score
        
        return scores
    
    def calculate_derivative_edges(
        self,
        game_id: str,
        home_team: str,
        away_team: str,
        fg_spread: float,
        fg_total: Optional[float] = None,
        players: Optional[List[Dict[str, Any]]] = None
    ) -> DerivativeEdge:
        """
        Calculate 1Q and 1H betting edges by comparing model spreads to book lines.
        
        The book typically prices derivatives as:
        - 1Q spread = FG spread / 4
        - 1H spread = FG spread / 2
        
        We run Monte Carlo simulations with segment stops to calculate the model's
        actual expected 1Q and 1H spreads, then compute the edge.
        
        Args:
            game_id: Unique game identifier
            home_team: Home team name
            away_team: Away team name
            fg_spread: Full game spread from book (negative = home favored)
            fg_total: Full game total from book (optional)
            players: List of player dicts for simulation (optional)
        
        Returns:
            DerivativeEdge with edge calculations and confidence rating
        """
        book_1q_spread = fg_spread / 4
        book_1h_spread = fg_spread / 2
        
        if players is None:
            players = self._generate_default_players(home_team, away_team)
        
        q1_spreads = []
        h1_spreads = []
        fg_spreads = []
        
        for i in range(self.n_simulations):
            scores = self.simulate_segment(players, segment_type="FG", seed=i)
            
            q1_spread = scores.home_1q - scores.away_1q
            h1_spread = scores.home_1h - scores.away_1h
            fg_sim_spread = scores.home_fg - scores.away_fg
            
            q1_spreads.append(q1_spread)
            h1_spreads.append(h1_spread)
            fg_spreads.append(fg_sim_spread)
        
        model_1q_spread = sum(q1_spreads) / len(q1_spreads)
        model_1h_spread = sum(h1_spreads) / len(h1_spreads)
        
        edge_1q = model_1q_spread - book_1q_spread
        edge_1h = model_1h_spread - book_1h_spread
        
        max_edge = max(abs(edge_1q), abs(edge_1h))
        if max_edge > 1.5:
            confidence = "high"
        elif max_edge > 0.75:
            confidence = "medium"
        else:
            confidence = "low"
        
        factors = self._generate_edge_factors(
            home_team, away_team, 
            model_1q_spread, book_1q_spread,
            model_1h_spread, book_1h_spread,
            q1_spreads, h1_spreads
        )
        
        return DerivativeEdge(
            game_id=game_id,
            league=self.league,
            home_team=home_team,
            away_team=away_team,
            fg_spread=fg_spread,
            book_1q_spread=round(book_1q_spread, 2),
            book_1h_spread=round(book_1h_spread, 2),
            model_1q_spread=round(model_1q_spread, 2),
            model_1h_spread=round(model_1h_spread, 2),
            edge_1q=round(edge_1q, 2),
            edge_1h=round(edge_1h, 2),
            confidence=confidence,
            factors=factors
        )
    
    def get_team_derivative_profile(
        self,
        team_name: str,
        team_context: Optional[Any] = None,
        opponents: Optional[List[Dict[str, Any]]] = None,
        n_games: int = 100
    ) -> TeamDerivativeProfile:
        """
        Analyze a team's segment-level scoring patterns.
        
        Runs multiple simulations to determine if a team is:
        - fast_starter: Exceeds FG/4 expectation in 1Q
        - slow_starter: Underperforms in 1Q
        - closer: Outperforms in 4Q
        - frontrunner: Builds leads but doesn't extend them
        
        Args:
            team_name: Name of the team to profile
            team_context: TeamContext or dict with team ratings
            opponents: List of opponent player dicts for simulation
            n_games: Number of games to simulate for profiling
        
        Returns:
            TeamDerivativeProfile with team's scoring tendencies
        """
        if team_name in self._team_profiles:
            return self._team_profiles[team_name]
        
        players = self._generate_team_players(team_name, is_home=True)
        if opponents is None:
            opponents = self._generate_default_opponents()
        
        all_players = players + opponents
        
        q1_diffs = []
        h1_diffs = []
        h2_diffs = []
        q4_diffs = []
        
        for i in range(n_games):
            scores = self.simulate_segment(all_players, segment_type="FG", seed=i * 100)
            
            fg_margin = scores.home_fg - scores.away_fg
            
            expected_1q_margin = fg_margin / 4
            expected_1h_margin = fg_margin / 2
            expected_q4_margin = fg_margin / 4
            
            actual_1q_margin = scores.home_1q - scores.away_1q
            actual_1h_margin = scores.home_1h - scores.away_1h
            actual_h2_margin = fg_margin - actual_1h_margin
            actual_q4_margin = actual_h2_margin / 2
            
            q1_diffs.append(actual_1q_margin - expected_1q_margin)
            h1_diffs.append(actual_1h_margin - expected_1h_margin)
            h2_diffs.append(actual_h2_margin - expected_1h_margin)
            q4_diffs.append(actual_q4_margin - expected_q4_margin)
        
        avg_1q_diff = sum(q1_diffs) / len(q1_diffs)
        avg_1h_diff = sum(h1_diffs) / len(h1_diffs)
        avg_h2_diff = sum(h2_diffs) / len(h2_diffs)
        avg_q4_diff = sum(q4_diffs) / len(q4_diffs)
        
        fast_starter = avg_1q_diff > 0.5
        slow_starter = avg_1q_diff < -0.5
        closer = avg_q4_diff > 0.5
        frontrunner = avg_1h_diff > 0.5 and avg_h2_diff < 0
        
        profile = TeamDerivativeProfile(
            team_name=team_name,
            fast_starter=fast_starter,
            slow_starter=slow_starter,
            closer=closer,
            frontrunner=frontrunner,
            avg_1q_differential=round(avg_1q_diff, 2),
            avg_1h_differential=round(avg_1h_diff, 2)
        )
        
        self._team_profiles[team_name] = profile
        return profile
    
    def _generate_default_players(
        self,
        home_team: str,
        away_team: str
    ) -> List[Dict[str, Any]]:
        """
        Generate default player lists when no players provided.
        
        Creates synthetic players based on team context or league averages.
        
        Args:
            home_team: Home team name
            away_team: Away team name
        
        Returns:
            List of player dicts for simulation
        """
        players = []
        
        home_off = self._get_context_value(self.home_context, 'off_rating', 110.0)
        home_pace = self._get_context_value(self.home_context, 'pace', 100.0)
        away_off = self._get_context_value(self.away_context, 'off_rating', 110.0)
        away_pace = self._get_context_value(self.away_context, 'pace', 100.0)
        
        for i in range(5):
            usage = 0.25 if i == 0 else 0.20 if i == 1 else 0.15
            players.append({
                "name": f"{home_team}_Player_{i+1}",
                "team": home_team,
                "team_side": "home",
                "is_home": True,
                "usage_rate": usage,
                "rebound_rate": 0.10 + (0.05 * (4 - i) if i < 3 else 0),
                "pts_mean": home_off / 5 * usage * 2,
            })
        
        for i in range(5):
            usage = 0.25 if i == 0 else 0.20 if i == 1 else 0.15
            players.append({
                "name": f"{away_team}_Player_{i+1}",
                "team": away_team,
                "team_side": "away",
                "is_home": False,
                "usage_rate": usage,
                "rebound_rate": 0.10 + (0.05 * (4 - i) if i < 3 else 0),
                "pts_mean": away_off / 5 * usage * 2,
            })
        
        return players
    
    def _generate_team_players(
        self,
        team_name: str,
        is_home: bool = True
    ) -> List[Dict[str, Any]]:
        """Generate synthetic players for a single team."""
        context = self.home_context if is_home else self.away_context
        off_rating = self._get_context_value(context, 'off_rating', 110.0)
        
        players = []
        for i in range(5):
            usage = 0.25 if i == 0 else 0.20 if i == 1 else 0.15
            players.append({
                "name": f"{team_name}_Player_{i+1}",
                "team": team_name,
                "team_side": "home" if is_home else "away",
                "is_home": is_home,
                "usage_rate": usage,
                "rebound_rate": 0.10,
                "pts_mean": off_rating / 5 * usage * 2,
            })
        return players
    
    def _generate_default_opponents(self) -> List[Dict[str, Any]]:
        """Generate generic opponent players."""
        players = []
        for i in range(5):
            usage = 0.22 if i == 0 else 0.18 if i == 1 else 0.14
            players.append({
                "name": f"Opponent_Player_{i+1}",
                "team": "Opponent",
                "team_side": "away",
                "is_home": False,
                "usage_rate": usage,
                "rebound_rate": 0.10,
                "pts_mean": 22.0 * usage * 2,
            })
        return players
    
    def _generate_edge_factors(
        self,
        home_team: str,
        away_team: str,
        model_1q: float,
        book_1q: float,
        model_1h: float,
        book_1h: float,
        q1_spreads: List[float],
        h1_spreads: List[float]
    ) -> List[str]:
        """
        Generate qualitative factors explaining the edge.
        
        Args:
            home_team: Home team name
            away_team: Away team name
            model_1q: Model's 1Q spread projection
            book_1q: Book's 1Q spread line
            model_1h: Model's 1H spread projection
            book_1h: Book's 1H spread line
            q1_spreads: List of 1Q spreads from simulations
            h1_spreads: List of 1H spreads from simulations
        
        Returns:
            List of factor strings
        """
        factors = []
        
        home_profile = self.get_team_derivative_profile(home_team)
        away_profile = self.get_team_derivative_profile(away_team)
        
        if home_profile.fast_starter and model_1q > book_1q:
            factors.append(f"{home_team} fast starter profile supports 1Q edge")
        
        if away_profile.slow_starter and model_1q > book_1q:
            factors.append(f"{away_team} slow starter at {home_team}'s venue")
        
        if home_profile.fast_starter:
            factors.append(f"{home_team} scripted opener (+{home_profile.avg_1q_differential:.1f} 1Q)")
        
        if away_profile.fast_starter and model_1q < book_1q:
            factors.append(f"{away_team} strong opening tendency")
        
        if home_profile.frontrunner and model_1h > book_1h:
            factors.append(f"{home_team} frontrunner profile supports 1H")
        
        if home_profile.closer:
            factors.append(f"{home_team} closer tendency (2H strength)")
        
        q1_std = (sum((x - model_1q) ** 2 for x in q1_spreads) / len(q1_spreads)) ** 0.5
        if q1_std < 3.0:
            factors.append("Low 1Q variance increases confidence")
        elif q1_std > 6.0:
            factors.append("High 1Q variance reduces confidence")
        
        if not factors:
            if abs(model_1q - book_1q) > 1.0:
                factors.append(f"Model shows {abs(model_1q - book_1q):.1f}pt 1Q deviation")
            else:
                factors.append("Minor edge based on pace/efficiency differentials")
        
        return factors


def analyze_derivative_edges(
    game_id: str,
    home_team: str,
    away_team: str,
    fg_spread: float,
    league: str = "NBA",
    home_context: Optional[Any] = None,
    away_context: Optional[Any] = None,
    n_simulations: int = 1000
) -> DerivativeEdge:
    """
    Convenience function to analyze derivative edges for a single game.
    
    Args:
        game_id: Unique game identifier
        home_team: Home team name
        away_team: Away team name
        fg_spread: Full game spread from book
        league: League code (NBA or NFL)
        home_context: TeamContext for home team
        away_context: TeamContext for away team
        n_simulations: Number of Monte Carlo simulations
    
    Returns:
        DerivativeEdge with edge calculations
    """
    analyzer = DerivativeEdgeAnalyzer(
        league=league,
        n_simulations=n_simulations,
        home_context=home_context,
        away_context=away_context
    )
    
    return analyzer.calculate_derivative_edges(
        game_id=game_id,
        home_team=home_team,
        away_team=away_team,
        fg_spread=fg_spread
    )


if __name__ == "__main__":
    import json
    
    edge = analyze_derivative_edges(
        game_id="test_game_001",
        home_team="Los Angeles Lakers",
        away_team="Golden State Warriors",
        fg_spread=-5.5,
        league="NBA",
        n_simulations=100
    )
    
    result = {
        "game_id": edge.game_id,
        "league": edge.league,
        "home_team": edge.home_team,
        "away_team": edge.away_team,
        "fg_spread": edge.fg_spread,
        "book_1q_spread": edge.book_1q_spread,
        "book_1h_spread": edge.book_1h_spread,
        "model_1q_spread": edge.model_1q_spread,
        "model_1h_spread": edge.model_1h_spread,
        "edge_1q": edge.edge_1q,
        "edge_1h": edge.edge_1h,
        "confidence": edge.confidence,
        "factors": edge.factors
    }
    
    print(json.dumps(result, indent=2))
