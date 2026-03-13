"""
Core data abstractions used across the engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class Team:
    """Lightweight team representation for engine consumption."""

    name: str
    league: str
    abbreviation: str = ""
    record: str = ""
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "league": self.league,
            "abbreviation": self.abbreviation,
            "record": self.record,
            "stats": self.stats,
        }
