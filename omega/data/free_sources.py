"""
Free Data Sources Catalog

Documentation of available free APIs and their limits.
Provides unified interface for data access.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from omega.data import odds_scraper, stats_scraper, schedule_api


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
