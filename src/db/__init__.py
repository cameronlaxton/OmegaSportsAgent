"""
OMEGA Sports Betting Database Layer

Active schema: src.db.schema (Hybrid JSONB Schema, tracked by Alembic).
Legacy ORM (models.py, database.py, seed.py) has been removed.
"""

from src.db.schema import Base as HybridBase

__all__ = [
    "HybridBase",
]
