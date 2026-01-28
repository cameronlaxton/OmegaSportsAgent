"""
Markov Play-by-Play Simulation Engine

Simulates games play-by-play using Markov chains to model state transitions
and accumulate player statistics. Particularly useful for player props where
individual play involvement matters.

AUTONOMOUS CALIBRATION:
This engine uses the AutoCalibrator system to continuously improve accuracy
by learning from historical predictions and outcomes.
"""

from __future__ import annotations
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, TYPE_CHECKING
import random

if TYPE_CHECKING:
    from src.data.stats_ingestion import TeamContext, PlayerContext

try:
    import numpy as np
except ImportError:
    np = None

try:
    from src.validation import get_tuned_parameter
    CALIBRATION_ENABLED = True
except ImportError:
    CALIBRATION_ENABLED = False
    def get_tuned_parameter(name: str, default: Any) -> Any:
        return default

logger = logging.getLogger(__name__)

DATA_INTEGRITY_LOG_PATH = "data/logs/data_integrity_log.json"


def _log_validation_to_integrity_file(entry: Dict[str, Any]) -> None:
    """Append a validation entry to the data integrity log file."""
    try:
        os.makedirs(os.path.dirname(DATA_INTEGRITY_LOG_PATH), exist_ok=True)
        
        entries = []
        if os.path.exists(DATA_INTEGRITY_LOG_PATH):
            try:
                with open(DATA_INTEGRITY_LOG_PATH, 'r') as f:
                    entries = json.load(f)
            except (json.JSONDecodeError, IOError):
                entries = []
        
        entries.append(entry)
        
        if len(entries) > 1000:
            entries = entries[-1000:]
        
        with open(DATA_INTEGRITY_LOG_PATH, 'w') as f:
            json.dump(entries, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to write to data integrity log: {e}")


def validate_team_context(context: Any) -> Tuple[bool, List[str]]:
    """
    Check if team has required stats for simulation.
    
    Critical: This enforces the no-defaults policy. If validation fails,
    the game should be skipped from betting recommendations.
    
    Args:
        context: TeamContext object or dict with team stats
    
    Returns:
        Tuple of (is_valid, list of issues)
    """
    issues = []
    
    if context is None:
        issues.append("No team context provided")
        return False, issues
    
    if isinstance(context, dict):
        off_rating = context.get("off_rating", 0)
        def_rating = context.get("def_rating", 0)
        pace = context.get("pace", 0)
        team_name = context.get("name", "Unknown")
    else:
        off_rating = getattr(context, "off_rating", 0)
        def_rating = getattr(context, "def_rating", 0)
        pace = getattr(context, "pace", 0)
        team_name = getattr(context, "name", "Unknown")
    
    if off_rating is None or off_rating <= 0:
        issues.append("Missing offensive rating")
    
    if def_rating is None or def_rating <= 0:
        issues.append("Missing defensive rating")
    
    if pace is None or pace <= 0:
        issues.append("Missing pace")
    
    is_valid = len(issues) == 0
    
    if not is_valid:
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "team_validation_failure",
            "entity": team_name,
            "entity_type": "team",
            "issues": issues,
            "data": {
                "off_rating": off_rating,
                "def_rating": def_rating,
                "pace": pace
            }
        }
        _log_validation_to_integrity_file(entry)
        logger.warning(f"Team validation failed for {team_name}: {', '.join(issues)}")
    
    return is_valid, issues


def validate_player_context(context: Any) -> Tuple[bool, List[str]]:
    """
    Check if player has required stats for simulation.
    
    Critical: This enforces the no-defaults policy. If validation fails,
    the player prop should be skipped.
    
    Args:
        context: PlayerContext object or dict with player stats
    
    Returns:
        Tuple of (is_valid, list of issues)
    """
    issues = []
    
    if context is None:
        issues.append("No player context provided")
        return False, issues
    
    if isinstance(context, dict):
        pts_mean = context.get("pts_mean", 0)
        player_name = context.get("name", "Unknown")
    else:
        pts_mean = getattr(context, "pts_mean", 0)
        player_name = getattr(context, "name", "Unknown")
    
    if pts_mean is None or pts_mean <= 0:
        issues.append("Missing points average")
    
    is_valid = len(issues) == 0
    
    if not is_valid:
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "player_validation_failure",
            "entity": player_name,
            "entity_type": "player",
            "issues": issues
        }
        _log_validation_to_integrity_file(entry)
        logger.warning(f"Player validation failed for {player_name}: {', '.join(issues)}")
    
    return is_valid, issues


