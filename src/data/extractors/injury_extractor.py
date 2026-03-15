"""
Injury extractor — extracts injury/availability status from raw text.
"""

from __future__ import annotations

import re
from typing import Dict, List

from agent.models import GatherSlot
from src.data.extractors.base_extractor import FactExtractor
from src.data.models.facts import SourceAttribution, SportsFact


class InjuryExtractor(FactExtractor):
    """Extracts injury and availability information from text content."""

    @property
    def data_type(self) -> str:
        return "injury"

    def schema_hint(self, slot: GatherSlot) -> Dict[str, str]:
        return {
            "player_name": "str",
            "status": "str",          # "out", "doubtful", "questionable", "probable", "available"
            "injury_type": "str",     # "ankle", "knee", "illness", etc.
            "expected_return": "str",  # ISO date or description
            "team": "str",
        }

    def extract_rule_based(
        self, raw_text: str, slot: GatherSlot, attribution: SourceAttribution
    ) -> List[SportsFact]:
        """Try to extract injury info from common patterns."""
        facts: List[SportsFact] = []

        # Pattern: "Player Name (injury) - Status" or "Player Name: Status (injury)"
        injury_pattern = re.compile(
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s*"
            r"(?:\(([^)]+)\)\s*[-–—]\s*|:\s*)"
            r"(out|doubtful|questionable|probable|day-to-day|injured|available)",
            re.IGNORECASE,
        )

        entity_lower = slot.entity.lower()
        for match in injury_pattern.finditer(raw_text):
            player = match.group(1).strip()
            injury_type = match.group(2).strip() if match.group(2) else "unspecified"
            status = match.group(3).strip().lower()

            # Only include if entity matches (team name in text near the player)
            context_start = max(0, match.start() - 200)
            context = raw_text[context_start:match.end() + 200].lower()
            if entity_lower in context:
                facts.append(SportsFact(
                    key="player_name",
                    value=player,
                    data_type="injury",
                    entity=slot.entity,
                    league=slot.league,
                    attribution=attribution,
                ))
                facts.append(SportsFact(
                    key="status",
                    value=status,
                    data_type="injury",
                    entity=slot.entity,
                    league=slot.league,
                    attribution=attribution,
                ))
                facts.append(SportsFact(
                    key="injury_type",
                    value=injury_type,
                    data_type="injury",
                    entity=slot.entity,
                    league=slot.league,
                    attribution=attribution,
                ))

        return facts
