"""
Normalization layer — name cleaning, entity resolution, validation.

Provides stateless name normalization (no DB required) and DB-backed
entity validation (gracefully degrades if DB is unavailable).
"""

from src.normalization.normalizer import (
    normalize_team_name,
    normalize_player_name,
    normalize_league,
)
from src.normalization.validator import validate_entity, ValidationResult

__all__ = [
    "normalize_team_name",
    "normalize_player_name",
    "normalize_league",
    "validate_entity",
    "ValidationResult",
]
