"""
Session-scoped in-memory cache for hot data during a single retrieval pass.

Prevents redundant lookups when multiple slots need the same underlying data
(e.g., home_team.off_rating and home_team.def_rating both from the same
team stats fetch).
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any, Optional


class SessionCache:
    """Simple LRU cache scoped to one retrieve_facts() call.

    Keys are (data_type, entity, league) tuples.
    Values are raw data dicts from providers.
    """

    def __init__(self, max_size: int = 128):
        self._store: OrderedDict[tuple, Any] = OrderedDict()
        self._max_size = max_size

    def _make_key(self, data_type: str, entity: str, league: str) -> tuple:
        return (data_type, entity.lower().strip(), league.upper().strip())

    def get(self, data_type: str, entity: str, league: str) -> Optional[Any]:
        """Retrieve cached data, or None if not present."""
        key = self._make_key(data_type, entity, league)
        if key in self._store:
            self._store.move_to_end(key)
            return self._store[key]
        return None

    def put(self, data_type: str, entity: str, league: str, value: Any) -> None:
        """Store a value in the cache."""
        key = self._make_key(data_type, entity, league)
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = value
        if len(self._store) > self._max_size:
            self._store.popitem(last=False)

    def clear(self) -> None:
        """Clear all cached entries."""
        self._store.clear()

    def __len__(self) -> int:
        return len(self._store)
