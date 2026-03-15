"""
Stats extractor — extracts team and player statistics from raw text.
"""

from __future__ import annotations

import re
from typing import Dict, List

from agent.models import GatherSlot
from src.data.extractors.base_extractor import FactExtractor
from src.data.models.facts import SourceAttribution, SportsFact


class StatsExtractor(FactExtractor):
    """Extracts team and player stats from text content."""

    @property
    def data_type(self) -> str:
        return "team_stat"

    def schema_hint(self, slot: GatherSlot) -> Dict[str, str]:
        if slot.data_type == "player_stat":
            return self._player_schema(slot)
        return self._team_schema(slot)

    def _team_schema(self, slot: GatherSlot) -> Dict[str, str]:
        """Schema for team stats — varies by sport."""
        league = slot.league.upper()
        base = {
            "off_rating": "float",
            "def_rating": "float",
            "wins": "int",
            "losses": "int",
        }
        if league in ("NBA", "NCAAB", "WNBA"):
            base.update({
                "pace": "float",
                "fg_pct": "float",
                "three_pt_pct": "float",
                "ft_pct": "float",
                "reb_per_game": "float",
                "ast_per_game": "float",
                "tov_per_game": "float",
                "pts_per_game": "float",
            })
        elif league in ("NFL", "NCAAF"):
            base.update({
                "pts_per_game": "float",
                "yds_per_game": "float",
                "pass_yds_per_game": "float",
                "rush_yds_per_game": "float",
                "turnovers": "int",
            })
        elif league == "MLB":
            base.update({
                "runs_per_game": "float",
                "era": "float",
                "batting_avg": "float",
                "ops": "float",
            })
        elif league == "NHL":
            base.update({
                "goals_per_game": "float",
                "goals_against_per_game": "float",
                "power_play_pct": "float",
                "penalty_kill_pct": "float",
                "save_pct": "float",
            })
        return base

    def _player_schema(self, slot: GatherSlot) -> Dict[str, str]:
        """Schema for player stats."""
        return {
            "pts_mean": "float",
            "pts_std": "float",
            "reb_mean": "float",
            "ast_mean": "float",
            "stl_mean": "float",
            "blk_mean": "float",
            "min_mean": "float",
            "fg_pct": "float",
            "three_pt_pct": "float",
            "ft_pct": "float",
            "games_played": "int",
        }

    def extract_rule_based(
        self, raw_text: str, slot: GatherSlot, attribution: SourceAttribution
    ) -> List[SportsFact]:
        """Try to extract stats from common patterns."""
        facts: List[SportsFact] = []

        # Common stat patterns: "ORtg: 115.2" or "Offensive Rating: 115.2"
        _STAT_PATTERNS = {
            "off_rating": [
                r"(?:offensive\s+rating|ortg|off[._\s]?rating)[:\s]+(\d+\.?\d*)",
            ],
            "def_rating": [
                r"(?:defensive\s+rating|drtg|def[._\s]?rating)[:\s]+(\d+\.?\d*)",
            ],
            "pace": [
                r"(?:pace)[:\s]+(\d+\.?\d*)",
            ],
            "pts_per_game": [
                r"(?:points?\s+per\s+game|ppg|pts/?g)[:\s]+(\d+\.?\d*)",
            ],
            "fg_pct": [
                r"(?:field\s+goal\s+(?:pct|percentage|%)|fg[_%])[:\s]+(\d+\.?\d*)",
            ],
            "three_pt_pct": [
                r"(?:3[- ]?(?:pt|point)\s+(?:pct|percentage|%)|3p[_%]|three[- ]?pt)[:\s]+(\d+\.?\d*)",
            ],
        }

        entity = slot.entity
        league = slot.league

        for key, patterns in _STAT_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, raw_text, re.IGNORECASE)
                if match:
                    try:
                        value = float(match.group(1))
                        facts.append(SportsFact(
                            key=key,
                            value=value,
                            data_type=slot.data_type,
                            entity=entity,
                            league=league,
                            attribution=attribution,
                        ))
                    except ValueError:
                        pass
                    break  # Take first match per key

        return facts