def validate_game_for_simulation(
    home_context: Any, 
    away_context: Any
) -> Tuple[bool, str, List[str]]:
    """
    Validate that a game has complete data for simulation.
    
    This is the primary entry point for the no-defaults policy.
    If this returns False, the game should be SKIPPED from betting recommendations.
    
    Args:
        home_context: Home team's TeamContext
        away_context: Away team's TeamContext
    
    Returns:
        Tuple of (is_valid, skip_reason, all_issues)
    """
    all_issues = []
    
    home_valid, home_issues = validate_team_context(home_context)
    if not home_valid:
        home_name = getattr(home_context, 'name', 'Home team') if home_context else 'Home team'
        all_issues.extend([f"{home_name}: {issue}" for issue in home_issues])
    
    away_valid, away_issues = validate_team_context(away_context)
    if not away_valid:
        away_name = getattr(away_context, 'name', 'Away team') if away_context else 'Away team'
        all_issues.extend([f"{away_name}: {issue}" for issue in away_issues])
    
    is_valid = home_valid and away_valid
    
    if is_valid:
        skip_reason = ""
    else:
        skip_reason = f"Incomplete data: {'; '.join(all_issues)}"
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "game_skipped",
            "reason": skip_reason,
            "issues": all_issues
        }
        _log_validation_to_integrity_file(entry)
    
    return is_valid, skip_reason, all_issues


@dataclass
class GameContext:
    """
    Context for dynamic probability adjustments (Clutch Time, Garbage Time, etc.).

    Attributes:
        time_remaining: Minutes remaining in the game
        score_differential: Home score minus away score (positive = home leading)
        period: Current period/quarter
        is_clutch: Whether we're in clutch time (auto-calculated)
        is_garbage_time: Whether we're in garbage time (auto-calculated)
    """
    time_remaining: float = 48.0  # Full game for NBA
    score_differential: float = 0.0
    period: int = 1

    @property
    def is_clutch(self) -> bool:
        """
        Clutch time: Less than 2 minutes remaining AND game within 5 points.
        This is when star players take over and pace slows down.
        """
        return self.time_remaining < 2.0 and abs(self.score_differential) <= 5

    @property
    def is_garbage_time(self) -> bool:
        """
        Garbage time: Game is effectively over (large lead late).
        Starters rest, bench players get minutes.
        """
        return self.time_remaining < 5.0 and abs(self.score_differential) > 20


@dataclass
class MarkovState:
    """Represents a state in the Markov chain simulation."""
    league: str
    period: int = 1
    time_remaining: float = 48.0  # Total game time in minutes (NBA default)
    home_score: float = 0.0
    away_score: float = 0.0
    possession_team: str = "home"
    down: int = 1
    distance: float = 10.0
    field_position: float = 25.0
    player_stats: Dict[str, Dict[str, float]] = field(default_factory=dict)

    def get_player_stat(self, player_name: str, stat_key: str) -> float:
        """Get accumulated stat for a player."""
        return self.player_stats.get(player_name, {}).get(stat_key, 0.0)

    def add_player_stat(self, player_name: str, stat_key: str, value: float) -> None:
        """Add to a player's accumulated stat."""
        if player_name not in self.player_stats:
            self.player_stats[player_name] = {}
        if stat_key not in self.player_stats[player_name]:
            self.player_stats[player_name][stat_key] = 0.0
        self.player_stats[player_name][stat_key] += value

    @property
    def score_differential(self) -> float:
        """Home score minus away score."""
        return self.home_score - self.away_score

    def get_context(self) -> GameContext:
        """Get current game context for dynamic probability adjustments."""
        return GameContext(
            time_remaining=self.time_remaining,
            score_differential=self.score_differential,
            period=self.period
        )


