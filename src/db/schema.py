"""
OmegaSportsAgent Hybrid Schema (Relational + JSONB)

Architecture: Uses standard SQL columns for universal data (IDs, Names, Dates)
and JSONB for sport-specific stats to avoid sparse column bloat.

Reasoning: NBA players have rebounds, NFL players have passing_yards.
We use a "Box Score" JSON approach instead of 200 separate columns.
"""

import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Index, Boolean
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
    config = Column(JSONB, default={})


class Team(Base):
    """Canonical Team Entity."""
    __tablename__ = "teams"
    id = Column(String, primary_key=True)  # UUID or "NBA_LAL"
    league_id = Column(String, ForeignKey("leagues.id"))
    full_name = Column(String, nullable=False)  # "Los Angeles Lakers"
    abbrev = Column(String, index=True)  # "LAL"

    # ENTITY RESOLUTION: List of known aliases from scrapers
    # e.g., ["LA Lakers", "Lakers", "L.A. Lakers"]
    aliases = Column(JSONB, default=[])

    # Universal record tracking
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)

    # DYNAMIC STATS: {"off_rating": 112.5, "pace": 98.0}
    season_stats = Column(JSONB, default={})

    # Relationships
    league = relationship("League", backref="teams")


class Player(Base):
    """Canonical Player Entity."""
    __tablename__ = "players"
    id = Column(String, primary_key=True)  # UUID
    team_id = Column(String, ForeignKey("teams.id"))
    name = Column(String, index=True)  # "LeBron James"

    # ENTITY RESOLUTION: ["L. James", "Lebron Raymone James"]
    aliases = Column(JSONB, default=[])

    status = Column(String)  # "ACTIVE", "INJURED-IR"
    # Static info: {"position": "SF", "height": "6-9", "draft_year": 2003}
    details = Column(JSONB, default={})

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
    environment = Column(JSONB, default={})

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
