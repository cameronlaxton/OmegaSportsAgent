"""
Enhanced Historical Data Scraper for OmegaSports Validation Lab.

This module provides comprehensive data scraping beyond ESPN's scheduler API,
including historical game data, player statistics, team statistics, and advanced metrics.

Supports multiple data sources and comprehensive statistics collection for:
- NBA, NFL, NCAAB, NCAAF (2020-2024)
- Game results with scores
- Player statistics and props
- Team statistics
- Advanced metrics and analytics
"""

import logging
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import requests
from urllib.parse import urljoin
from core.multi_source_aggregator import MultiSourceAggregator, validate_not_sample_data

logger = logging.getLogger(__name__)


@dataclass
class GameStatistics:
    """Comprehensive game statistics."""
    game_id: str
    date: str
    sport: str
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    # Betting lines
    moneyline_home: Optional[float] = None
    moneyline_away: Optional[float] = None
    spread_line: Optional[float] = None
    spread_odds_home: Optional[float] = None
    spread_odds_away: Optional[float] = None
    total_line: Optional[float] = None
    over_odds: Optional[float] = None
    under_odds: Optional[float] = None
    # Team statistics
    home_team_stats: Optional[Dict[str, Any]] = None
    away_team_stats: Optional[Dict[str, Any]] = None
    # Player statistics  
    player_stats: Optional[List[Dict[str, Any]]] = None


