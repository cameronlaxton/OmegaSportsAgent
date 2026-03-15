"""
Free Data Sources Catalog

Documentation of available free APIs and their limits.
Provides unified interface for data access.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from src.data import odds_scraper, stats_scraper, schedule_api


class DataCategory(Enum):
    """Categories of sports data."""
    ODDS = "odds"
    SCHEDULE = "schedule"
    PLAYER_STATS = "player_stats"
    TEAM_STATS = "team_stats"
    STANDINGS = "standings"
    LIVE_SCORES = "live_scores"


@dataclass
class DataSource:
    """Information about a data source."""
    name: str
    url: str
    category: List[DataCategory]
    rate_limit: str
    daily_limit: Optional[int]
    requires_key: bool
    notes: str


FREE_DATA_SOURCES: Dict[str, DataSource] = {
    "odds_api": DataSource(
        name="The Odds API",
        url="https://the-odds-api.com",
        category=[DataCategory.ODDS],
        rate_limit="500 requests/month on free tier",
        daily_limit=None,
        requires_key=True,
        notes="Free tier: 500 requests/month. Provides odds from multiple bookmakers. "
              "Supports NBA, NFL, MLB, NHL, NCAAB, NCAAF and more. "
              "Set ODDS_API_KEY environment variable."
    ),
    "espn_api": DataSource(
        name="ESPN API",
        url="https://site.api.espn.com",
        category=[DataCategory.SCHEDULE, DataCategory.LIVE_SCORES, DataCategory.STANDINGS, 
                  DataCategory.PLAYER_STATS, DataCategory.TEAM_STATS],
        rate_limit="Unofficial - be respectful",
        daily_limit=None,
        requires_key=False,
        notes="Unofficial but widely used. No API key needed. "
              "Provides schedules, scores, standings, and basic stats. "
              "Rate limit yourself to avoid blocks."
    ),
    "basketball_reference": DataSource(
        name="Basketball Reference",
        url="https://www.basketball-reference.com",
        category=[DataCategory.PLAYER_STATS, DataCategory.TEAM_STATS],
        rate_limit="~20 requests/minute recommended",
        daily_limit=None,
        requires_key=False,
        notes="Comprehensive NBA/WNBA/NCAAB statistics. Scraping required. "
              "Very detailed historical data. Respect robots.txt."
    ),
    "pro_football_reference": DataSource(
        name="Pro Football Reference",
        url="https://www.pro-football-reference.com",
        category=[DataCategory.PLAYER_STATS, DataCategory.TEAM_STATS],
        rate_limit="~20 requests/minute recommended",
        daily_limit=None,
        requires_key=False,
        notes="Comprehensive NFL statistics. Scraping required. "
              "Historical data back to 1920. Respect robots.txt."
    ),
    "baseball_reference": DataSource(
        name="Baseball Reference",
        url="https://www.baseball-reference.com",
        category=[DataCategory.PLAYER_STATS, DataCategory.TEAM_STATS],
        rate_limit="~20 requests/minute recommended",
        daily_limit=None,
        requires_key=False,
        notes="Comprehensive MLB statistics. Scraping required. "
              "Extensive historical data."
    ),
    "hockey_reference": DataSource(
        name="Hockey Reference",
        url="https://www.hockey-reference.com",
        category=[DataCategory.PLAYER_STATS, DataCategory.TEAM_STATS],
        rate_limit="~20 requests/minute recommended",
        daily_limit=None,
        requires_key=False,
        notes="Comprehensive NHL statistics. Scraping required."
    ),
    "nba_api": DataSource(
        name="NBA Stats API",
        url="https://stats.nba.com",
        category=[DataCategory.PLAYER_STATS, DataCategory.TEAM_STATS],
        rate_limit="Strict - requires proper headers",
        daily_limit=None,
        requires_key=False,
        notes="Official NBA stats API. Requires specific headers. "
              "Can be unstable. Use nba_api Python package."
    )
}


def list_sources(category: Optional[DataCategory] = None) -> List[Dict[str, Any]]:
    """
    List available data sources, optionally filtered by category.
    
    Args:
        category: Optional category to filter by
    
    Returns:
        List of source information dictionaries
    """
    sources = []
    
    for key, source in FREE_DATA_SOURCES.items():
        if category is None or category in source.category:
            sources.append({
                "key": key,
                "name": source.name,
                "url": source.url,
                "categories": [c.value for c in source.category],
                "rate_limit": source.rate_limit,
                "requires_key": source.requires_key,
                "notes": source.notes
            })
    
    return sources


def get_source_info(source_key: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a specific data source.
    
    Args:
        source_key: Source identifier
    
    Returns:
        Source information or None if not found
    """
    source = FREE_DATA_SOURCES.get(source_key)
    if source is None:
        return None
    
    return {
        "key": source_key,
        "name": source.name,
        "url": source.url,
        "categories": [c.value for c in source.category],
        "rate_limit": source.rate_limit,
        "daily_limit": source.daily_limit,
        "requires_key": source.requires_key,
        "notes": source.notes
    }


