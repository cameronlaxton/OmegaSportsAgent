"""
Name normalizer — delegates to src/normalization/normalizer.py.

Provides a pipeline-compatible interface for entity name normalization.
"""

from __future__ import annotations

from src.normalization.normalizer import (
    normalize_league,
    normalize_player_name,
    normalize_team_name,
)


def normalize_entity_name(name: str, entity_type: str, league: str) -> str:
    """Normalize an entity name based on its type.

    Args:
        name: Raw entity name.
        entity_type: "team" or "player".
        league: League code.

    Returns:
        Normalized name.
    """
    if entity_type == "team":
        return normalize_team_name(name, league)
    elif entity_type == "player":
        return normalize_player_name(name)
    else:
        return name.strip()
