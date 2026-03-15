"""
Game log extractor — extracts player game-by-game stats from raw text.
"""

from __future__ import annotations

import re
from typing import Dict, List

from agent.models import GatherSlot
from src.data.extractors.base_extractor import FactExtractor
from src.data.models.facts import SourceAttribution, SportsFact


class GameLogExtractor(FactExtractor):
    """Extracts player game log entries from text content."""

    @property
    def data_type(self) -> str:
        return "player_game_log"

    def schema_hint(self, slot: GatherSlot) -> Dict[str, str]:
        return {
            "games": "list",  # List of game objects
            "pts_mean": "float",
            "pts_std": "float",
            "reb_mean": "float",
            "ast_mean": "float",
            "min_mean": "float",
            "last_5_pts": "list",
            "last_5_reb": "list",
            "last_5_ast": "list",
        }

    def extract_rule_based(
        self, raw_text: str, slot: GatherSlot, attribution: SourceAttribution
    ) -> List[SportsFact]:
        """Try to extract game log stats from common patterns."""
        facts: List[SportsFact] = []

        # Pattern: "X points" or "scored X" in recent game context
        pts_pattern = re.compile(
            r"(\d{1,2})\s+(?:points|pts|PTS)", re.IGNORECASE
        )
        pts_values = [int(m.group(1)) for m in pts_pattern.finditer(raw_text)]

        if pts_values:
            # Take last 5 if more than 5 found
            recent = pts_values[:10]  # Cap at 10 games
            mean_pts = sum(recent) / len(recent)

            facts.append(SportsFact(
                key="pts_mean",
                value=round(mean_pts, 1),
                data_type="player_game_log",
                entity=slot.entity,
                league=slot.league,
                attribution=attribution,
            ))

            if len(recent) > 1:
                import statistics
                std_pts = statistics.stdev(recent)
                facts.append(SportsFact(
                    key="pts_std",
                    value=round(std_pts, 1),
                    data_type="player_game_log",
                    entity=slot.entity,
                    league=slot.league,
                    attribution=attribution,
                ))

            facts.append(SportsFact(
                key="last_5_pts",
                value=recent[:5],
                data_type="player_game_log",
                entity=slot.entity,
                league=slot.league,
                attribution=attribution,
            ))

        return facts
