"""
Schedule extractor — extracts game schedule data from raw text.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Dict, List

from agent.models import GatherSlot
from src.data.extractors.base_extractor import FactExtractor
from src.data.models.facts import SourceAttribution, SportsFact


class ScheduleExtractor(FactExtractor):
    """Extracts schedule/matchup data from text content."""

    @property
    def data_type(self) -> str:
        return "schedule"

    def schema_hint(self, slot: GatherSlot) -> Dict[str, str]:
        return {
            "home_team": "str",
            "away_team": "str",
            "game_time": "str",
            "venue": "str",
            "status": "str",
            "home_score": "int",
            "away_score": "int",
        }

    def extract_rule_based(
        self, raw_text: str, slot: GatherSlot, attribution: SourceAttribution
    ) -> List[SportsFact]:
        """Try to extract schedule info from common patterns."""
        facts: List[SportsFact] = []

        # Pattern: "Team A vs Team B" or "Team A @ Team B"
        vs_pattern = re.compile(
            r"([A-Z][a-zA-Z\s]+?)\s+(?:vs\.?|@|at)\s+([A-Z][a-zA-Z\s]+?)(?:\s|,|\.|$)",
            re.IGNORECASE,
        )

        entity_lower = slot.entity.lower()
        for match in vs_pattern.finditer(raw_text):
            team1 = match.group(1).strip()
            team2 = match.group(2).strip()

            if entity_lower in team1.lower() or entity_lower in team2.lower():
                facts.append(SportsFact(
                    key="away_team",
                    value=team1,
                    data_type="schedule",
                    entity=slot.entity,
                    league=slot.league,
                    attribution=attribution,
                ))
                facts.append(SportsFact(
                    key="home_team",
                    value=team2,
                    data_type="schedule",
                    entity=slot.entity,
                    league=slot.league,
                    attribution=attribution,
                ))
                break

        return facts