class HistoricalDataScraper:
    """
    Enhanced scraper for historical sports data with comprehensive statistics.
    
    Goes beyond ESPN scheduler API to fetch:
    - Historical game results (2020-2024)
    - Complete player statistics
    - Team statistics and advanced metrics
    - Betting lines and odds
    """
    
    # ESPN API endpoints for historical data
    ESPN_BASE_URL = "https://site.api.espn.com/apis/site/v2/sports"
    
    # Game status constants
    COMPLETED_GAME_STATUS = "post"
    
    # Default betting odds when actual odds not available
    DEFAULT_ODDS = -110
    
    # Sport configurations
    SPORT_CONFIG = {
        "NBA": {
            "espn_path": "basketball/nba",
            "season_start_month": 10,  # October
            "season_end_month": 6,     # June
            "approx_games_per_season": 1230,  # 30 teams * 82 games / 2
        },
        "NFL": {
            "espn_path": "football/nfl",
            "season_start_month": 9,   # September  
            "season_end_month": 2,     # February
            "approx_games_per_season": 285,  # Regular + Playoffs
        },
        "NCAAB": {
            "espn_path": "basketball/mens-college-basketball",
            "season_start_month": 11,  # November
            "season_end_month": 4,     # April
            "approx_games_per_season": 5000,  # Many teams, many games
        },
        "NCAAF": {
            "espn_path": "football/college-football",
            "season_start_month": 8,   # August
            "season_end_month": 1,     # January
            "approx_games_per_season": 800,  # Bowl games + regular season
        },
    }
    
    def __init__(self, cache_dir: Optional[Path] = None, enable_multi_source: bool = True):
        """
        Initialize historical data scraper.
        
        Args:
            cache_dir: Directory for caching API responses
            enable_multi_source: Enable multi-source data aggregation for enhanced statistics (default: True)
        """
        self.cache_dir = Path(cache_dir) if cache_dir else Path("./data/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        
        # Initialize multi-source aggregator (enabled by default)
        self.enable_multi_source = enable_multi_source
        self.aggregator = MultiSourceAggregator(cache_dir=cache_dir) if enable_multi_source else None
        
        # Statistics tracking
        self.stats = {
            "total_games_fetched": 0,
            "games_with_full_stats": 0,
            "games_failed_validation": 0,
            "api_calls_made": 0,
            "cache_hits": 0,
        }
        
        logger.info(f"HistoricalDataScraper initialized with cache_dir={self.cache_dir}, multi_source={enable_multi_source}")
    
    def fetch_historical_games(
        self,
        sport: str,
        start_year: int,
        end_year: int,
        max_retries: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Fetch comprehensive historical game data for a sport and year range.
        
        Args:
            sport: Sport name (NBA, NFL, NCAAB, NCAAF)
            start_year: Start year (inclusive)
            end_year: End year (inclusive)
            max_retries: Maximum number of retry attempts per request
            
        Returns:
            List of game dictionaries with comprehensive statistics
        """
        if sport not in self.SPORT_CONFIG:
            raise ValueError(f"Unsupported sport: {sport}. Must be one of {list(self.SPORT_CONFIG.keys())}")
        
        logger.info(f"Fetching historical games for {sport} ({start_year}-{end_year})")
        all_games = []
        
        for year in range(start_year, end_year + 1):
            logger.info(f"Processing {sport} season {year}")
            games = self._fetch_season_games(sport, year, max_retries)
            all_games.extend(games)
            logger.info(f"  Fetched {len(games)} games for {year} season")
            
            # Rate limiting
            time.sleep(0.5)
        
        logger.info(f"Total games fetched for {sport}: {len(all_games)}")
        logger.info(f"Scraper statistics: {self.stats}")
        return all_games
    
    def _fetch_season_games(
        self,
        sport: str,
        year: int,
        max_retries: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Fetch all games for a specific sport season.
        
        Args:
            sport: Sport name
            year: Season year
            max_retries: Maximum retry attempts
            
        Returns:
            List of game dictionaries
        """
        config = self.SPORT_CONFIG[sport]
        games = []
        
        # Generate date range for season
        season_start = datetime(year, config["season_start_month"], 1)
        if config["season_end_month"] < config["season_start_month"]:
            # Season spans into next year
            season_end = datetime(year + 1, config["season_end_month"], 28)
        else:
            season_end = datetime(year, config["season_end_month"], 28)
        
        # Fetch games in chunks (weekly or monthly depending on sport)
        current_date = season_start
        chunk_days = 7 if sport in ["NBA", "NCAAB"] else 30  # Weekly for basketball, monthly for football
        
        while current_date <= season_end:
            chunk_end = min(current_date + timedelta(days=chunk_days), season_end)
            
            # Try to fetch from cache first
            cache_key = f"{sport}_{current_date.strftime('%Y%m%d')}_{chunk_end.strftime('%Y%m%d')}"
            cached_data = self._get_from_cache(cache_key)
            if cached_data:
                games.extend(cached_data)
                self.stats["cache_hits"] += 1
            else:
                # Fetch from API with retries
                chunk_games = self._fetch_games_chunk(
                    sport, current_date, chunk_end, max_retries
                )
                
                # Validate that we're getting real data, not mocked
                validated_games = []
                for game in chunk_games:
                    if validate_not_sample_data(game):
                        # Optionally enrich with multi-source data
                        if self.enable_multi_source and self.aggregator:
                            game = self.aggregator.enrich_game_data(
                                game,
                                fetch_advanced_stats=True,
                                fetch_player_stats=True,
                                fetch_odds_history=True
                            )
                            if game.get("advanced_stats") or game.get("player_stats"):
                                self.stats["games_with_full_stats"] += 1
                        
                        validated_games.append(game)
                        self.stats["total_games_fetched"] += 1
                    else:
                        self.stats["games_failed_validation"] += 1
                        logger.warning(f"Game failed validation (appears to be sample data): {game.get('game_id')}")
                
                games.extend(validated_games)
                self._save_to_cache(cache_key, validated_games)
                self.stats["api_calls_made"] += 1
            
            current_date = chunk_end + timedelta(days=1)
            time.sleep(0.3)  # Rate limiting
        
        return games
    
    def _fetch_games_chunk(
        self,
        sport: str,
        start_date: datetime,
        end_date: datetime,
        max_retries: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Fetch games for a specific date range from ESPN API.
        
        Note: Returns actual game data from ESPN API, including comprehensive
        statistics when available. Data completeness varies by game and sport.
        
        Args:
            sport: Sport name
            start_date: Start date
            end_date: End date
            max_retries: Maximum retry attempts
            
        Returns:
            List of game dictionaries with available comprehensive data
        """
        config = self.SPORT_CONFIG[sport]
        games = []
        
        # Construct ESPN API URL for scoreboard
        url = f"{self.ESPN_BASE_URL}/{config['espn_path']}/scoreboard"
        
        # Try each day in the range
        current = start_date
        while current <= end_date:
            date_str = current.strftime("%Y%m%d")
            params = {"dates": date_str}
            
            for attempt in range(max_retries):
                try:
                    response = self.session.get(url, params=params, timeout=10)
                    response.raise_for_status()
                    data = response.json()
                    
                    # Parse ESPN API response
                    if "events" in data:
                        for event in data.get("events", []):
                            game = self._parse_espn_event(event, sport)
                            if game:
                                games.append(game)
                    
                    break  # Success
                    
                except Exception as e:
                    logger.warning(f"Attempt {attempt + 1}/{max_retries} failed for {date_str}: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                    else:
                        logger.error(f"Failed to fetch data for {date_str} after {max_retries} attempts")
            
            current += timedelta(days=1)
            time.sleep(0.2)  # Rate limiting
        
        return games
    
    def _parse_espn_event(self, event: Dict[str, Any], sport: str) -> Optional[Dict[str, Any]]:
        """
        Parse ESPN API event into standardized game format with comprehensive stats.
        
        Args:
            event: ESPN event data
            sport: Sport name
            
        Returns:
            Parsed game dictionary or None if invalid
        """
        try:
            # Extract basic game info
            game_id = event.get("id", "")
            date = event.get("date", "")
            status = event.get("status", {}).get("type", {}).get("state", "")
            
            # Only process completed games with actual results
            if status != self.COMPLETED_GAME_STATUS:
                return None
            
            competitions = event.get("competitions", [])
            if not competitions:
                return None
            
            competition = competitions[0]
            competitors = competition.get("competitors", [])
            
            if len(competitors) != 2:
                return None
            
            # Identify home and away teams
            home_team = None
            away_team = None
            for comp in competitors:
                if comp.get("homeAway") == "home":
                    home_team = comp
                else:
                    away_team = comp
            
            if not home_team or not away_team:
                return None
            
            # Extract scores
            home_score = int(home_team.get("score", 0))
            away_score = int(away_team.get("score", 0))
            
            # Extract team names
            home_name = home_team.get("team", {}).get("displayName", "")
            away_name = away_team.get("team", {}).get("displayName", "")
            
            # Extract odds/lines if available
            odds = competition.get("odds", [])
            odds_data = odds[0] if odds else {}
            
            # Build comprehensive game data
            game = {
                "game_id": game_id,
                "date": datetime.fromisoformat(date.replace("Z", "+00:00")).strftime("%Y-%m-%d"),
                "sport": sport,
                "league": sport,
                "home_team": home_name,
                "away_team": away_name,
                "home_score": home_score,
                "away_score": away_score,
                "status": "final",
            }
            
            # Add betting lines if available
            if odds_data:
                game["moneyline"] = {
                    "home": odds_data.get("homeMoneyLine"),
                    "away": odds_data.get("awayMoneyLine"),
                }
                game["spread"] = {
                    "line": odds_data.get("spread"),
                    "home_odds": odds_data.get("homeSpreadOdds"),
                    "away_odds": odds_data.get("awaySpreadOdds"),
                }
                game["total"] = {
                    "line": odds_data.get("overUnder"),
                    "over_odds": self.DEFAULT_ODDS,
                    "under_odds": self.DEFAULT_ODDS,
                }
            
            # Add team statistics if available
            home_stats = home_team.get("statistics", [])
            away_stats = away_team.get("statistics", [])
            
            if home_stats:
                game["home_team_stats"] = self._parse_team_stats(home_stats, sport)
            if away_stats:
                game["away_team_stats"] = self._parse_team_stats(away_stats, sport)
            
            # Add additional metadata
            game["venue"] = competition.get("venue", {}).get("fullName", "")
            game["attendance"] = competition.get("attendance", 0)
            
            return game
            
        except Exception as e:
            logger.warning(f"Error parsing ESPN event: {e}")
            return None
    
    def _parse_team_stats(self, stats_list: List[Dict[str, Any]], sport: str) -> Dict[str, Any]:
        """
        Parse team statistics from ESPN format.
        
        Args:
            stats_list: List of statistics from ESPN
            sport: Sport name
            
        Returns:
            Dictionary of parsed statistics
        """
        stats = {}
        for stat in stats_list:
            name = stat.get("name", "")
            value = stat.get("displayValue", "")
            stats[name] = value
        return stats
    
    def _get_from_cache(self, key: str) -> Optional[List[Dict[str, Any]]]:
        """Get data from cache if available and not expired."""
        cache_file = self.cache_dir / f"hist_{key}.json"
        if not cache_file.exists():
            return None
        
        try:
            # Check if cache is older than 30 days
            file_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
            if file_age > timedelta(days=30):
                logger.debug(f"Cache expired: {key}")
                return None
            
            with open(cache_file, "r") as f:
                data = json.load(f)
            logger.debug(f"Cache hit: {key}")
            return data
        except Exception as e:
            logger.warning(f"Error reading cache {key}: {e}")
            return None
    
    def _save_to_cache(self, key: str, data: List[Dict[str, Any]]) -> None:
        """Save data to cache."""
        cache_file = self.cache_dir / f"hist_{key}.json"
        try:
            with open(cache_file, "w") as f:
                json.dump(data, f, default=str)
            logger.debug(f"Saved to cache: {key}")
        except Exception as e:
            logger.warning(f"Error writing cache {key}: {e}")
    
    def get_season_summary(self, sport: str, year: int) -> Dict[str, Any]:
        """
        Get summary statistics for a season.
        
        Args:
            sport: Sport name
            year: Season year
            
        Returns:
            Dictionary with season summary
        """
        games = self._fetch_season_games(sport, year)
        
        return {
            "sport": sport,
            "year": year,
            "total_games": len(games),
            "teams": len(set([g["home_team"] for g in games] + [g["away_team"] for g in games])),
            "date_range": {
                "start": min([g["date"] for g in games]) if games else None,
                "end": max([g["date"] for g in games]) if games else None,
            },
            "data_quality": {
                "total_fetched": self.stats["total_games_fetched"],
                "with_full_stats": self.stats["games_with_full_stats"],
                "failed_validation": self.stats["games_failed_validation"],
                "api_calls": self.stats["api_calls_made"],
                "cache_hits": self.stats["cache_hits"],
            }
        }
