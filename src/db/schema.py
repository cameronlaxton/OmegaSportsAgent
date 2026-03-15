"""
OmegaSportsAgent Hybrid Schema (Relational + JSONB)

Architecture: Uses standard SQL columns for universal data (IDs, Names, Dates)
and JSONB for sport-specific stats to avoid sparse column bloat.

Reasoning: NBA players have rebounds, NFL players have passing_yards.
We use a "Box Score" JSON approach instead of 200 separate columns.
"""

import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Index
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


# --- AGENT STORAGE ---

class FactSnapshot(Base):
    """Timestamped data observation with source provenance and TTL.

    The fact cache: stores every value the agent gathers from providers
    so repeat queries hit the cache instead of re-fetching.
    """
    __tablename__ = "fact_snapshots"
    id = Column(Integer, primary_key=True, autoincrement=True)
    slot_key = Column(String, nullable=False, index=True)   # e.g. "home_team.off_rating"
    data_type = Column(String, nullable=False)               # "team_stat", "odds", "injury", etc.
    entity = Column(String, nullable=False, index=True)      # team or player name
    league = Column(String, nullable=False)
    data = Column(JSONB, nullable=False)                     # the actual payload
    source = Column(String, nullable=False)                  # provider name
    source_url = Column(String)                              # attribution URL
    confidence = Column(Float, default=1.0)
    fetched_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)            # fetched_at + TTL
    quality_score = Column(Float, default=0.0)

    __table_args__ = (
        Index("idx_fact_snap_lookup", "slot_key", "entity", "league"),
        Index("idx_fact_snap_expires", "expires_at"),
        Index("idx_fact_snap_data_gin", "data", postgresql_using="gin"),
    )


class ExecutionRun(Base):
    """Audit trail of every agent query execution.

    Records what the agent understood, planned, gathered, and produced
    so we can debug and improve the pipeline.
    """
    __tablename__ = "execution_runs"
    id = Column(String, primary_key=True)                    # UUID4
    query_text = Column(String, nullable=False)
    understanding = Column(JSONB)                            # serialized QueryUnderstanding
    plan = Column(JSONB)                                     # serialized AnswerPlan
    slots_requested = Column(Integer)
    slots_filled = Column(Integer)
    data_quality_score = Column(Float)
    execution_mode = Column(String)
    providers_used = Column(JSONB, default=list)             # ["espn_schedule", "odds_api"]
    errors = Column(JSONB, default=list)
    duration_ms = Column(Integer)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)


class Prediction(Base):
    """Prediction ledger for backtesting and calibration.

    Every formal edge the system outputs is logged here with
    the market snapshot at prediction time, enabling later settlement
    and walk-forward validation.
    """
    __tablename__ = "predictions"
    id = Column(String, primary_key=True)                    # UUID4
    execution_run_id = Column(String, ForeignKey("execution_runs.id"))
    game_id = Column(String, ForeignKey("games.id"))
    league = Column(String, nullable=False)
    prediction_type = Column(String, nullable=False)         # "spread", "moneyline", "total", "player_prop"
    prediction = Column(JSONB, nullable=False)               # {"side": "home", "line": -5.5, "model_prob": 0.58}
    market_snapshot = Column(JSONB)                          # odds at prediction time
    data_quality_score = Column(Float)
    outcome = Column(String)                                 # "WIN", "LOSS", "PUSH", None if unsettled
    settled_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Relationships
    execution_run = relationship("ExecutionRun", backref="predictions")
    game = relationship("Game", backref="predictions")
