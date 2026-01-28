"""
OmegaSportsAgent Hybrid Schema (Relational + JSONB)

Architecture: Uses standard SQL columns for universal data (IDs, Names, Dates)
and JSONB for sport-specific stats to avoid sparse column bloat.

Reasoning: NBA players have rebounds, NFL players have passing_yards.
We use a "Box Score" JSON approach instead of 200 separate columns.

This is the SINGLE SOURCE OF TRUTH for all database models.
All SQLAlchemy models are defined here using the Hybrid JSONB architecture.
"""

import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Enum, Index,
    Boolean, Numeric, Text, CheckConstraint
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Sport(enum.Enum):
    NBA = "NBA"
    NFL = "NFL"
    MLB = "MLB"
    NHL = "NHL"


class MarketStatus(enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    SETTLED = "SETTLED"


# --- CORE ENTITIES ---

class League(Base):
    """Configuration for leagues (e.g., specific rules, season dates)."""
    __tablename__ = "leagues"
    id = Column(String, primary_key=True)  # "NBA", "NFL"
    sport = Column(Enum(Sport), nullable=False)
    current_season = Column(Integer)  # 2026
    # JSONB for rule sets (e.g., quarter length, shot clock)
    config = Column(JSONB, default=dict)


class Team(Base):
    """Canonical Team Entity."""
    __tablename__ = "teams"
    id = Column(String, primary_key=True)  # UUID or "NBA_LAL"
    league_id = Column(String, ForeignKey("leagues.id"))
    full_name = Column(String, nullable=False)  # "Los Angeles Lakers"
    abbrev = Column(String, index=True)  # "LAL"

    # ENTITY RESOLUTION: List of known aliases from scrapers
    # e.g., ["LA Lakers", "Lakers", "L.A. Lakers"]
    aliases = Column(JSONB, default=list)

    # Universal record tracking
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)

    # DYNAMIC STATS: {"off_rating": 112.5, "pace": 98.0}
    season_stats = Column(JSONB, default=dict)

    # Relationships
    league = relationship("League", backref="teams")


class Player(Base):
    """Canonical Player Entity."""
    __tablename__ = "players"
    id = Column(String, primary_key=True)  # UUID
    team_id = Column(String, ForeignKey("teams.id"))
    name = Column(String, index=True)  # "LeBron James"

    # ENTITY RESOLUTION: ["L. James", "Lebron Raymone James"]
    aliases = Column(JSONB, default=list)

    status = Column(String)  # "ACTIVE", "INJURED-IR"
    # Static info: {"position": "SF", "height": "6-9", "draft_year": 2003}
    details = Column(JSONB, default=dict)

    # Relationships
    team = relationship("Team", backref="players")


# --- DATA LAKE (The "Box Scores") ---

class Game(Base):
    """The central event."""
    __tablename__ = "games"
    id = Column(String, primary_key=True)  # "NBA_20260126_LAL_GSW"
    league_id = Column(String, ForeignKey("leagues.id"))
    date = Column(DateTime, index=True)
    status = Column(Enum(MarketStatus), default=MarketStatus.OPEN)

    home_team_id = Column(String, ForeignKey("teams.id"))
    away_team_id = Column(String, ForeignKey("teams.id"))

    home_score = Column(Integer)
    away_score = Column(Integer)

    # CONTEXT: {"weather": {"temp": 32, "wind": 15}, "stadium": "Chase Center", "refs": [...]}
    environment = Column(JSONB, default=dict)

    # Relationships
    league = relationship("League", backref="games")
    home_team = relationship("Team", foreign_keys=[home_team_id])
    away_team = relationship("Team", foreign_keys=[away_team_id])


class PlayerGameLog(Base):
    """
    THE BOX SCORE.
    This is the most important table for props modeling.
    """
    __tablename__ = "player_game_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(String, ForeignKey("games.id"))
    player_id = Column(String, ForeignKey("players.id"))
    team_id = Column(String, ForeignKey("teams.id"))

    # DYNAMIC STATS:
    # NBA: {"min": 32, "pts": 25, "reb": 8, "ast": 10, "usg_pct": 0.28}
    # NFL: {"pass_yds": 250, "pass_td": 2, "rush_yds": 10, "targets": 0}
    stats = Column(JSONB, nullable=False)

    __table_args__ = (
        Index("idx_pgl_player_game", "player_id", "game_id"),
        Index("idx_pgl_stats_gin", "stats", postgresql_using="gin"),  # Allows searching inside JSON
    )

    # Relationships
    game = relationship("Game", backref="player_logs")
    player = relationship("Player", backref="game_logs")
    team = relationship("Team", backref="player_game_logs")


# --- MARKET & EXECUTION ---

class OddsSnapshot(Base):
    """Captures the market state at a specific time (Steam/CLV tracking)."""
    __tablename__ = "odds_snapshots"
    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(String, ForeignKey("games.id"))
    bookmaker = Column(String)  # "Pinnacle", "DraftKings"
    timestamp = Column(DateTime, default=datetime.utcnow)

    # RAW MARKET DATA:
    # {"spread": {"home": -5.5, "price": -110}, "moneyline": {"home": -220}, "total": 215.5}
    markets = Column(JSONB, nullable=False)

    # Relationships
    game = relationship("Game", backref="odds_snapshots")


