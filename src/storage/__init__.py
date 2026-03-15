"""
Storage layer — canonical persistence for the agent lifecycle.

Provides get_session() as the single point for obtaining a SQLAlchemy session.
If DATABASE_URL is not configured, get_session() returns None and all storage
operations degrade gracefully (the pipeline still works, just without caching).
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger("omega.storage")

_engine = None
_session_factory = None


def _init_engine():
    """Initialize the SQLAlchemy engine from DATABASE_URL."""
    global _engine, _session_factory
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        logger.debug("DATABASE_URL not set — storage layer disabled")
        return
    try:
        _engine = create_engine(database_url, pool_pre_ping=True)
        _session_factory = sessionmaker(bind=_engine)
        logger.info("Storage engine initialized")
    except Exception as exc:
        logger.warning("Failed to initialize storage engine: %s", exc)
        _engine = None
        _session_factory = None


def get_session() -> Optional[Session]:
    """Return a SQLAlchemy session if DATABASE_URL is configured, else None.

    Callers must handle None gracefully — storage is optional.
    The session should be used as a context manager or closed explicitly.
    """
    global _engine, _session_factory
    if _session_factory is None:
        _init_engine()
    if _session_factory is None:
        return None
    return _session_factory()
