"""
Odds extractor — extracts betting odds from raw text.
"""

from __future__ import annotations

import re
from typing import Dict, List

from agent.models import GatherSlot
from src.data.extractors.base_extractor import FactExtractor
from src.data.models.facts import SourceAttribution, SportsFact


class OddsExtractor(FactExtractor):
    """Extracts odds/betting lines from text content."""

    @property
    def data_type(self) -> str:
        return "odds"

    def schema_hint(self, slot: GatherSlot) -> Dict[str, str]:
        return {
            "moneyline_home": "int",
            "moneyline_away": "int",
            "spread_home": "float",
            "spread_away": "float",
            "spread_price_home": "int",
            "spread_price_away": "int",
            "total": "float",
            "total_over_price": "int",
            "total_under_price": "int",
            "bookmaker": "str",
        }

    def extract_rule_based(
        self, raw_text: str, slot: GatherSlot, attribution: SourceAttribution
    ) -> List[SportsFact]:
        """Try to extract odds from common formats."""
        facts: List[SportsFact] = []

        # Pattern: American moneyline like "-150" or "+130"
        ml_pattern = re.compile(r"([+-]\d{3,4})")
        moneylines = ml_pattern.findall(raw_text)

        if len(moneylines) >= 2:
            facts.append(SportsFact(
                key="moneyline_home",
                value=int(moneylines[0]),
                data_type="odds",
                entity=slot.entity,
                league=slot.league,
                attribution=attribution,
            ))
            facts.append(SportsFact(
                key="moneyline_away",
                value=int(moneylines[1]),
                data_type="odds",
                entity=slot.entity,
                league=slot.league,
                attribution=attribution,
            ))

        # Pattern: spread like "-3.5" or "+7"
        spread_pattern = re.compile(r"spread[:\s]+([+-]?\d+\.?\d*)", re.IGNORECASE)
        spread_match = spread_pattern.search(raw_text)
        if spread_match:
            facts.append(SportsFact(
                key="spread_home",
                value=float(spread_match.group(1)),
                data_type="odds",
                entity=slot.entity,
                league=slot.league,
                attribution=attribution,
            ))

        # Pattern: total/over-under like "O/U 224.5" or "Total: 224.5"
        total_pattern = re.compile(
            r"(?:total|o/?u|over/?under)[:\s]+(\d{2,3}\.?\d*)",
            re.IGNORECASE,
        )
        total_match = total_pattern.search(raw_text)
        if total_match:
            facts.append(SportsFact(
                key="total",
                value=float(total_match.group(1)),
                data_type="odds",
                entity=slot.entity,
                league=slot.league,
                attribution=attribution,
            ))

        return facts
