"""
Simple file-based cache/persistence for analysis results.

Used to avoid re-simulating identical requests and to persist
intermediate data across agent runs.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Dict, Optional


class OmegaCacheLogger:
    """File-based key-value cache with JSON serialization."""

    def __init__(self, cache_dir: str = ".omega_cache") -> None:
        self.cache_dir = os.path.abspath(cache_dir)
        os.makedirs(self.cache_dir, exist_ok=True)

    def _key_path(self, key: str) -> str:
        safe_key = hashlib.sha256(key.encode()).hexdigest()[:16]
        return os.path.join(self.cache_dir, f"{safe_key}.json")

    def save(self, key: str, data: Dict[str, Any]) -> None:
        """Save a dict to cache under the given key."""
        path = self._key_path(key)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"key": key, "data": data}, f, default=str)

    def load(self, key: str) -> Optional[Dict[str, Any]]:
        """Load a cached dict by key. Returns None if not found."""
        path = self._key_path(key)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            if payload.get("key") == key:
                return payload.get("data")
        except (json.JSONDecodeError, KeyError):
            pass
        return None

    def clear(self) -> None:
        """Remove all cached entries."""
        for fname in os.listdir(self.cache_dir):
            if fname.endswith(".json"):
                os.remove(os.path.join(self.cache_dir, fname))
