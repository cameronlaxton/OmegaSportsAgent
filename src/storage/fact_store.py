"""
Fact Store — TTL-aware cache for provider results.

Stores every value the agent gathers from providers in the fact_snapshots
table. On subsequent queries, the fact gatherer checks here before hitting
remote APIs, reducing latency and API quota consumption.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

from agent.models import GatherSlot, ProviderResult
from src.db.schema import FactSnapshot

logger = logging.getLogger("omega.storage.fact_store")


def get_cached_fact(
    session: Session,
    slot_key: str,
    entity: str,
    league: str,
    freshness_max: float,
) -> Optional[FactSnapshot]:
    """Look up a non-expired fact_snapshot row.

    Returns the newest matching row where expires_at > now, or None.
    """
    now = datetime.utcnow()
    try:
        row = (
            session.query(FactSnapshot)
            .filter(
                and_(
                    FactSnapshot.slot_key == slot_key,
                    FactSnapshot.entity == entity,
                    FactSnapshot.league == league,
                    FactSnapshot.expires_at > now,
                )
            )
            .order_by(FactSnapshot.fetched_at.desc())
            .first()
        )
        return row
    except Exception as exc:
        logger.debug("Fact cache lookup failed: %s", exc)
        return None


def store_fact(
    session: Session,
    slot: GatherSlot,
    result: ProviderResult,
    quality_score: float,
) -> Optional[FactSnapshot]:
    """Insert a new fact_snapshot row.

    Computes expires_at = fetched_at + timedelta(seconds=slot.freshness_max).
    Returns the inserted row, or None on failure.
    """
    try:
        row = FactSnapshot(
            slot_key=slot.key,
            data_type=slot.data_type,
            entity=slot.entity,
            league=slot.league,
            data=result.data,
            source=result.source,
            source_url=result.source_url,
            confidence=result.confidence,
            fetched_at=result.fetched_at,
            expires_at=result.fetched_at + timedelta(seconds=slot.freshness_max),
            quality_score=quality_score,
        )
        session.add(row)
        session.commit()
        return row
    except Exception as exc:
        logger.warning("Failed to store fact: %s", exc)
        session.rollback()
        return None


def purge_expired(session: Session) -> int:
    """Delete expired fact_snapshots. Returns count of rows deleted."""
    now = datetime.utcnow()
    try:
        count = (
            session.query(FactSnapshot)
            .filter(FactSnapshot.expires_at < now)
            .delete()
        )
        session.commit()
        return count
    except Exception as exc:
        logger.warning("Failed to purge expired facts: %s", exc)
        session.rollback()
        return 0
