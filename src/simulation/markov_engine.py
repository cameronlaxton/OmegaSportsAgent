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


def validate_player_context(
    context: Any,
    league: str = "NBA",
    prop_stat_key: Optional[str] = None,
) -> Tuple[bool, List[str]]:
    """
    Check if player has required stats for simulation, aware of sport archetype.

    Validation rules per archetype:
      basketball (NBA/NCAAB/WNBA/FIBA): pts_mean > 0
      american_football (NFL/NCAAF): at least one of pass_yards, rush_yards, receiving_yards > 0
      baseball (MLB): batting_avg or at_bats present
      hockey (NHL): goals, shots, or toi present
      soccer: goals_mean or shots_mean or minutes_mean present
      tennis: serve_win_pct present
      golf: strokes_gained_total or scoring_avg present
      fighting (UFC/Boxing): win_pct or finish_rate present
      esports: kills_mean or kd_ratio or rating present
      unknown: pass (don't block)

    Args:
        context: PlayerContext object or dict with player stats
        league: League code for archetype dispatch
        prop_stat_key: Optional specific stat key being validated

    Returns:
        Tuple of (is_valid, list of issues)
    """
    issues = []

    if context is None:
        issues.append("No player context provided")
        return False, issues

    def _get(key: str, default=0):
        if isinstance(context, dict):
            return context.get(key, default)
        return getattr(context, key, default)

    player_name = _get("name", "Unknown")
    league_upper = league.upper()

    # Import archetype mapping
    try:
        from src.simulation.sport_archetypes import get_archetype_name
        archetype = get_archetype_name(league_upper)
    except ImportError:
        archetype = None

    if archetype == "basketball":
        pts_mean = _get("pts_mean", 0)
        if pts_mean is None or pts_mean <= 0:
            issues.append("Missing points average (pts_mean)")

    elif archetype == "american_football":
        pass_yds = _get("pass_yards", _get("pass_yards_mean", 0))
        rush_yds = _get("rush_yards", _get("rush_yards_mean", 0))
        rec_yds = _get("receiving_yards", _get("rec_yards_mean", 0))
        if not any(v and v > 0 for v in [pass_yds, rush_yds, rec_yds]):
            issues.append("Missing football stats (need pass_yards, rush_yards, or receiving_yards > 0)")

    elif archetype == "baseball":
        ba = _get("batting_avg", 0)
        ab = _get("at_bats", 0)
        era = _get("era", 0)
        role = _get("role", "")
        if role == "pitcher":
            if not (era and era > 0):
                issues.append("Missing pitcher stats (need era > 0)")
        else:
            if not any(v and v > 0 for v in [ba, ab]):
                issues.append("Missing batter stats (need batting_avg or at_bats > 0)")

    elif archetype == "hockey":
        goals = _get("goals_mean", _get("goals", 0))
        shots = _get("shots_mean", _get("shots", 0))
        toi = _get("toi", _get("toi_share", 0))
        saves = _get("saves_mean", 0)
        if not any(v and v > 0 for v in [goals, shots, toi, saves]):
            issues.append("Missing hockey stats (need goals, shots, toi, or saves > 0)")

    elif archetype == "soccer":
        goals = _get("goals_mean", 0)
        shots = _get("shots_mean", 0)
        mins = _get("minutes_mean", 0)
        if not any(v and v > 0 for v in [goals, shots, mins]):
            issues.append("Missing soccer stats (need goals_mean, shots_mean, or minutes_mean > 0)")

    elif archetype == "tennis":
        serve_pct = _get("serve_win_pct", 0)
        elo = _get("elo_rating", 0)
        if not any(v and v > 0 for v in [serve_pct, elo]):
            issues.append("Missing tennis stats (need serve_win_pct or elo_rating > 0)")

    elif archetype == "golf":
        sg = _get("strokes_gained_total", 0)
        avg = _get("scoring_avg", 0)
        if not any(v and v != 0 for v in [sg, avg]):  # SG can be negative
            issues.append("Missing golf stats (need strokes_gained_total or scoring_avg)")

    elif archetype == "fighting":
        win_pct = _get("win_pct", 0)
        finish = _get("finish_rate", 0)
        elo = _get("elo_rating", 0)
        if not any(v and v > 0 for v in [win_pct, finish, elo]):
            issues.append("Missing fighting stats (need win_pct, finish_rate, or elo_rating > 0)")

    elif archetype == "esports":
        kills = _get("kills_mean", 0)
        kd = _get("kd_ratio", 0)
        rating = _get("rating", 0)
        if not any(v and v > 0 for v in [kills, kd, rating]):
            issues.append("Missing esports stats (need kills_mean, kd_ratio, or rating > 0)")

    else:
        # Unknown archetype: pass validation (don't block)
        pass

    is_valid = len(issues) == 0

    if not is_valid:
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "player_validation_failure",
            "entity": player_name,
            "entity_type": "player",
            "league": league_upper,
            "archetype": archetype,
            "issues": issues,
        }
        _log_validation_to_integrity_file(entry)
        logger.warning(f"Player validation failed for {player_name} ({league_upper}): {', '.join(issues)}")

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
class MarkovState:
    """Represents a state in the Markov chain simulation."""
    league: str
    period: int = 1
    time_remaining: float = 0.0
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
    
    def sample_transition(self, state_type: str) -> str:
        """Sample a transition outcome based on probabilities."""
        probs = self.get_transition_probs(state_type)
        if not probs:
            return "default"
        
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
        """Calculate base number of possessions/opportunities based on sport archetype."""
        possession_adj = get_tuned_parameter("markov_possession_adjustment_factor", 1.0)

        try:
            from src.simulation.sport_archetypes import get_archetype_name
            archetype = get_archetype_name(self.league)
        except ImportError:
            archetype = None

        def _ctx_pace(ctx, default):
            if ctx is None:
                return default
            if isinstance(ctx, dict):
                return ctx.get("pace", default)
            return getattr(ctx, "pace", default)

        if archetype == "basketball":
            from src.foundation.league_config import get_league_config
            cfg = get_league_config(self.league)
            default_pace = cfg.get("avg_pace", 100.0)
            home_pace = _ctx_pace(self.home_context, default_pace)
            away_pace = _ctx_pace(self.away_context, default_pace)
            avg_pace = (home_pace + away_pace) / 2
            return int(avg_pace * 2 * possession_adj)

        elif archetype == "american_football":
            return int(150 * possession_adj)

        elif archetype == "baseball":
            # ~38 plate appearances per team per game × 2 = ~76 per side
            return int(152 * possession_adj)

        elif archetype == "hockey":
            # ~60 shifts per team → ~120 total
            return int(120 * possession_adj)

        elif archetype == "soccer":
            # ~50 meaningful possessions per side × 2
            return int(100 * possession_adj)

        elif archetype == "tennis":
            # ~180 points in a best-of-3 match
            return int(180 * possession_adj)

        elif archetype == "golf":
            # 72 holes per tournament (4 rounds × 18)
            return int(72 * possession_adj)

        elif archetype == "fighting":
            # ~50 significant strike exchanges per round × 3 rounds
            return int(150 * possession_adj)

        elif archetype == "esports":
            # ~25 rounds per map × 3 maps
            return int(75 * possession_adj)

        # Fallback
        return int(200 * possession_adj)
    
    def _get_context_value(self, context: Any, key: str, default: float) -> float:
        """Safely get a value from a context (dict or dataclass)."""
        if context is None:
            return default
        if isinstance(context, dict):
            return context.get(key, default)
        return getattr(context, key, default)
    
    def _adjust_transition_probs(self, offense_context: Any, defense_context: Any) -> Dict[str, float]:
        """
        Adjust transition probabilities based on team offensive/defensive ratings.
        Dispatches to sport-specific adjustment logic.

        Returns:
            Adjusted transition probabilities dict
        """
        base_probs = self.transition_matrix.get_transition_probs("possession").copy()

        try:
            from src.simulation.sport_archetypes import get_archetype_name
            archetype = get_archetype_name(self.league)
        except ImportError:
            archetype = None

        if archetype == "basketball":
            return self._adjust_basketball(base_probs, offense_context, defense_context)
        elif archetype == "american_football":
            return self._adjust_football(base_probs, offense_context, defense_context)
        elif archetype == "baseball":
            return self._adjust_baseball(base_probs, offense_context, defense_context)
        elif archetype == "hockey":
            return self._adjust_hockey(base_probs, offense_context, defense_context)
        elif archetype == "soccer":
            return self._adjust_soccer(base_probs, offense_context, defense_context)

        # Tennis, golf, fighting, esports: Markov play-by-play not primary model
        return base_probs

    def _adjust_basketball(self, base_probs, off_ctx, def_ctx):
        """Basketball-specific transition adjustments."""
        off_rating = self._get_context_value(off_ctx, 'off_rating', 110.0)
        def_rating = self._get_context_value(def_ctx, 'def_rating', 110.0)
        fg_pct = self._get_context_value(off_ctx, 'fg_pct', 0.45)
        three_pt_pct = self._get_context_value(off_ctx, 'three_pt_pct', 0.35)

        off_mult = off_rating / 110.0
        def_mult = 110.0 / max(def_rating, 90.0)
        combined = (off_mult + def_mult) / 2

        adj = {
            "two_point_make": min(0.50, base_probs.get("two_point_make", 0.35) * combined * (fg_pct / 0.45)),
            "two_point_miss": max(0.10, base_probs.get("two_point_miss", 0.20) / combined),
            "three_point_make": min(0.20, base_probs.get("three_point_make", 0.12) * combined * (three_pt_pct / 0.35)),
            "three_point_miss": max(0.10, base_probs.get("three_point_miss", 0.18) / combined),
            "free_throws": base_probs.get("free_throws", 0.08),
            "turnover": base_probs.get("turnover", 0.07),
        }
        total = sum(adj.values())
        return {k: v / total for k, v in adj.items()}

    def _adjust_football(self, base_probs, off_ctx, def_ctx):
        """American football transition adjustments."""
        ppg = self._get_context_value(off_ctx, 'off_rating', 22.5)
        papg = self._get_context_value(def_ctx, 'def_rating', 22.5)

        # Scale scoring transitions by PPG relative to league average ~22.5
        scoring_mult = ppg / 22.5
        defense_mult = 22.5 / max(papg, 10.0)
        combined = (scoring_mult + defense_mult) / 2

        adj = {}
        for k, v in base_probs.items():
            if "touchdown" in k or "field_goal" in k or "score" in k:
                adj[k] = v * combined
            elif "turnover" in k or "punt" in k:
                adj[k] = v / combined
            else:
                adj[k] = v

        total = sum(adj.values())
        return {k: v / total for k, v in adj.items()} if total > 0 else base_probs

    def _adjust_baseball(self, base_probs, off_ctx, def_ctx):
        """Baseball transition adjustments."""
        ba = self._get_context_value(off_ctx, 'batting_avg', 0.250)
        opp_era = self._get_context_value(def_ctx, 'era', 4.00)

        # Hit probability scaled by batting avg relative to league .250
        hit_mult = ba / 0.250 if ba > 0 else 1.0
        # Pitcher quality: lower ERA = fewer hits
        pitcher_mult = 4.00 / max(opp_era, 1.0)

        adj = {}
        for k, v in base_probs.items():
            if "hit" in k or "single" in k or "double" in k or "triple" in k or "home_run" in k:
                adj[k] = v * hit_mult * pitcher_mult
            elif "strikeout" in k:
                adj[k] = v / hit_mult
            else:
                adj[k] = v

        total = sum(adj.values())
        return {k: v / total for k, v in adj.items()} if total > 0 else base_probs

    def _adjust_hockey(self, base_probs, off_ctx, def_ctx):
        """Hockey transition adjustments."""
        shots_pg = self._get_context_value(off_ctx, 'shots_per_game', 30.0)
        opp_sv_pct = self._get_context_value(def_ctx, 'goalie_sv_pct', 0.905)

        shot_mult = shots_pg / 30.0
        # Lower save % = more goals
        goal_mult = (1 - 0.905) / max(1 - opp_sv_pct, 0.01)

        adj = {}
        for k, v in base_probs.items():
            if "shot_on_goal" in k or "shot" in k:
                adj[k] = v * shot_mult
            elif "goal" in k:
                adj[k] = v * shot_mult * goal_mult
            else:
                adj[k] = v

        total = sum(adj.values())
        return {k: v / total for k, v in adj.items()} if total > 0 else base_probs

    def _adjust_soccer(self, base_probs, off_ctx, def_ctx):
        """Soccer transition adjustments."""
        xg = self._get_context_value(off_ctx, 'xg_for', 1.25)
        xga = self._get_context_value(def_ctx, 'xg_against', 1.25)

        attack_mult = xg / 1.25 if xg > 0 else 1.0
        defense_mult = 1.25 / max(xga, 0.3)

        adj = {}
        for k, v in base_probs.items():
            if "goal" in k or "shot" in k:
                adj[k] = v * attack_mult * defense_mult
            else:
                adj[k] = v

        total = sum(adj.values())
        return {k: v / total for k, v in adj.items()} if total > 0 else base_probs
    
    def _select_involved_player(self, players: List[Dict[str, Any]], stat_key: str) -> Optional[Dict[str, Any]]:
        """Select which player is involved in a play based on usage/role weights.

        Weight keys by sport archetype:
          basketball: pts/ast → usage_rate, reb → rebound_rate
          american_football: pass_yds/rec_yds → target_share, rush_yds → carry_share
          baseball: hits/runs/rbis → pa_share or batting_avg, strikeouts → k_rate
          hockey: goals/assists/shots → toi_share, saves → 1.0 (goalie only)
          soccer: goals/assists/shots → minutes_mean
          tennis/golf/fighting/esports: equal weighting (individual sports)
        """
        if not players:
            return None

        # Stat key → (weight_key, default_weight) mapping
        _WEIGHT_MAP = {
            # Basketball
            "pts": ("usage_rate", 0.15),
            "ast": ("usage_rate", 0.15),
            "reb": ("rebound_rate", 0.10),
            "3pm": ("usage_rate", 0.15),
            "pra": ("usage_rate", 0.15),
            "stl": ("usage_rate", 0.10),
            "blk": ("rebound_rate", 0.10),
            # American Football
            "pass_yds": ("target_share", 0.15),
            "rec_yds": ("target_share", 0.15),
            "receptions": ("target_share", 0.15),
            "rush_yds": ("carry_share", 0.15),
            "pass_td": ("target_share", 0.15),
            "rush_td": ("carry_share", 0.15),
            "rec_td": ("target_share", 0.15),
            # Baseball
            "hits": ("pa_share", 0.11),
            "total_bases": ("pa_share", 0.11),
            "runs": ("pa_share", 0.11),
            "rbis": ("pa_share", 0.11),
            "hrs": ("pa_share", 0.11),
            "stolen_bases": ("pa_share", 0.11),
            "strikeouts_pitched": ("k_rate", 0.20),
            "outs_recorded": ("k_rate", 0.20),
            # Hockey
            "goals": ("toi_share", 0.10),
            "assists": ("toi_share", 0.10),
            "points": ("toi_share", 0.10),
            "shots_on_goal": ("toi_share", 0.10),
            "saves": ("saves_share", 1.0),
            # Soccer
            "shots": ("minutes_mean", 0.15),
            "shots_on_target": ("minutes_mean", 0.15),
            # Esports
            "kills": ("rating", 0.15),
            "deaths": ("rating", 0.15),
        }

        weight_key, default_w = _WEIGHT_MAP.get(stat_key, ("usage_rate", 0.15))

        weights = []
        for p in players:
            w = p.get(weight_key, default_w)
            # For "goals" in soccer, also check goals_mean
            if stat_key in ("goals", "assists") and weight_key == "toi_share":
                alt = p.get("goals_mean", p.get("goals_per_game", 0))
                if alt and alt > 0:
                    w = alt
            weights.append(max(0.01, w))

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
    
    def _simulate_nba_possession(self, state: MarkovState, home_players: List, away_players: List) -> MarkovState:
        """Simulate a single NBA possession with team-adjusted probabilities."""
        offense = home_players if state.possession_team == "home" else away_players
        
        if self.home_context and self.away_context:
            if state.possession_team == "home":
                adj_probs = self._adjust_transition_probs(self.home_context, self.away_context)
            else:
                adj_probs = self._adjust_transition_probs(self.away_context, self.home_context)
            outcome = self._sample_adjusted_transition(adj_probs)
        else:
            outcome = self.transition_matrix.sample_transition("possession")
        
        if outcome in ("two_point_make", "three_point_make"):
            scorer = self._select_involved_player(offense, "pts")
            if scorer:
                points = 3 if outcome == "three_point_make" else 2
                player_name = scorer.get("name", scorer.get("player_name", ""))
                state.add_player_stat(player_name, "pts", points)
                
                if state.possession_team == "home":
                    state.home_score += points
                else:
                    state.away_score += points
                
                if random.random() < 0.25:
                    assister = self._select_involved_player(offense, "ast")
                    if assister and assister != scorer:
                        state.add_player_stat(assister.get("name", assister.get("player_name", "")), "ast", 1)
        
        elif outcome == "free_throws":
            scorer = self._select_involved_player(offense, "pts")
            if scorer:
                made = random.choices([0, 1, 2], weights=[0.1, 0.2, 0.7])[0]
                player_name = scorer.get("name", scorer.get("player_name", ""))
                state.add_player_stat(player_name, "pts", made)
                if state.possession_team == "home":
                    state.home_score += made
                else:
                    state.away_score += made
        
        if outcome in ("two_point_miss", "three_point_miss"):
            defense = away_players if state.possession_team == "home" else home_players
            rebounder = self._select_involved_player(defense, "reb")
            if rebounder:
                state.add_player_stat(rebounder.get("name", rebounder.get("player_name", "")), "reb", 1)
        
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
    
    def simulate_game(self, n_possessions: int = 200, seed: Optional[int] = None) -> MarkovState:
        """
        Simulate a full game and return final state with player stats.
        
        Args:
            n_possessions: Number of possessions/plays to simulate
            seed: Random seed for reproducibility
        
        Returns:
            MarkovState with accumulated player statistics
        """
        if seed is not None:
            random.seed(seed)
            if np is not None:
                np.random.seed(seed)
        
        state = MarkovState(league=self.league)
        home_players = [p for p in self.players if p.get("team_side") == "home" or p.get("is_home", False)]
        away_players = [p for p in self.players if p.get("team_side") == "away" or p.get("is_home", False) is False]
        
        if not home_players:
            home_players = self.players[:len(self.players)//2]
        if not away_players:
            away_players = self.players[len(self.players)//2:]
        
        for _ in range(n_possessions):
            if self.league == "NBA":
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