class UnifiedDataClient:
    """
    Unified interface for accessing sports data from multiple free sources.
    Automatically selects the best source and handles fallbacks.
    """
    
    def __init__(self):
        """Initialize the unified data client."""
        self._source_priority = {
            DataCategory.ODDS: ["odds_api", "espn_api"],
            DataCategory.SCHEDULE: ["espn_api"],
            DataCategory.PLAYER_STATS: ["basketball_reference", "pro_football_reference", "espn_api"],
            DataCategory.TEAM_STATS: ["basketball_reference", "pro_football_reference", "espn_api"],
            DataCategory.STANDINGS: ["espn_api"],
            DataCategory.LIVE_SCORES: ["espn_api"]
        }
    
    def get_odds(self, league: str, game_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get odds data for a league or specific game.
        
        Args:
            league: League code
            game_id: Optional game ID for specific game odds
        
        Returns:
            Odds data dictionary
        """
        if game_id:
            return {
                "source": "odds_api",
                "data": odds_scraper.get_current_odds(game_id, league)
            }
        
        return {
            "source": "odds_api",
            "data": odds_scraper.get_upcoming_games(league)
        }
    
    def get_schedule(self, league: str, days: int = 1) -> Dict[str, Any]:
        """
        Get game schedule for a league.
        
        Args:
            league: League code
            days: Number of days to include
        
        Returns:
            Schedule data dictionary
        """
        if days == 1:
            return {
                "source": "espn_api",
                "data": schedule_api.get_todays_games(league)
            }
        
        return {
            "source": "espn_api",
            "data": schedule_api.get_upcoming_games(league, days)
        }
    
    def get_player_stats(self, player_name: str, league: str) -> Dict[str, Any]:
        """
        Get player statistics.
        
        Args:
            player_name: Player's full name
            league: League code
        
        Returns:
            Player stats dictionary
        """
        source = "basketball_reference" if league.upper() in ["NBA", "NCAAB"] else "pro_football_reference"
        
        return {
            "source": source,
            "data": stats_scraper.get_player_stats(player_name, league)
        }
    
    def get_team_stats(self, team: str, league: str) -> Dict[str, Any]:
        """
        Get team statistics.
        
        Args:
            team: Team name or abbreviation
            league: League code
        
        Returns:
            Team stats dictionary
        """
        source = "basketball_reference" if league.upper() in ["NBA", "NCAAB"] else "pro_football_reference"
        
        return {
            "source": source,
            "data": stats_scraper.get_team_stats(team, league)
        }
    
    def get_standings(self, league: str) -> Dict[str, Any]:
        """
        Get league standings.
        
        Args:
            league: League code
        
        Returns:
            Standings data dictionary
        """
        return {
            "source": "espn_api",
            "data": schedule_api.get_standings(league)
        }
    
    def get_game_details(self, game_id: str, league: Optional[str] = None) -> Dict[str, Any]:
        """
        Get detailed game information.
        
        Args:
            game_id: Game/event ID
            league: Optional league code
        
        Returns:
            Game details dictionary
        """
        return {
            "source": "espn_api",
            "data": schedule_api.get_game_details(game_id, league)
        }
    
    def check_all_sources(self) -> Dict[str, Dict[str, Any]]:
        """
        Check status of all data sources.
        
        Returns:
            Dictionary with status of each source
        """
        return {
            "odds_api": odds_scraper.check_api_status(),
            "espn_api": schedule_api.check_api_status()
        }


def create_client() -> UnifiedDataClient:
    """
    Create a unified data client instance.
    
    Returns:
        UnifiedDataClient instance
    """
    return UnifiedDataClient()


SUPPORTED_LEAGUES = ["NBA", "NFL", "MLB", "NHL", "NCAAB", "NCAAF", "WNBA", "MLS"]


# ---------------------------------------------------------------------------
# Convenience functions used by the Agent orchestrator
# ---------------------------------------------------------------------------

import logging as _logging

_logger = _logging.getLogger("omega.free_sources")

# League-specific defaults for deriving off/def ratings from raw stats
_LEAGUE_DEFAULTS: Dict[str, Dict[str, float]] = {
    "NBA":   {"avg_pts": 112.0, "avg_pace": 100.0},
    "NCAAB": {"avg_pts": 72.0,  "avg_pace": 68.0},
    "WNBA":  {"avg_pts": 82.0,  "avg_pace": 78.0},
    "NFL":   {"avg_pts": 22.0,  "avg_pace": 12.0},
    "NCAAF": {"avg_pts": 28.0,  "avg_pace": 12.0},
    "MLB":   {"avg_pts": 4.5,   "avg_pace": 9.0},
    "NHL":   {"avg_pts": 3.1,   "avg_pace": 60.0},
}


def _raw_stats_to_context(raw: Dict[str, Any], team: str, league: str) -> Dict[str, Any]:
    """
    Convert raw scraped team stats into the engine's TeamContext dict format.

    The engine needs: name, league, off_rating, def_rating, pace.
    Scraped data varies by source; this function does best-effort mapping.
    """
    defaults = _LEAGUE_DEFAULTS.get(league.upper(), {"avg_pts": 100.0, "avg_pace": 70.0})
    stats_blob = raw.get("stats", {})

    # --- Offensive rating ---
    off = (
        stats_blob.get("pts_per_game")
        or raw.get("pts_per_game")
        or stats_blob.get("points_for")
        or defaults["avg_pts"]
    )

    # --- Defensive rating (points allowed) ---
    def_val = (
        stats_blob.get("pts_allowed_per_game")
        or stats_blob.get("points_against")
        or defaults["avg_pts"]
    )

    pace = stats_blob.get("pace") or defaults["avg_pace"]

    context: Dict[str, Any] = {
        "name": raw.get("name", team),
        "league": league.upper(),
        "off_rating": float(off),
        "def_rating": float(def_val),
        "pace": float(pace),
        "pts_per_game": float(off),
        "fg_pct": float(stats_blob.get("fg_pct", 0.45)),
        "three_pt_pct": float(stats_blob.get("fg3_pct", 0.35)),
    }

    # Carry through any sport-specific extras
    for k, v in stats_blob.items():
        if k not in context:
            context[k] = v

    return context


def get_team_stats_free(team: str, league: str) -> Optional[Dict[str, Any]]:
    """
    Fetch team stats from free sources and return in engine-ready dict format.

    Falls back through: stats_scraper → ESPN → None.
    """
    try:
        raw = stats_scraper.get_team_stats(team, league)
        if raw:
            return _raw_stats_to_context(raw, team, league)
    except Exception as exc:
        _logger.debug("stats_scraper.get_team_stats failed for %s/%s: %s", team, league, exc)

    return None


def get_odds_free(home: str, away: str, league: str) -> Optional[Dict[str, Any]]:
    """
    Fetch odds for a matchup and return in OddsInput-compatible dict format.

    Uses The Odds API (via odds_scraper) first; returns None if unavailable.
    """
    try:
        games = odds_scraper.get_upcoming_games(league)
    except Exception as exc:
        _logger.debug("odds_scraper.get_upcoming_games failed for %s: %s", league, exc)
        return None

    if not games:
        return None

    home_lower = home.lower()
    away_lower = away.lower()

    for game in games:
        g_home = game.get("home_team", "").lower()
        g_away = game.get("away_team", "").lower()

        # Fuzzy match: check if the search term is a substring
        if not ((home_lower in g_home or g_home in home_lower) and
                (away_lower in g_away or g_away in away_lower)):
            continue

        # Extract consensus odds from first bookmaker
        bookmakers = game.get("bookmakers", [])
        if not bookmakers:
            return None

        book = bookmakers[0]
        markets = book.get("markets", {})

        odds_dict: Dict[str, Any] = {}

        # Moneyline (h2h)
        h2h = markets.get("h2h", [])
        for outcome in h2h:
            name_lower = outcome.get("name", "").lower()
            if home_lower in name_lower or name_lower in g_home:
                odds_dict["moneyline_home"] = outcome.get("price")
            elif away_lower in name_lower or name_lower in g_away:
                odds_dict["moneyline_away"] = outcome.get("price")
            elif name_lower == "draw":
                odds_dict["moneyline_draw"] = outcome.get("price")

        # Spreads
        spreads = markets.get("spreads", [])
        for outcome in spreads:
            name_lower = outcome.get("name", "").lower()
            if home_lower in name_lower or name_lower in g_home:
                odds_dict["spread_home"] = outcome.get("point")
                odds_dict["spread_home_price"] = outcome.get("price", -110)
                break

        # Totals
        totals = markets.get("totals", [])
        for outcome in totals:
            if outcome.get("name", "").lower() == "over":
                odds_dict["over_under"] = outcome.get("point")
                break

        if odds_dict:
            return odds_dict

    return None


def get_supported_leagues() -> List[str]:
    """Get list of supported leagues."""
    return SUPPORTED_LEAGUES.copy()


def get_league_sources(league: str) -> Dict[str, List[str]]:
    """
    Get available data sources for a league.
    
    Args:
        league: League code
    
    Returns:
        Dictionary mapping data types to available sources
    """
    league = league.upper()
    
    sources = {
        "odds": ["odds_api", "espn_api"],
        "schedule": ["espn_api"],
        "standings": ["espn_api"],
        "live_scores": ["espn_api"]
    }
    
    if league in ["NBA", "NCAAB", "WNBA"]:
        sources["player_stats"] = ["basketball_reference", "espn_api"]
        sources["team_stats"] = ["basketball_reference", "espn_api"]
    elif league in ["NFL", "NCAAF"]:
        sources["player_stats"] = ["pro_football_reference", "espn_api"]
        sources["team_stats"] = ["pro_football_reference", "espn_api"]
    elif league == "MLB":
        sources["player_stats"] = ["baseball_reference", "espn_api"]
        sources["team_stats"] = ["baseball_reference", "espn_api"]
    elif league == "NHL":
        sources["player_stats"] = ["hockey_reference", "espn_api"]
        sources["team_stats"] = ["hockey_reference", "espn_api"]
    else:
        sources["player_stats"] = ["espn_api"]
        sources["team_stats"] = ["espn_api"]
    
    return sources
