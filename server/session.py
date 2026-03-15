"""
In-memory session store for chat conversations.

Tracks conversation history per session with TTL-based pruning.
The interface is designed so it can be swapped to Redis or DB later
without changing endpoint code.
"""

from __future__ import annotations

import logging
import time
import threading
from typing import Dict, List, Optional
from uuid import uuid4

from src.contracts.schemas import ChatMessage

logger = logging.getLogger("omega.server.session")

MAX_MESSAGES_PER_SESSION = 20
DEFAULT_MAX_AGE_SEC = 3600  # 1 hour


class SessionStore:
    """Thread-safe in-memory conversation store."""

    def __init__(self, max_age_sec: int = DEFAULT_MAX_AGE_SEC) -> None:
        self._sessions: Dict[str, List[ChatMessage]] = {}
        self._timestamps: Dict[str, float] = {}  # session_id → last_active epoch
        self._max_age_sec = max_age_sec
        self._lock = threading.Lock()

    def create_session(self) -> str:
        """Create a new session and return its ID."""
        session_id = uuid4().hex
        with self._lock:
            self._sessions[session_id] = []
            self._timestamps[session_id] = time.time()
        logger.info("Created session %s", session_id)
        return session_id

    def get_or_create(self, session_id: Optional[str]) -> str:
        """Return existing session ID or create a new one."""
        if session_id and session_id in self._sessions:
            with self._lock:
                self._timestamps[session_id] = time.time()
            return session_id
        return self.create_session()

    def get_history(self, session_id: str) -> List[ChatMessage]:
        """Return conversation history for a session."""
        with self._lock:
            return list(self._sessions.get(session_id, []))

    def append(self, session_id: str, message: ChatMessage) -> None:
        """Append a message to the session history."""
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = []
            self._sessions[session_id].append(message)
            # Trim to max messages (keep most recent)
            if len(self._sessions[session_id]) > MAX_MESSAGES_PER_SESSION:
                self._sessions[session_id] = self._sessions[session_id][-MAX_MESSAGES_PER_SESSION:]
            self._timestamps[session_id] = time.time()

    def prune(self) -> int:
        """Remove sessions older than max_age_sec. Returns count removed."""
        now = time.time()
        expired = []
        with self._lock:
            for sid, ts in self._timestamps.items():
                if now - ts > self._max_age_sec:
                    expired.append(sid)
            for sid in expired:
                del self._sessions[sid]
                del self._timestamps[sid]
        if expired:
            logger.info("Pruned %d expired sessions", len(expired))
        return len(expired)


# Module-level singleton
session_store = SessionStore()
