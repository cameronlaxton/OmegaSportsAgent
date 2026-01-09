"""
Universal Sports Schema for OmegaSports Headless Engine

Defines strict Pydantic models for sports data validation.
This ensures all data (odds, spreads, props) follows a consistent format
before entering the simulation engine.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class Sport(str, Enum):
    NBA = "NBA"
    NFL = "NFL"
    MLB = "MLB"
    NHL = "NHL"
    NCAAB = "NCAAB"
    NCAAF = "NCAAF"
    SOCCER = "SOCCER"


class BettingLine(BaseModel):
    """Represents a single betting line from a sportsbook."""
    sportsbook: str = Field(description="Name of the sportsbook (e.g., 'DraftKings', 'FanDuel')")
    price: float = Field(description="American odds (e.g., -110) or decimal odds (e.g., 1.91)")
    value: Optional[float] = Field(default=None, description="The spread value (e.g., -7.5) or total (e.g., 220.5)")
    
    def is_decimal_odds(self) -> bool:
        """Detect if price is in decimal format (typically 1.01 to ~20.0)."""
        return 1.0 < self.price < 20.0
    
    def implied_probability(self) -> float:
        """
        Calculate implied probability from odds.
        Automatically detects American vs decimal odds format.
        """
        if self.is_decimal_odds():
            return 1 / self.price
        elif self.price >= 100:
            return 100 / (self.price + 100)
        else:
            return abs(self.price) / (abs(self.price) + 100)


class PropBet(BaseModel):
    """Represents a player prop bet."""
    player_name: str = Field(description="Full name of the player")
    team: Optional[str] = Field(default=None, description="Team the player belongs to")
    prop_type: str = Field(description="Type of prop (e.g., 'Points', 'Rebounds', 'Passing Yards')")
    line: float = Field(description="The prop line value (e.g., 25.5 for points)")
    over_price: float = Field(description="Odds for over (American: -110, or decimal: 1.91)")
    under_price: float = Field(description="Odds for under (American: -110, or decimal: 1.91)")
    
    @staticmethod
    def _calc_implied_prob(price: float) -> float:
        """Calculate implied probability from American or decimal odds."""
        if 1.0 < price < 20.0:
            return 1 / price
        elif price >= 100:
            return 100 / (price + 100)
        else:
            return abs(price) / (abs(price) + 100)
    
    def over_implied_prob(self) -> float:
        """Calculate implied probability for over."""
        return self._calc_implied_prob(self.over_price)
    
    def under_implied_prob(self) -> float:
        """Calculate implied probability for under."""
        return self._calc_implied_prob(self.under_price)


class TeamData(BaseModel):
    """Team statistics and context."""
    name: str
    abbreviation: Optional[str] = None
    record: Optional[str] = Field(default=None, description="Win-Loss record (e.g., '22-10')")
    rank: Optional[int] = None
    injuries: List[str] = Field(default_factory=list, description="List of injured players")
    extra_data: Dict[str, Any] = Field(default_factory=dict)


class GameData(BaseModel):
    """
    Universal game data structure for all sports.
    
    This is the primary data format that must be used when feeding
    data into the OmegaSports simulation engine.
    """
    sport: str = Field(description="Sport identifier (NBA, NFL, MLB, etc.)")
    league: str = Field(description="League identifier")
    game_id: Optional[str] = Field(default=None, description="Unique game identifier")
    timestamp: datetime = Field(default_factory=datetime.now, description="When this data was captured")
    game_time: Optional[datetime] = Field(default=None, description="Scheduled game start time")
    
    home_team: str = Field(description="Home team name")
    away_team: str = Field(description="Away team name")
    home_team_data: Optional[TeamData] = None
    away_team_data: Optional[TeamData] = None
    
    moneyline: Optional[Dict[str, BettingLine]] = Field(
        default=None, 
        description="Moneyline odds - {'home': BettingLine, 'away': BettingLine}"
    )
    spread: Optional[Dict[str, BettingLine]] = Field(
        default=None,
        description="Spread odds - {'home': BettingLine, 'away': BettingLine}"
    )
    total: Optional[Dict[str, BettingLine]] = Field(
        default=None,
        description="Over/Under totals - {'over': BettingLine, 'under': BettingLine}"
    )
    
    player_props: List[PropBet] = Field(default_factory=list, description="List of player prop bets")
    
    raw_markdown_source: Optional[str] = Field(
        default=None,
        description="Original markdown content for verification"
    )
    source_url: Optional[str] = Field(default=None, description="URL where data was scraped from")
    extra_data: Dict[str, Any] = Field(default_factory=dict, description="Additional sport-specific data")
    
    def get_home_ml_odds(self) -> Optional[float]:
        """Get home team moneyline odds."""
        if self.moneyline and "home" in self.moneyline:
            return self.moneyline["home"].price
        return None
    
    def get_away_ml_odds(self) -> Optional[float]:
        """Get away team moneyline odds."""
        if self.moneyline and "away" in self.moneyline:
            return self.moneyline["away"].price
        return None
    
    def get_spread_value(self) -> Optional[float]:
        """Get the spread value (from home team perspective)."""
        if self.spread and "home" in self.spread:
            return self.spread["home"].value
        return None
    
    def get_total_value(self) -> Optional[float]:
        """Get the over/under total value."""
        if self.total and "over" in self.total:
            return self.total["over"].value
        return None


class SimulationInput(BaseModel):
    """Input structure for running simulations."""
    game: GameData
    n_iterations: int = Field(default=10000, ge=1000, le=100000)
    include_props: bool = Field(default=True)
    confidence_threshold: float = Field(default=0.05, ge=0.0, le=0.5)


class BetRecommendation(BaseModel):
    """Output structure for bet recommendations."""
    game_id: Optional[str] = None
    matchup: str
    pick: str
    bet_type: str = Field(description="Type: 'ml', 'spread', 'total', 'prop'")
    odds: int
    model_prob: float = Field(ge=0.0, le=1.0)
    implied_prob: float = Field(ge=0.0, le=1.0)
    edge_pct: float
    ev_pct: float
    confidence_tier: str = Field(description="Tier: 'A', 'B', 'C', or 'Pass'")
    recommended_units: float = Field(ge=0.0)
    factors: List[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.now)


class DailySlate(BaseModel):
    """Collection of games for a single day."""
    date: str = Field(description="Date in YYYY-MM-DD format")
    sport: str
    games: List[GameData] = Field(default_factory=list)
    recommendations: List[BetRecommendation] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.now)
    
    def to_simulation_inputs(self, n_iterations: int = 10000) -> List[SimulationInput]:
        """Convert slate to simulation inputs."""
        return [
            SimulationInput(game=game, n_iterations=n_iterations)
            for game in self.games
        ]
