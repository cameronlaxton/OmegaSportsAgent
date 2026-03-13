"""
Lightweight persistence helpers for historical odds.

This is intentionally minimal so LLM agents can swap in their own storage.
Defaults to JSONL under data/odds_history.jsonl.
"""

from __future__ import annotations

import json
import os
from typing import Dict, Any, List

DEFAULT_ODDS_HISTORY_PATH = "data/odds_history.jsonl"


def append_odds_record(record: Dict[str, Any], path: str = DEFAULT_ODDS_HISTORY_PATH) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def load_odds_history(path: str = DEFAULT_ODDS_HISTORY_PATH, limit: int = 10000) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    records: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= limit:
                break
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records
