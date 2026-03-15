"""Extractors — convert raw text/data into structured SportsFact objects."""

from src.data.extractors.base_extractor import FactExtractor, get_extractor
from src.data.extractors.schedule_extractor import ScheduleExtractor
from src.data.extractors.odds_extractor import OddsExtractor
from src.data.extractors.stats_extractor import StatsExtractor
from src.data.extractors.injury_extractor import InjuryExtractor
from src.data.extractors.game_log_extractor import GameLogExtractor

__all__ = [
    "FactExtractor",
    "get_extractor",
    "ScheduleExtractor",
    "OddsExtractor",
    "StatsExtractor",
    "InjuryExtractor",
    "GameLogExtractor",
]
