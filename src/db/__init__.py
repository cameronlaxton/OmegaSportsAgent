"""
OMEGA Sports Betting Database Layer
Multi-sport PostgreSQL storage for simulations, predictions, and analytics.

All models are defined in src.db.schema using the Hybrid JSONB architecture.
This is the SINGLE SOURCE OF TRUTH for database models.
"""

from src.db.database import SessionLocal, get_db, engine
from src.db.schema import (
    # Base class
    Base,
    # Enums
    Sport, MarketStatus, SimulationStatus,
    # Core entities
    League, Team, Player, Game, PlayerGameLog,
    # Market & Execution
    OddsSnapshot, Wager,
    # Entity resolution
    CanonicalName,
    # Simulation & Calibration
    Simulation, SimulationResult, ModelCalibration,
    # Stats & Odds tracking
    PlayerSeasonStats, BettingOdds,
)

__all__ = [
    # Database utilities
    'SessionLocal', 'get_db', 'engine', 'Base',
    # Enums
    'Sport', 'MarketStatus', 'SimulationStatus',
    # Core entities
    'League', 'Team', 'Player', 'Game', 'PlayerGameLog',
    # Market & Execution
    'OddsSnapshot', 'Wager',
    # Entity resolution
    'CanonicalName',
    # Simulation & Calibration
    'Simulation', 'SimulationResult', 'ModelCalibration',
    # Stats & Odds tracking
    'PlayerSeasonStats', 'BettingOdds',
]
