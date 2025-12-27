# Core Abstractions Module

"""
Module Name: Core Abstractions
Version: 1.0.0
Description: League-agnostic core abstractions for Team, Player, Game, and State objects.
Functions:
    - Team class: Represents a team with ratings and stats
    - Player class: Represents a player with stats and usage
    - Game class: Represents a game matchup
    - State class: Generic game state (base class for league-specific states)
Usage Notes:
    - These are base classes; league-specific subclasses extend them
    - Designed for league-agnostic core layer
    - Used by projection and simulation modules
"""

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Optional, Any, List

@dataclass
class Team:
    """
    Represents a team with ratings, stats, and metadata.
    League-agnostic base class.
    """
    name: str
    league: str
    off_rating: float = 0.0
    def_rating: float = 0.0
    pace: float = 0.0
    stats: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def net_rating(self) -> float:
        """Returns offensive rating minus defensive rating."""
        return self.off_rating - self.def_rating
    
    def get_stat(self, stat_key: str, default: float = 0.0) -> float:
        """Gets a stat value, returning default if not found."""
        return self.stats.get(stat_key, default)
    
    def set_stat(self, stat_key: str, value: float) -> None:
        """Sets a stat value."""
        self.stats[stat_key] = value

@dataclass
class Player:
    """
    Represents a player with stats, usage, and metadata.
    League-agnostic base class.
    """
    name: str
    team: str
    league: str
    position: Optional[str] = None
    usage_rate: float = 0.0
    stats: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_stat(self, stat_key: str, default: float = 0.0) -> float:
        """Gets a stat value, returning default if not found."""
        return self.stats.get(stat_key, default)
    
    def set_stat(self, stat_key: str, value: float) -> None:
        """Sets a stat value."""
        self.stats[stat_key] = value

@dataclass
class Game:
    """
    Represents a game matchup between two teams.
    League-agnostic base class.
    """
    game_id: str
    league: str
    home_team: Team
    away_team: Team
    date: Optional[str] = None
    venue: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_team(self, team_name: str) -> Optional[Team]:
        """Gets team by name (home or away)."""
        if self.home_team.name == team_name:
            return self.home_team
        if self.away_team.name == team_name:
            return self.away_team
        return None

@dataclass
class State:
    """
    Generic game state representation.
    Base class for league-specific state objects (Possession, Drive, Inning, Shift).
    """
    league: str
    period: int = 1
    time_remaining: float = 0.0
    score: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_score(self, team_name: str, default: float = 0.0) -> float:
        """Gets score for a team."""
        return self.score.get(team_name, default)
    
    def set_score(self, team_name: str, value: float) -> None:
        """Sets score for a team."""
        self.score[team_name] = value

# League-specific state subclasses (examples)

@dataclass
class Possession(State):
    """
    NBA/NBA-style possession state.
    """
    team_with_ball: Optional[str] = None
    field_position: Optional[float] = None  # For NBA: 0-100 court position
    shot_clock: Optional[float] = None

@dataclass
class Drive(State):
    """
    NFL/NCAAF-style drive state.
    """
    team_with_ball: Optional[str] = None
    field_position: float = 0.0  # Yard line (0-100)
    down: int = 1
    distance: float = 10.0
    time_remaining: float = 0.0

@dataclass
class Inning(State):
    """
    MLB-style inning state.
    """
    inning: int = 1
    half: str = "top"  # "top" or "bottom"
    outs: int = 0
    bases: Dict[str, bool] = field(default_factory=lambda: {"first": False, "second": False, "third": False})
    runs_this_inning: float = 0.0

@dataclass
class Shift(State):
    """
    NHL-style shift/possession state.
    """
    team_with_puck: Optional[str] = None
    zone: str = "neutral"  # "offensive", "neutral", "defensive"
    power_play: bool = False
    shots_this_shift: int = 0

# Helper functions for creating objects from dicts

def team_from_dict(data: Dict[str, Any]) -> Team:
    """Creates a Team object from a dictionary."""
    return Team(
        name=data.get("name", ""),
        league=data.get("league", ""),
        off_rating=data.get("off_rating", 0.0),
        def_rating=data.get("def_rating", 0.0),
        pace=data.get("pace", 0.0),
        stats=data.get("stats", {}),
        metadata=data.get("metadata", {})
    )

def player_from_dict(data: Dict[str, Any]) -> Player:
    """Creates a Player object from a dictionary."""
    return Player(
        name=data.get("name", ""),
        team=data.get("team", ""),
        league=data.get("league", ""),
        position=data.get("position"),
        usage_rate=data.get("usage_rate", 0.0),
        stats=data.get("stats", {}),
        metadata=data.get("metadata", {})
    )

def game_from_dict(data: Dict[str, Any], home_team: Team, away_team: Team) -> Game:
    """Creates a Game object from a dictionary and Team objects."""
    return Game(
        game_id=data.get("game_id", ""),
        league=data.get("league", ""),
        home_team=home_team,
        away_team=away_team,
        date=data.get("date"),
        venue=data.get("venue"),
        context=data.get("context", {}),
        metadata=data.get("metadata", {})
    )

```