class TransitionMatrix:
    """
    Manages transition probabilities between game states.
    
    Each league has different state transitions:
    - NBA: Possession outcomes (shot, turnover, foul, etc.)
    - NFL: Play outcomes (pass, rush, sack, turnover, etc.)
    - MLB: Plate appearance outcomes (hit, out, walk, etc.)
    - NHL: Shift outcomes (shot, goal, turnover, etc.)
    """
    
    def __init__(self, league: str):
        self.league = league.upper()
        self._transitions = self._build_default_transitions()
    
    def _build_default_transitions(self) -> Dict[str, Dict[str, float]]:
        """Build default transition probabilities by league with autonomous calibration."""
        if self.league == "NBA":
            # Get calibrated shot allocation for star players
            star_allocation = get_tuned_parameter("markov_shot_allocation_star", 0.30)
            
            # Distribute remaining allocation proportionally
            remaining = 1.0 - star_allocation
            secondary = remaining * 0.357  # ~25% of 70%
            tertiary = remaining * 0.286   # ~20% of 70%
            other = remaining * 0.357      # ~25% of 70%
            
            return {
                "possession": {
                    "two_point_make": 0.35,
                    "two_point_miss": 0.20,
                    "three_point_make": 0.12,
                    "three_point_miss": 0.18,
                    "free_throws": 0.08,
                    "turnover": 0.07
                },
                "shot_allocation": {
                    "star_player": star_allocation,
                    "secondary": secondary,
                    "tertiary": tertiary,
                    "other": other
                }
            }
        elif self.league == "NFL":
            return {
                "play_type": {
                    "pass": 0.58,
                    "rush": 0.38,
                    "sack": 0.04
                },
                "pass_result": {
                    "complete": 0.65,
                    "incomplete": 0.28,
                    "interception": 0.02,
                    "sack": 0.05
                },
                "rush_result": {
                    "positive": 0.55,
                    "negative": 0.20,
                    "fumble": 0.02,
                    "no_gain": 0.23
                },
                "scoring": {
                    "touchdown": 0.20,
                    "field_goal": 0.15,
                    "no_score": 0.65
                }
            }
        elif self.league == "MLB":
            return {
                "plate_appearance": {
                    "single": 0.15,
                    "double": 0.05,
                    "triple": 0.005,
                    "home_run": 0.03,
                    "walk": 0.08,
                    "strikeout": 0.22,
                    "ground_out": 0.25,
                    "fly_out": 0.20,
                    "other_out": 0.015
                }
            }
        elif self.league == "NHL":
            return {
                "possession": {
                    "shot_on_goal": 0.25,
                    "shot_blocked": 0.15,
                    "shot_missed": 0.10,
                    "turnover": 0.20,
                    "clear": 0.15,
                    "faceoff": 0.15
                },
                "goal_probability": {
                    "even_strength": 0.08,
                    "power_play": 0.15,
                    "short_handed": 0.03
                }
            }
        else:
            return {"default": {"continue": 1.0}}
    
    def get_transition_probs(self, state_type: str) -> Dict[str, float]:
        """Get transition probabilities for a state type."""
        return self._transitions.get(state_type, {"default": 1.0})

    def sample_transition(
        self,
        state_type: str,
        context: Optional[GameContext] = None
    ) -> str:
        """
        Sample a transition outcome based on probabilities.

        Args:
            state_type: Type of transition (e.g., "possession", "play_type")
            context: Optional GameContext for dynamic probability adjustments

        Returns:
            Sampled outcome string
        """
        probs = self.get_transition_probs(state_type)
        if not probs:
            return "default"

        # Apply clutch time adjustments if context is provided
        if context and context.is_clutch and state_type == "possession":
            probs = self._apply_clutch_adjustments(probs.copy())

        outcomes = list(probs.keys())
        weights = list(probs.values())

        if np is not None:
            return np.random.choice(outcomes, p=weights)

        r = random.random()
        cumulative = 0.0
        for outcome, weight in zip(outcomes, weights):
            cumulative += weight
            if r <= cumulative:
                return outcome
        return outcomes[-1]

    def _apply_clutch_adjustments(self, probs: Dict[str, float]) -> Dict[str, float]:
        """
        Apply clutch time adjustments to transition probabilities.

        In clutch time (< 2 min, within 5 points):
        - Pace slows down (more deliberate possessions)
        - Higher variance on shot outcomes (pressure effects)
        - More free throws (intentional fouling, playing for contact)

        Args:
            probs: Base transition probabilities

        Returns:
            Adjusted probabilities for clutch situations
        """
        if self.league != "NBA":
            return probs

        # Clutch time adjustments
        clutch_adj = {
            "two_point_make": 0.95,   # Slightly harder to score under pressure
            "two_point_miss": 1.05,   # More misses due to pressure
            "three_point_make": 0.90,  # Three-pointers harder in clutch
            "three_point_miss": 1.10,  # More misses
            "free_throws": 1.40,       # More intentional fouling, playing for contact
            "turnover": 1.15,          # More turnovers under pressure
        }

        adjusted = {}
        for outcome, base_prob in probs.items():
            adj_factor = clutch_adj.get(outcome, 1.0)
            adjusted[outcome] = base_prob * adj_factor

        # Normalize to sum to 1.0
        total = sum(adjusted.values())
        return {k: v / total for k, v in adjusted.items()}