class Wager(Base):
    """The Betting Ledger."""
    __tablename__ = "wagers"
    id = Column(String, primary_key=True)
    game_id = Column(String, ForeignKey("games.id"))

    # Bet Details
    market_type = Column(String)  # "PLAYER_PROP", "SPREAD"
    selection = Column(String)  # "Over 22.5 Pts"
    price = Column(Integer)  # -110
    units = Column(Float)  # 1.25

    # The Edge
    model_prob = Column(Float)  # 0.58
    implied_prob = Column(Float)  # 0.524

    # Result & CLV
    result = Column(String)  # "WIN", "LOSS"
    closing_price = Column(Integer)  # -135 (Did we beat the move?)
    profit = Column(Float)

    # Relationships
    game = relationship("Game", backref="wagers")


# --- ENTITY RESOLUTION SUPPORT ---

class CanonicalName(Base):
    """
    Maps scraper aliases to canonical entity UUIDs.
    Used by the EntityResolver to handle name variations.
    """
    __tablename__ = "canonical_names"
    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_type = Column(String, nullable=False)  # "player", "team"
    canonical_id = Column(String, nullable=False, index=True)  # UUID reference
    alias = Column(String, nullable=False, index=True)  # "G. Antetokounmpo"
    source = Column(String)  # "espn", "balldontlie", "manual"
    confidence = Column(Float, default=1.0)  # 1.0 = exact, <1.0 = fuzzy match

    __table_args__ = (
        Index("idx_canonical_alias_type", "alias", "entity_type"),
    )


# --- SIMULATION & CALIBRATION ---

