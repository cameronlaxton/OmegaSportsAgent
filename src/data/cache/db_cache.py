"""
Persistent DB cache — delegates to src/storage/fact_store.py.

Best-effort: if the DB is not configured, all operations silently return None / no-op.
"""

from __future__ import annotations

import logging
from typing import Optional

from agent.models import GatherSlot, ProviderResult

logger = logging.getLogger("omega.data.cache.db_cache")


def check_db_cache(slot: GatherSlot) -> Optional[ProviderResult]:
    """Check the fact_snapshots table for a fresh cached result.

    Returns a ProviderResult if a non-expired entry exists, else None.
    """
    try:
        from src.storage import get_session
        from src.storage.fact_store import get_cached_fact

        session = get_session()
        if session is None:
            return None

        cached = get_cached_fact(
            session,
            slot.key,
            slot.entity,
            slot.league,
            slot.freshness_max,
        )
        if cached is None:
            session.close()
            return None

        result = ProviderResult(
            data=cached.data,
            source=cached.source,
            source_url=cached.source_url,
            fetched_at=cached.fetched_at,
            confidence=cached.confidence,
        )
        session.close()
        logger.debug("DB cache hit for slot %s (source=%s)", slot.key, cached.source)
        return result

    except Exception as exc:
        logger.debug("DB cache check failed: %s", exc)
        return None


def store_to_db_cache(slot: GatherSlot, result: ProviderResult, quality_score: float) -> None:
    """Store a provider result in the fact_snapshots cache. Best-effort."""
    try:
        from src.storage import get_session
        from src.storage.fact_store import store_fact

        session = get_session()
        if session is None:
            return
        store_fact(session, slot, result, quality_score)
        session.close()
    except Exception as exc:
        logger.debug("DB cache store failed: %s", exc)