class MarkovSimulator:
    """
    Play-by-play Markov chain simulator for player prop projections.
    
    Simulates games at the play level, tracking player involvement
    and stat accumulation throughout.
    """
    
    def __init__(
        self, 
        league: str, 
        players: List[Dict[str, Any]],
        home_context: Optional[Any] = None,
        away_context: Optional[Any] = None
    ):
        """
        Initialize the simulator.
        
        Args:
            league: League identifier
            players: List of player dicts with stats and usage rates
            home_context: Optional TeamContext with home team ratings/pace
            away_context: Optional TeamContext with away team ratings/pace
        """
        self.league = league.upper()
        self.players = players
        self.home_context = home_context
        self.away_context = away_context
        self.transition_matrix = TransitionMatrix(league)
        self._player_lookup = {p.get("name", p.get("player_name", "")): p for p in players}
        
        self._base_n_possessions = self._calculate_base_possessions()
    
    def _get_active_players(self, team: str) -> List[Dict[str, Any]]:
        """Get active players for a team."""
        return [p for p in self.players if p.get("team") == team]
    
    def _calculate_base_possessions(self) -> int:
        """Calculate base number of possessions based on team pace with calibration."""
        possession_adj = get_tuned_parameter("markov_possession_adjustment_factor", 1.0)
        
        if self.league == "NBA":
            if self.home_context and self.away_context:
                home_pace = getattr(self.home_context, 'pace', None) or self.home_context.get('pace', 100.0) if isinstance(self.home_context, dict) else getattr(self.home_context, 'pace', 100.0)
                away_pace = getattr(self.away_context, 'pace', None) or self.away_context.get('pace', 100.0) if isinstance(self.away_context, dict) else getattr(self.away_context, 'pace', 100.0)
                avg_pace = (home_pace + away_pace) / 2
                return int(avg_pace * 2 * possession_adj)
            return int(200 * possession_adj)
        elif self.league == "NFL":
            return int(150 * possession_adj)
        return int(200 * possession_adj)
    
    def _get_context_value(self, context: Any, key: str, default: float) -> float:
        """Safely get a value from a context (dict or dataclass)."""
        if context is None:
            return default
        if isinstance(context, dict):
            return context.get(key, default)
        return getattr(context, key, default)
    
    def _adjust_transition_probs(
        self,
        offense_context: Any,
        defense_context: Any,
        game_context: Optional[GameContext] = None
    ) -> Dict[str, float]:
        """
        Adjust transition probabilities based on team offensive/defensive ratings
        and game context (clutch time, garbage time, etc.).

        Higher off_rating -> higher shot make percentages (scale 0.35 base by off_rating/110)
        Higher def_rating -> lower opponent shot percentages

        CLUTCH TIME LOGIC (< 2 min, within 5 points):
        - Pace decreases (longer possessions, more deliberate)
        - Star player usage increases 1.5x (they take the last shots)
        - Shot variance increases (choking vs. clutch performances)
        - More free throw attempts (intentional fouling, playing for contact)

        Args:
            offense_context: Offensive team's TeamContext
            defense_context: Defensive team's TeamContext
            game_context: Optional GameContext with time/score information

        Returns:
            Adjusted possession transition probabilities
        """
        base_probs = self.transition_matrix.get_transition_probs("possession").copy()

        if self.league != "NBA":
            return base_probs

        off_rating = self._get_context_value(offense_context, 'off_rating', 110.0)
        def_rating = self._get_context_value(defense_context, 'def_rating', 110.0)
        fg_pct = self._get_context_value(offense_context, 'fg_pct', 0.45)
        three_pt_pct = self._get_context_value(offense_context, 'three_pt_pct', 0.35)

        off_multiplier = off_rating / 110.0
        def_multiplier = 110.0 / max(def_rating, 90.0)
        combined_multiplier = (off_multiplier + def_multiplier) / 2

        base_two_make = base_probs.get("two_point_make", 0.35)
        base_three_make = base_probs.get("three_point_make", 0.12)

        adj_two_make = min(0.50, base_two_make * combined_multiplier * (fg_pct / 0.45))
        adj_three_make = min(0.20, base_three_make * combined_multiplier * (three_pt_pct / 0.35))

        adj_two_miss = max(0.10, base_probs.get("two_point_miss", 0.20) / combined_multiplier)
        adj_three_miss = max(0.10, base_probs.get("three_point_miss", 0.18) / combined_multiplier)

        adjusted = {
            "two_point_make": adj_two_make,
            "two_point_miss": adj_two_miss,
            "three_point_make": adj_three_make,
            "three_point_miss": adj_three_miss,
            "free_throws": base_probs.get("free_throws", 0.08),
            "turnover": base_probs.get("turnover", 0.07)
        }

        # Apply CLUTCH TIME adjustments
        if game_context and game_context.is_clutch:
            adjusted = self._apply_clutch_time_adjustments(adjusted, game_context)
            logger.debug(f"Clutch time engaged: time={game_context.time_remaining:.1f}m, diff={game_context.score_differential}")

        # Apply GARBAGE TIME adjustments (optional)
        if game_context and game_context.is_garbage_time:
            adjusted = self._apply_garbage_time_adjustments(adjusted)

        total = sum(adjusted.values())
        return {k: v / total for k, v in adjusted.items()}

    def _apply_clutch_time_adjustments(
        self,
        probs: Dict[str, float],
        context: GameContext
    ) -> Dict[str, float]:
        """
        Apply clutch time adjustments to transition probabilities.

        In clutch time (< 2 min, within 5 points):
        - Shot efficiency decreases slightly (pressure)
        - Three-point attempts decrease (more conservative)
        - Free throw rate increases (intentional fouling, driving to basket)
        - Turnover rate increases (tighter defense, pressure)
        - Variance increases (clutch vs. choke performances)

        Args:
            probs: Base adjusted probabilities
            context: Game context with time/score

        Returns:
            Clutch-adjusted probabilities
        """
        # Closer games have more pressure
        pressure_factor = 1.0 + (1.0 - abs(context.score_differential) / 5.0) * 0.2

        clutch_multipliers = {
            "two_point_make": 0.92 / pressure_factor,   # Harder under pressure
            "two_point_miss": 1.08 * pressure_factor,   # More misses
            "three_point_make": 0.85,                    # Teams go for safer shots
            "three_point_miss": 1.15,                    # More conservative
            "free_throws": 1.50,                         # Intentional fouls, driving
            "turnover": 1.20 * pressure_factor,          # Tighter defense
        }

        adjusted = {}
        for outcome, base_prob in probs.items():
            multiplier = clutch_multipliers.get(outcome, 1.0)
            adjusted[outcome] = base_prob * multiplier

        return adjusted

    def _apply_garbage_time_adjustments(self, probs: Dict[str, float]) -> Dict[str, float]:
        """
        Apply garbage time adjustments (blowout game, starters resting).

        In garbage time:
        - Less efficient shooting (bench players)
        - More turnovers (less experience)
        - More three-point attempts (running down clock)
        """
        garbage_multipliers = {
            "two_point_make": 0.85,
            "two_point_miss": 1.15,
            "three_point_make": 0.80,
            "three_point_miss": 1.20,
            "free_throws": 0.80,
            "turnover": 1.30,
        }

        return {k: v * garbage_multipliers.get(k, 1.0) for k, v in probs.items()}

    def _get_clutch_usage_multiplier(
        self,
        player: Dict[str, Any],
        context: GameContext
    ) -> float:
        """
        Get usage rate multiplier for a player in clutch time.

        Star players (high usage rate) get 1.5x multiplier in clutch.
        Role players get reduced usage.

        Args:
            player: Player dict with usage_rate
            context: Game context

        Returns:
            Usage rate multiplier (1.0 in normal time, 1.5 for stars in clutch)
        """
        if not context.is_clutch:
            return 1.0

        base_usage = player.get("usage_rate", 0.15)

        # Star threshold: top usage players (>25% usage rate)
        if base_usage >= 0.25:
            return 1.5  # Stars take over in clutch

        # Secondary players: slight increase
        elif base_usage >= 0.18:
            return 1.15

        # Role players: reduced touches in clutch
        else:
            return 0.70
    
    def _select_involved_player(
        self,
        players: List[Dict[str, Any]],
        stat_key: str,
        game_context: Optional[GameContext] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Select which player is involved in a play based on usage rates.

        In clutch time, star players get 1.5x usage boost.

        Args:
            players: List of player dicts
            stat_key: Stat being accumulated (pts, reb, ast, etc.)
            game_context: Optional game context for clutch adjustments

        Returns:
            Selected player dict or None
        """
        if not players:
            return None

        weights = []
        for p in players:
            if stat_key in ("pts", "ast"):
                base_weight = p.get("usage_rate", 0.15)
            elif stat_key in ("reb",):
                base_weight = p.get("rebound_rate", 0.10)
            elif stat_key in ("pass_yds", "rec_yds"):
                base_weight = p.get("target_share", 0.15)
            elif stat_key in ("rush_yds",):
                base_weight = p.get("carry_share", 0.15)
            else:
                base_weight = p.get("usage_rate", 0.15)

            # Apply clutch usage multiplier
            if game_context:
                clutch_mult = self._get_clutch_usage_multiplier(p, game_context)
                base_weight *= clutch_mult

            weights.append(max(0.01, base_weight))

        total = sum(weights)
        probs = [w / total for w in weights]

        if np is not None:
            idx = np.random.choice(len(players), p=probs)
            return players[idx]

        r = random.random()
        cumulative = 0.0
        for player, prob in zip(players, probs):
            cumulative += prob
            if r <= cumulative:
                return player
        return players[-1]
    
    def _sample_adjusted_transition(self, adj_probs: Dict[str, float]) -> str:
        """Sample from adjusted transition probabilities."""
        outcomes = list(adj_probs.keys())
        weights = list(adj_probs.values())
        
        if np is not None:
            return np.random.choice(outcomes, p=weights)
        
        r = random.random()
        cumulative = 0.0
        for outcome, weight in zip(outcomes, weights):
            cumulative += weight
            if r <= cumulative:
                return outcome
        return outcomes[-1]
    
    def _simulate_nba_possession(
        self,
        state: MarkovState,
        home_players: List,
        away_players: List
    ) -> MarkovState:
        """
        Simulate a single NBA possession with team-adjusted probabilities.

        Includes dynamic clutch time logic when game is close and time is running low.
        """
        offense = home_players if state.possession_team == "home" else away_players

        # Get game context for clutch/garbage time adjustments
        game_context = state.get_context()

        # Calculate average possession time based on game state
        # Normal: ~24 seconds (0.4 min), Clutch: ~35 seconds (0.58 min, running clock)
        if game_context.is_clutch:
            avg_possession_time = 0.58  # Slower pace in clutch
        else:
            avg_possession_time = 0.40  # Normal pace

        # Decrement time remaining
        possession_time = avg_possession_time * (0.8 + random.random() * 0.4)  # Variance
        state.time_remaining = max(0.0, state.time_remaining - possession_time)

        # Get adjusted transition probabilities with game context
        if self.home_context and self.away_context:
            if state.possession_team == "home":
                adj_probs = self._adjust_transition_probs(
                    self.home_context, self.away_context, game_context
                )
            else:
                adj_probs = self._adjust_transition_probs(
                    self.away_context, self.home_context, game_context
                )
            outcome = self._sample_adjusted_transition(adj_probs)
        else:
            outcome = self.transition_matrix.sample_transition("possession", game_context)

        if outcome in ("two_point_make", "three_point_make"):
            # Pass game context for clutch usage boost
            scorer = self._select_involved_player(offense, "pts", game_context)
            if scorer:
                points = 3 if outcome == "three_point_make" else 2
                player_name = scorer.get("name", scorer.get("player_name", ""))
                state.add_player_stat(player_name, "pts", points)

                if state.possession_team == "home":
                    state.home_score += points
                else:
                    state.away_score += points

                # Assists - less likely in clutch (more ISO plays)
                assist_prob = 0.20 if game_context.is_clutch else 0.25
                if random.random() < assist_prob:
                    assister = self._select_involved_player(offense, "ast", game_context)
                    if assister and assister != scorer:
                        state.add_player_stat(
                            assister.get("name", assister.get("player_name", "")), "ast", 1
                        )

        elif outcome == "free_throws":
            scorer = self._select_involved_player(offense, "pts", game_context)
            if scorer:
                # Clutch free throws: more pressure, slightly lower makes
                if game_context.is_clutch:
                    weights = [0.15, 0.25, 0.60]  # Worse in clutch
                else:
                    weights = [0.10, 0.20, 0.70]  # Normal FT shooting

                made = random.choices([0, 1, 2], weights=weights)[0]
                player_name = scorer.get("name", scorer.get("player_name", ""))
                state.add_player_stat(player_name, "pts", made)
                if state.possession_team == "home":
                    state.home_score += made
                else:
                    state.away_score += made

        if outcome in ("two_point_miss", "three_point_miss"):
            defense = away_players if state.possession_team == "home" else home_players
            rebounder = self._select_involved_player(defense, "reb", game_context)
            if rebounder:
                state.add_player_stat(
                    rebounder.get("name", rebounder.get("player_name", "")), "reb", 1
                )

        state.possession_team = "away" if state.possession_team == "home" else "home"
        return state
    
    def _simulate_nfl_play(self, state: MarkovState, home_players: List, away_players: List) -> MarkovState:
        """Simulate a single NFL play."""
        offense = home_players if state.possession_team == "home" else away_players
        
        play_type = self.transition_matrix.sample_transition("play_type")
        
        if play_type == "pass":
            result = self.transition_matrix.sample_transition("pass_result")
            if result == "complete":
                receiver = self._select_involved_player(offense, "rec_yds")
                if receiver:
                    yards = max(0, random.gauss(8, 6))
                    player_name = receiver.get("name", receiver.get("player_name", ""))
                    state.add_player_stat(player_name, "rec_yds", yards)
                    state.add_player_stat(player_name, "rec", 1)
                    state.field_position += yards
                    state.distance -= yards
        
        elif play_type == "rush":
            rusher = self._select_involved_player(offense, "rush_yds")
            if rusher:
                yards = max(-5, random.gauss(4, 3))
                player_name = rusher.get("name", rusher.get("player_name", ""))
                state.add_player_stat(player_name, "rush_yds", yards)
                state.field_position += yards
                state.distance -= yards
        
        state.down += 1
        if state.distance <= 0:
            state.down = 1
            state.distance = 10.0
        
        if state.field_position >= 100:
            if state.possession_team == "home":
                state.home_score += 7
            else:
                state.away_score += 7
            state.possession_team = "away" if state.possession_team == "home" else "home"
            state.field_position = 25.0
            state.down = 1
            state.distance = 10.0
        
        if state.down > 4:
            state.possession_team = "away" if state.possession_team == "home" else "home"
            state.field_position = 100 - state.field_position
            state.down = 1
            state.distance = 10.0
        
        return state
    
    def simulate_game(
        self,
        n_possessions: int = 200,
        seed: Optional[int] = None,
        use_time_based: bool = True
    ) -> MarkovState:
        """
        Simulate a full game and return final state with player stats.

        Supports two simulation modes:
        1. Possession-based (legacy): Fixed number of possessions
        2. Time-based (new): Simulates until time expires, with dynamic clutch logic

        Args:
            n_possessions: Number of possessions/plays to simulate (possession-based mode)
            seed: Random seed for reproducibility
            use_time_based: If True, simulate based on game time rather than fixed possessions

        Returns:
            MarkovState with accumulated player statistics
        """
        if seed is not None:
            random.seed(seed)
            if np is not None:
                np.random.seed(seed)

        # Initialize game time based on league
        if self.league == "NBA":
            initial_time = 48.0  # 48 minutes
        elif self.league == "NFL":
            initial_time = 60.0  # 60 minutes
        elif self.league == "NHL":
            initial_time = 60.0  # 60 minutes
        elif self.league == "NCAAB":
            initial_time = 40.0  # 40 minutes
        else:
            initial_time = 48.0

        state = MarkovState(league=self.league, time_remaining=initial_time)

        # Separate home and away players
        home_players = [
            p for p in self.players
            if p.get("team_side") == "home" or p.get("is_home", False)
        ]
        away_players = [
            p for p in self.players
            if p.get("team_side") == "away" or p.get("is_home", False) is False
        ]

        if not home_players:
            home_players = self.players[:len(self.players)//2]
        if not away_players:
            away_players = self.players[len(self.players)//2:]

        if use_time_based:
            # TIME-BASED SIMULATION: Run until clock expires
            # This enables dynamic clutch logic as time winds down
            possession_count = 0
            max_possessions = 300  # Safety limit

            while state.time_remaining > 0 and possession_count < max_possessions:
                if self.league == "NBA" or self.league == "NCAAB":
                    state = self._simulate_nba_possession(state, home_players, away_players)
                elif self.league == "NFL":
                    state = self._simulate_nfl_play(state, home_players, away_players)
                else:
                    state = self._simulate_nba_possession(state, home_players, away_players)

                possession_count += 1

                # Log clutch time events
                context = state.get_context()
                if context.is_clutch and possession_count % 5 == 0:
                    logger.debug(
                        f"Clutch: {state.time_remaining:.1f}m left, "
                        f"Score {state.home_score:.0f}-{state.away_score:.0f}"
                    )
        else:
            # POSSESSION-BASED SIMULATION (legacy mode)
            for _ in range(n_possessions):
                if self.league == "NBA" or self.league == "NCAAB":
                    state = self._simulate_nba_possession(state, home_players, away_players)
                elif self.league == "NFL":
                    state = self._simulate_nfl_play(state, home_players, away_players)
                else:
                    state = self._simulate_nba_possession(state, home_players, away_players)

        return state
    
    def run_simulation(
        self,
        n_iter: int = 10000,
        n_possessions: int = 200,
        seed: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Run multiple game simulations and return player stat distributions.
        
        Args:
            n_iter: Number of simulation iterations
            n_possessions: Possessions per game
            seed: Random seed
        
        Returns:
            Dict with player stat distributions
        """
        if seed is not None:
            random.seed(seed)
            if np is not None:
                np.random.seed(seed)
        
        all_player_stats: Dict[str, Dict[str, List[float]]] = {}
        
        for _ in range(n_iter):
            game_state = self.simulate_game(n_possessions)
            
            for player_name, stats in game_state.player_stats.items():
                if player_name not in all_player_stats:
                    all_player_stats[player_name] = {}
                for stat_key, value in stats.items():
                    if stat_key not in all_player_stats[player_name]:
                        all_player_stats[player_name][stat_key] = []
                    all_player_stats[player_name][stat_key].append(value)
        
        results = {}
        for player_name, stats in all_player_stats.items():
            results[player_name] = {}
            for stat_key, values in stats.items():
                mean_val = sum(values) / len(values) if values else 0
                std_val = (sum((v - mean_val) ** 2 for v in values) / len(values)) ** 0.5 if len(values) > 1 else 0
                results[player_name][stat_key] = {
                    "mean": mean_val,
                    "std": std_val,
                    "min": min(values) if values else 0,
                    "max": max(values) if values else 0,
                    "samples": values[:20]
                }
        
        return results


def run_markov_player_prop_simulation(
    player: Dict[str, Any],
    teammates: List[Dict[str, Any]],
    opponents: List[Dict[str, Any]],
    stat_key: str,
    market_line: float,
    league: str = "NBA",
    n_iter: int = 10000,
    seed: Optional[int] = None
) -> Dict[str, Any]:
    """
    Run Markov simulation for a player prop bet.
    
    Args:
        player: Player dict with usage rates and stats
        teammates: List of teammate dicts
        opponents: List of opponent dicts
        stat_key: Stat to simulate (e.g., "pts", "reb", "rec_yds")
        market_line: The betting line for the prop
        league: League identifier
        n_iter: Number of simulation iterations
        seed: Random seed
    
    Returns:
        Dict with over/under probabilities and stat distribution
    """
    all_players = []
    
    player_copy = dict(player)
    player_copy["team_side"] = "home"
    all_players.append(player_copy)
    
    for tm in teammates:
        tm_copy = dict(tm)
        tm_copy["team_side"] = "home"
        all_players.append(tm_copy)
    
    for opp in opponents:
        opp_copy = dict(opp)
        opp_copy["team_side"] = "away"
        all_players.append(opp_copy)
    
    simulator = MarkovSimulator(league, all_players)
    
    n_possessions = 200 if league in ("NBA", "NCAAB") else 150
    
    results = simulator.run_simulation(n_iter, n_possessions, seed)
    
    player_name = player.get("name", player.get("player_name", ""))
    player_results = results.get(player_name, {}).get(stat_key, {})
    
    samples = player_results.get("samples", [])
    all_samples = []
    
    if samples:
        for _ in range(n_iter):
            game_state = simulator.simulate_game(n_possessions)
            stat_val = game_state.get_player_stat(player_name, stat_key)
            all_samples.append(stat_val)
    
    if all_samples:
        over_count = sum(1 for s in all_samples if s > market_line)
        under_count = sum(1 for s in all_samples if s < market_line)
        push_count = sum(1 for s in all_samples if abs(s - market_line) < 0.5)
        
        return {
            "over_prob": over_count / len(all_samples),
            "under_prob": under_count / len(all_samples),
            "push_prob": push_count / len(all_samples),
            "mean": player_results.get("mean", 0),
            "std": player_results.get("std", 0),
            "min": player_results.get("min", 0),
            "max": player_results.get("max", 0),
            "market_line": market_line,
            "player_name": player_name,
            "stat_key": stat_key
        }
    
    return {
        "over_prob": 0.5,
        "under_prob": 0.5,
        "push_prob": 0.0,
        "mean": 0,
        "std": 0,
        "market_line": market_line,
        "player_name": player_name,
        "stat_key": stat_key,
        "error": "No samples generated"
    }