class SimulationStatus(enum.Enum):
    """Status of a simulation run."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Simulation(Base):
    """
    Metadata about Monte Carlo simulation runs.

    Tracks simulation configurations and execution metrics.
    """
    __tablename__ = "simulations"
    id = Column(String, primary_key=True)  # UUID
    league_id = Column(String, ForeignKey("leagues.id"))
    season = Column(Integer, nullable=False)
    simulation_name = Column(String)
    simulation_type = Column(String)  # "game", "player_prop", "season"
    model_version = Column(String)
    num_iterations = Column(Integer, nullable=False)
    status = Column(Enum(SimulationStatus), default=SimulationStatus.PENDING)

    # Execution timing
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    execution_time_seconds = Column(Float)

    # JSONB for flexible parameters (avoid sparse columns)
    # {"variance_scalar": 1.0, "home_advantage": 3.5, "recency_weight": 0.7}
    parameters = Column(JSONB, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    league = relationship("League", backref="simulations")
    results = relationship("SimulationResult", back_populates="simulation")

    __table_args__ = (
        Index("idx_sim_league_season", "league_id", "season"),
        Index("idx_sim_status", "status"),
    )


class SimulationResult(Base):
    """
    Probability distributions and outcomes from Monte Carlo simulations.

    Uses JSONB for score distributions to support any sport without schema bloat.
    The distributions column can store percentiles, histograms, and raw samples.
    """
    __tablename__ = "simulation_results"
    id = Column(String, primary_key=True)  # UUID
    simulation_id = Column(String, ForeignKey("simulations.id"))
    game_id = Column(String, ForeignKey("games.id"))
    season = Column(Integer, nullable=False)

    # Core probabilities (universal across all sports)
    home_win_prob = Column(Float, CheckConstraint('home_win_prob >= 0 AND home_win_prob <= 1'))
    away_win_prob = Column(Float, CheckConstraint('away_win_prob >= 0 AND away_win_prob <= 1'))
    tie_prob = Column(Float)  # For sports that allow ties

    # Spread & Total predictions
    predicted_spread = Column(Float)  # Home team spread (negative = home favored)
    spread_std_dev = Column(Float)
    cover_prob = Column(Float)  # Probability of covering the market spread

    predicted_total = Column(Float)
    total_std_dev = Column(Float)
    over_prob = Column(Float)  # Probability of going over market total

    # Edge calculations (stored for CLV tracking)
    edge_pct = Column(Float)
    ev_pct = Column(Float)
    confidence_tier = Column(String(5))  # A, B, C

    # JSONB for detailed score distributions (hybrid approach)
    # {
    #   "home_score": {"mean": 112.5, "median": 113, "std": 12.3, "p10": 95, "p25": 104, "p75": 121, "p90": 129},
    #   "away_score": {"mean": 108.2, "median": 108, "std": 11.8, ...},
    #   "margin": {"mean": 4.3, "std": 15.2, ...},
    #   "histogram": [[90, 100, 12], [100, 110, 35], ...],
    #   "samples": [{"home": 115, "away": 108}, ...]  # First N samples for debugging
    # }
    distributions = Column(JSONB, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    simulation = relationship("Simulation", back_populates="results")
    game = relationship("Game", backref="simulation_results")

    __table_args__ = (
        Index("idx_simresult_game", "game_id"),
        Index("idx_simresult_season", "season"),
        Index("idx_simresult_distributions_gin", "distributions", postgresql_using="gin"),
    )


class ModelCalibration(Base):
    """
    Model accuracy tracking and parameter tuning.

    Records calibration metrics over time to enable continuous improvement.
    Uses JSONB for sport-specific accuracy metrics.
    """
    __tablename__ = "model_calibrations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    league_id = Column(String, ForeignKey("leagues.id"))
    season = Column(Integer, nullable=False)
    model_version = Column(String, nullable=False)
    calibration_date = Column(DateTime, default=datetime.utcnow)

    # Core calibration metrics
    brier_score = Column(Float)  # Lower is better (0 = perfect)
    log_loss = Column(Float)  # Lower is better
    calibration_error = Column(Float)  # ECE - Expected Calibration Error

    # Win probability accuracy
    win_prob_accuracy = Column(Float)

    # Spread/Total accuracy
    spread_mae = Column(Float)  # Mean Absolute Error for spread predictions
    spread_cover_accuracy = Column(Float)  # % of spread picks correct
    total_mae = Column(Float)
    over_under_accuracy = Column(Float)

    # ROI tracking
    roi_percent = Column(Float)
    profitable_bets = Column(Integer)
    total_bets = Column(Integer)

    # JSONB for sport-specific metrics and parameters
    # {
    #   "parameters_used": {"kelly_multiplier": 0.25, "edge_threshold": 0.03},
    #   "by_market_type": {"spread": {"accuracy": 0.54}, "total": {"accuracy": 0.51}},
    #   "by_confidence_tier": {"A": {"roi": 5.2}, "B": {"roi": -1.3}},
    #   "clv_analysis": {"avg_clv": 1.2, "clv_positive_rate": 0.62}
    # }
    metrics = Column(JSONB, default=dict)

    notes = Column(Text)

    # Relationships
    league = relationship("League", backref="calibrations")

    __table_args__ = (
        Index("idx_calibration_league_season", "league_id", "season"),
        Index("idx_calibration_version", "model_version"),
        Index("idx_calibration_date", "calibration_date"),
    )


class PlayerSeasonStats(Base):
    """
    Aggregated player statistics per season.

    Uses JSONB for sport-specific stats to avoid 200+ sparse columns.
    This complements PlayerGameLog (individual games) with season aggregates.
    """
    __tablename__ = "player_season_stats"
    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(String, ForeignKey("players.id"), nullable=False)
    team_id = Column(String, ForeignKey("teams.id"))
    season = Column(Integer, nullable=False)

    # Universal stats
    games_played = Column(Integer, default=0)
    games_started = Column(Integer, default=0)

    # JSONB for sport-specific season averages and totals
    # NBA: {"pts_per_game": 25.5, "reb_per_game": 8.2, "ast_per_game": 7.1, "usage_rate": 0.32, ...}
    # NFL: {"pass_yds": 4200, "pass_td": 32, "rush_yds": 250, "targets": 0, "fantasy_pts_ppr": 320, ...}
    # MLB: {"avg": 0.285, "hr": 32, "rbi": 98, "ops": 0.875, ...}
    stats = Column(JSONB, nullable=False, default=dict)

    # Projection/fantasy specific
    # {"ppr": 285.5, "half_ppr": 265.2, "standard": 245.0, "projected": 290.0}
    fantasy_points = Column(JSONB, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    player = relationship("Player", backref="season_stats")
    team = relationship("Team", backref="player_stats")

    __table_args__ = (
        Index("idx_player_season_stats", "player_id", "season"),
        Index("idx_team_season_stats", "team_id", "season"),
        Index("idx_player_stats_gin", "stats", postgresql_using="gin"),
    )


class BettingOdds(Base):
    """
    Historical betting odds snapshots for analysis and CLV tracking.

    Separate from OddsSnapshot to maintain backwards compatibility.
    This model tracks opening/closing line movements.
    """
    __tablename__ = "betting_odds"
    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(String, ForeignKey("games.id"), nullable=False)
    sportsbook = Column(String)  # "pinnacle", "draftkings", etc.
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Line data
    home_ml = Column(Integer)  # -150
    away_ml = Column(Integer)  # +130
    spread = Column(Float)  # -5.5
    spread_home_price = Column(Integer)  # -110
    spread_away_price = Column(Integer)  # -110
    total = Column(Float)  # 215.5
    over_price = Column(Integer)  # -110
    under_price = Column(Integer)  # -110

    # Line movement tracking
    is_opening = Column(Boolean, default=False)
    is_closing = Column(Boolean, default=False)

    # Relationships
    game = relationship("Game", backref="betting_odds")

    __table_args__ = (
        Index("idx_betting_odds_game", "game_id"),
        Index("idx_betting_odds_timestamp", "timestamp"),
        Index("idx_betting_odds_book", "sportsbook"),
    )
