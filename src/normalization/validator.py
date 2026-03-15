"""
Entity Validator — checks if entities exist in the DB.

Non-blocking: if the DB is not configured, returns a permissive result
with lower confidence. The pipeline never fails due to validation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

logger = logging.getLogger("omega.normalization.validator")


@dataclass
class ValidationResult:
    """Result of entity validation."""

    is_valid: bool
    canonical_id: Optional[str] = None
    canonical_name: Optional[str] = None
    confidence: float = 0.5
    warning: Optional[str] = None


def validate_entity(
    entity_name: str,
    entity_type: str,
    league: str,
    session: Optional[Session] = None,
) -> ValidationResult:
    """Validate an entity against the DB.

    If session is None (no DB), returns a permissive result.
    If DB is available, uses EntityResolver for resolution.
    """
    if session is None:
        return ValidationResult(
            is_valid=True,
            confidence=0.5,
            warning="no_db_validation",
        )

    try:
        from src.normalization.entity_resolver import EntityResolver

        resolver = EntityResolver(session)

        if entity_type == "team":
            resolved = resolver.resolve_team(entity_name, league)
        elif entity_type == "player":
            resolved = resolver.resolve_player(entity_name, league)
        else:
            return ValidationResult(
                is_valid=True,
                confidence=0.5,
                warning=f"unknown_entity_type:{entity_type}",
            )

        if resolved is None:
            return ValidationResult(
                is_valid=False,
                confidence=0.0,
                warning=f"entity_not_found:{entity_name}",
            )

        return ValidationResult(
            is_valid=True,
            canonical_id=resolved.canonical_id,
            canonical_name=resolved.canonical_name,
            confidence=resolved.confidence,
            warning=f"fuzzy_match:{resolved.confidence:.2f}" if resolved.confidence < 1.0 else None,
        )

    except Exception as exc:
        logger.debug("Entity validation failed: %s", exc)
        return ValidationResult(
            is_valid=True,
            confidence=0.5,
            warning=f"validation_error:{exc}",
        )
