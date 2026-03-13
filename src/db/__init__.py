"""
OMEGA Sports Betting Database Layer

ACTIVE SCHEMA: src.db.schema (Hybrid JSONB Schema, used by Alembic)
LEGACY SCHEMA: src.db.models + src.db.database (pre-Hybrid ORM, not used in production)

Production code should import from src.db.schema directly.
The legacy re-exports below are retained for backwards compatibility with seed.py.
"""

# Active schema (Hybrid JSONB) - import from here for production use
from src.db.schema import Base as HybridBase

# Legacy ORM re-exports (database.py + models.py) - DO NOT USE for new code
from src.db.database import SessionLocal, get_db, engine, Base
from src.db.models import (
    League, Team, Player, Game,
    Simulation, SimulationResult,
    PlayerSeasonStats, BettingOdds, ModelCalibration
)

__all__ = [
    'HybridBase',
    'SessionLocal', 'get_db', 'engine', 'Base',
    'League', 'Team', 'Player', 'Game',
    'Simulation', 'SimulationResult',
    'PlayerSeasonStats', 'BettingOdds', 'ModelCalibration'
]
