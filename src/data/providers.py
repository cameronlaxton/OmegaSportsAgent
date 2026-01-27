"""
Provider interfaces and lightweight schemas for web/scraped data ingestion.

LLM agents can implement these callables to supply data from search/scrape
workflows without changing the core simulation pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol


# ---- Core Schemas ----


@dataclass
class TeamContextInput:
    name: str
    league: str
    off_rating: Optional[float] = None
    def_rating: Optional[float] = None
    pace: Optional[float] = None
    stats: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "league": self.league,
            "off_rating": self.off_rating,
            "def_rating": self.def_rating,
            "pace": self.pace,
            "stats": self.stats or {},
        }


@dataclass
class PlayerContextInput:
    name: str
    team: str
    league: str
    usage_rate: Optional[float] = None
    stats: Dict[str, Any] = None


@dataclass
class OddsQuote:
    """Normalized odds payload."""

    moneyline_home: Optional[float] = None
    moneyline_away: Optional[float] = None
    spread_home: Optional[float] = None
    spread_away: Optional[float] = None
    over_under: Optional[float] = None
    book: Optional[str] = None
    opened_at: Optional[str] = None
    updated_at: Optional[str] = None
    market_type: str = "pregame"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "moneyline_home": self.moneyline_home,
            "moneyline_away": self.moneyline_away,
            "spread_home": self.spread_home,
            "spread_away": self.spread_away,
            "over_under": self.over_under,
            "book": self.book,
            "opened_at": self.opened_at,
            "updated_at": self.updated_at,
            "market_type": self.market_type,
        }


@dataclass
class HistoricalOddsRecord:
    game_id: str
    league: str
    book: str
    opened_at: str
    moneyline_home: Optional[float] = None
    moneyline_away: Optional[float] = None
    spread_home: Optional[float] = None
    spread_away: Optional[float] = None
    over_under: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class WeatherNewsSignal:
    """Textual/weather signals scraped from public sources."""

    summary: str
    severity: Optional[str] = None
    wind_mph: Optional[float] = None
    temperature_f: Optional[float] = None
    precipitation: Optional[str] = None
    source: Optional[str] = None


# ---- Provider Protocols ----


class GamesProvider(Protocol):
    def __call__(self, league: str) -> List[Dict[str, Any]]:
        ...


class TeamContextProvider(Protocol):
    def __call__(self, team: str, league: str) -> Optional[TeamContextInput]:
        ...


class PlayerContextProvider(Protocol):
    def __call__(self, player: str, league: str) -> Optional[PlayerContextInput]:
        ...


class OddsProvider(Protocol):
    def __call__(self, game: Dict[str, Any], league: str) -> Optional[OddsQuote]:
        ...


class WeatherNewsProvider(Protocol):
    def __call__(self, game: Dict[str, Any], league: str) -> Optional[WeatherNewsSignal]:
        ...

