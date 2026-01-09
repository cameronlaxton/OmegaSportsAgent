"""
Multi-source data aggregator for comprehensive sports statistics.

This module extends the historical data scraper to fetch data from multiple sources
beyond ESPN, including:
- ESPN API (game results, basic stats)
- Sports Reference (advanced statistics)
- The Odds API (historical betting lines)
- BallDontLie API (player statistics)
- Perplexity API (enrichment for missing/ambiguous data)
- OddsPortal/Covers (historical odds scraping)

Ensures comprehensive data collection with real, not mocked, statistics.
"""

import logging
import sqlite3
import hashlib
import json
import os
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
import requests
from pathlib import Path

logger = logging.getLogger(__name__)


class PerplexityCache:
    """
    SQLite-based cache for Perplexity API responses optimized for backtesting.
    
    Features:
    - Indexed on (player_name, game_date) for fast lookups during 10,000+ iteration backtests
    - Aggressive caching with 30-day TTL
    - Query hash-based deduplication
    - Sub-millisecond lookup performance
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize Perplexity cache with SQLite database.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path or Path("data/cache/perplexity.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = None
        self._initialize_database()
        logger.info(f"PerplexityCache initialized at {self.db_path}")
    
    def _initialize_database(self):
        """Create database schema with indexes."""
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        
        cursor = self.conn.cursor()
        
        # Create cache table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS perplexity_cache (
                query_hash TEXT PRIMARY KEY,
                player_name TEXT,
                game_date TEXT,
                prop_type TEXT,
                response_json TEXT,
                timestamp INTEGER,
                ttl INTEGER DEFAULT 2592000
            )
        """)
        
        # Create composite index for fast player+date lookups during backtesting
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_player_date 
            ON perplexity_cache(player_name, game_date)
        """)
        
        # Create index on timestamp for cleanup
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp 
            ON perplexity_cache(timestamp)
        """)
        
        self.conn.commit()
        logger.info("Perplexity cache database schema initialized")
    
    def get(
        self,
        query: str,
        player_name: Optional[str] = None,
        game_date: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached response for query.
        
        Args:
            query: Query string
            player_name: Optional player name for indexed lookup
            game_date: Optional game date for indexed lookup
        
        Returns:
            Cached response dictionary or None
        """
        query_hash = self._hash_query(query)
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT response_json, timestamp, ttl 
            FROM perplexity_cache 
            WHERE query_hash = ?
        """, (query_hash,))
        
        row = cursor.fetchone()
        
        if row:
            # Check if cache is still valid
            cached_time = row['timestamp']
            ttl = row['ttl']
            current_time = int(time.time())
            
            if current_time - cached_time <= ttl:
                response = json.loads(row['response_json'])
                logger.debug(f"Cache hit for query hash {query_hash[:8]}...")
                return response
            else:
                # Expired, delete it
                cursor.execute("DELETE FROM perplexity_cache WHERE query_hash = ?", (query_hash,))
                self.conn.commit()
                logger.debug(f"Cache expired for query hash {query_hash[:8]}...")
        
        return None
    
    def set(
        self,
        query: str,
        response: Dict[str, Any],
        player_name: Optional[str] = None,
        game_date: Optional[str] = None,
        prop_type: Optional[str] = None,
        ttl: int = 2592000  # 30 days default
    ):
        """
        Cache response for query.
        
        Args:
            query: Query string
            response: Response dictionary to cache
            player_name: Optional player name for indexing
            game_date: Optional game date for indexing
            prop_type: Optional prop type
            ttl: Time to live in seconds (default 30 days)
        """
        query_hash = self._hash_query(query)
        response_json = json.dumps(response)
        timestamp = int(time.time())
        
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO perplexity_cache 
            (query_hash, player_name, game_date, prop_type, response_json, timestamp, ttl)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (query_hash, player_name, game_date, prop_type, response_json, timestamp, ttl))
        
        self.conn.commit()
        logger.debug(f"Cached response for query hash {query_hash[:8]}...")
    
    def get_by_player_date(
        self,
        player_name: str,
        game_date: str,
        prop_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fast indexed lookup by player name and game date.
        
        Optimized for backtesting scenarios where we need all cached data
        for a specific player on a specific date.
        
        Args:
            player_name: Player name
            game_date: Game date in YYYY-MM-DD format
            prop_type: Optional prop type filter
        
        Returns:
            List of cached response dictionaries
        """
        cursor = self.conn.cursor()
        
        if prop_type:
            cursor.execute("""
                SELECT response_json, timestamp, ttl 
                FROM perplexity_cache 
                WHERE player_name = ? AND game_date = ? AND prop_type = ?
            """, (player_name, game_date, prop_type))
        else:
            cursor.execute("""
                SELECT response_json, timestamp, ttl 
                FROM perplexity_cache 
                WHERE player_name = ? AND game_date = ?
            """, (player_name, game_date))
        
        rows = cursor.fetchall()
        current_time = int(time.time())
        
        valid_responses = []
        expired_hashes = []
        
        for row in rows:
            cached_time = row['timestamp']
            ttl = row['ttl']
            
            if current_time - cached_time <= ttl:
                response = json.loads(row['response_json'])
                valid_responses.append(response)
            else:
                expired_hashes.append(row['query_hash'])
        
        # Clean up expired entries
        if expired_hashes:
            cursor.executemany(
                "DELETE FROM perplexity_cache WHERE query_hash = ?",
                [(h,) for h in expired_hashes]
            )
            self.conn.commit()
        
        return valid_responses
    
    def cleanup_expired(self):
        """Remove all expired cache entries."""
        current_time = int(time.time())
        
        cursor = self.conn.cursor()
        cursor.execute("""
            DELETE FROM perplexity_cache 
            WHERE timestamp + ttl < ?
        """, (current_time,))
        
        deleted = cursor.rowcount
        self.conn.commit()
        
        if deleted > 0:
            logger.info(f"Cleaned up {deleted} expired cache entries")
        
        return deleted
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as total FROM perplexity_cache")
        total = cursor.fetchone()['total']
        
        cursor.execute("""
            SELECT COUNT(*) as expired 
            FROM perplexity_cache 
            WHERE timestamp + ttl < ?
        """, (int(time.time()),))
        expired = cursor.fetchone()['expired']
        
        return {
            "total_entries": total,
            "valid_entries": total - expired,
            "expired_entries": expired,
            "cache_hit_rate": "N/A"  # Would need tracking
        }
    
    def _hash_query(self, query: str) -> str:
        """Generate hash for query string."""
        return hashlib.md5(query.encode('utf-8')).hexdigest()
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
    
    def __del__(self):
        """Cleanup on deletion."""
        self.close()


class MultiSourceAggregator:
    """
    Aggregates sports data from multiple sources to ensure comprehensive coverage.
    
    Sources:
    1. ESPN API - Primary game results and basic stats
    2. BallDontLie API - Player statistics and box scores
    3. The Odds API - Primary betting lines and odds
    4. OddsPortal - Historical odds scraping (fallback)
    5. Covers - Historical odds scraping (fallback)
    6. Perplexity API - Enrichment for missing/ambiguous data
    """
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize multi-source aggregator.
        
        Args:
            cache_dir: Directory for caching responses
        """
        self.cache_dir = Path(cache_dir) if cache_dir else Path("./data/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Perplexity cache
        self.perplexity_cache = PerplexityCache(
            db_path=self.cache_dir / "perplexity.db"
        )
        
        # Initialize API key for Perplexity
        self.perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")
        if not self.perplexity_api_key:
            logger.warning("PERPLEXITY_API_KEY not set - enrichment features limited")
        
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        
        # Track which sources are available
        self.available_sources = {
            "espn": True,
            "balldontlie": False,
            "odds_api": False,
            "perplexity": bool(self.perplexity_api_key),
            "oddsportal": True,
            "covers": True,
        }
        
        logger.info("MultiSourceAggregator initialized")
    
    def enrich_game_data(
        self,
        game: Dict[str, Any],
        fetch_advanced_stats: bool = True,
        fetch_player_stats: bool = True,
        fetch_odds_history: bool = True
    ) -> Dict[str, Any]:
        """
        Enrich game data with statistics from multiple sources.
        
        This ensures we get REAL, comprehensive data beyond basic ESPN results.
        
        Args:
            game: Base game data from ESPN
            fetch_advanced_stats: Whether to fetch advanced team statistics
            fetch_player_stats: Whether to fetch player-level statistics
            fetch_odds_history: Whether to fetch historical odds data
            
        Returns:
            Enriched game dictionary with comprehensive statistics
        """
        enriched = game.copy()
        
        # Try to fetch advanced statistics from additional sources
        if fetch_advanced_stats:
            advanced_stats = self._fetch_advanced_statistics(game)
            if advanced_stats:
                enriched["advanced_stats"] = advanced_stats
        
        # Try to fetch player-level statistics
        if fetch_player_stats:
            player_stats = self._fetch_player_statistics(game)
            if player_stats:
                enriched["player_stats"] = player_stats
        
        # Try to fetch historical odds data
        if fetch_odds_history:
            odds_history = self._fetch_odds_history(game)
            if odds_history:
                enriched["odds_history"] = odds_history
        
        return enriched
    
    def _fetch_advanced_statistics(self, game: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Fetch advanced statistics from Sports Reference or similar sources.
        
        This would include:
        - Offensive/Defensive ratings
        - Pace statistics
        - Four factors (eFG%, TO%, OR%, FT rate)
        - Player efficiency ratings
        - Plus/minus statistics
        
        Args:
            game: Base game data
            
        Returns:
            Dictionary of advanced statistics or None if unavailable
        """
        # TODO: Implement Sports Reference scraping
        # For now, return None to indicate this data source needs implementation
        
        # Example structure of what this would return:
        # return {
        #     "home_advanced": {
        #         "offensive_rating": 112.5,
        #         "defensive_rating": 108.3,
        #         "pace": 98.7,
        #         "effective_fg_pct": 0.545,
        #         "turnover_pct": 0.132,
        #         "offensive_rebound_pct": 0.287,
        #         "free_throw_rate": 0.245
        #     },
        #     "away_advanced": { ... }
        # }
        
        logger.debug(f"Advanced statistics not yet implemented for game {game.get('game_id')}")
        return None
    
    def _fetch_player_statistics(self, game: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch player-level statistics from BallDontLie box scores.
        
        Uses enhanced BallDontLie client with /v1/stats endpoint.
        
        Args:
            game: Base game data
            
        Returns:
            List of player stat dictionaries or None if unavailable
        """
        try:
            from src.balldontlie_client import BallDontLieAPIClient
            
            client = BallDontLieAPIClient()
            
            # Check if game already has BallDontLie game ID
            bdl_game_id = game.get("balldontlie_game_id")
            
            if not bdl_game_id:
                # Need to find matching game
                game_date = game.get("date")
                if not game_date:
                    logger.debug("No game date - cannot fetch player stats")
                    return None
                
                # Get games for this date
                bdl_games = client.get_games(game_date, game_date)
                
                if not bdl_games:
                    logger.debug(f"No BallDontLie games found for {game_date}")
                    return None
                
                # Match by team names
                home_team = game.get("home_team", "").lower()
                away_team = game.get("away_team", "").lower()
                
                for bdl_game in bdl_games:
                    bdl_home = bdl_game.get("home_team", {}).get("full_name", "").lower()
                    bdl_away = bdl_game.get("visitor_team", {}).get("full_name", "").lower()
                    
                    if (home_team in bdl_home or bdl_home in home_team) and \
                       (away_team in bdl_away or bdl_away in away_team):
                        bdl_game_id = bdl_game.get("id")
                        break
            
            if not bdl_game_id:
                logger.debug("Could not match game to BallDontLie")
                return None
            
            # Fetch box score
            box_score = client.get_box_score(bdl_game_id)
            
            if box_score:
                logger.info(f"✓ Fetched player stats for game {bdl_game_id}")
                return box_score.get("player_stats", [])
            
        except Exception as e:
            logger.error(f"Error fetching player statistics: {e}")
        
        return None
    
    def _fetch_odds_history(self, game: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Fetch historical odds with smart fallback: Odds API (primary) -> scrapers (fallback).
        
        Prioritizes The Odds API, uses OddsPortal/Covers only for gaps.
        
        Args:
            game: Base game data
            
        Returns:
            Dictionary of odds history or None if unavailable
        """
        game_date = game.get("date")
        sport = game.get("sport")
        
        if not game_date or not sport:
            logger.debug("Missing date or sport for odds fetch")
            return None
        
        odds_data = None
        
        # Primary: Try The Odds API
        try:
            from src.odds_api_client import TheOddsAPIClient
            
            odds_client = TheOddsAPIClient()
            odds_games = odds_client.get_historical_odds(sport, game_date)
            
            if odds_games:
                # Find matching game by team names
                home_team = game.get("home_team", "").lower()
                away_team = game.get("away_team", "").lower()
                
                for odds_game in odds_games:
                    odds_home = odds_game.get("home_team", "").lower()
                    odds_away = odds_game.get("away_team", "").lower()
                    
                    if (home_team in odds_home or odds_home in home_team) and \
                       (away_team in odds_away or odds_away in away_team):
                        odds_data = odds_game
                        logger.info(f"✓ Fetched odds from The Odds API")
                        break
        except Exception as e:
            logger.debug(f"The Odds API fetch failed: {e}")
        
        # Fallback: Use scrapers only if Odds API had no data
        if not odds_data:
            odds_data = self._fetch_odds_from_scrapers(sport, game_date, game)
        
        return odds_data
    
    def _fetch_odds_from_scrapers(
        self,
        sport: str,
        date: str,
        game: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch odds from bot-friendly scraper sources as fallback.
        
        Args:
            sport: Sport name
            date: Date in YYYY-MM-DD format
            game: Game data for matching
        
        Returns:
            Odds dictionary or None
        """
        try:
            from src.historical_scrapers import OddsPortalScraper, CoversOddsHistoryScraper
            
            home_team = game.get("home_team", "").lower()
            away_team = game.get("away_team", "").lower()
            
            # Try OddsPortal first
            try:
                oddsportal = OddsPortalScraper()
                scraped_games = oddsportal.scrape_game_odds(sport, date)
                
                for scraped_game in scraped_games:
                    scraped_home = scraped_game.get("home_team", "").lower()
                    scraped_away = scraped_game.get("away_team", "").lower()
                    
                    if (home_team in scraped_home or scraped_home in home_team) and \
                       (away_team in scraped_away or scraped_away in away_team):
                        logger.info(f"✓ Fetched odds from OddsPortal (fallback)")
                        return scraped_game
            except Exception as e:
                logger.debug(f"OddsPortal scraping failed: {e}")
            
            # Try Covers as final fallback
            try:
                covers = CoversOddsHistoryScraper()
                scraped_games = covers.scrape_game_odds(sport, date)
                
                for scraped_game in scraped_games:
                    scraped_home = scraped_game.get("home_team", "").lower()
                    scraped_away = scraped_game.get("away_team", "").lower()
                    
                    if (home_team in scraped_home or scraped_home in home_team) and \
                       (away_team in scraped_away or scraped_away in away_team):
                        logger.info(f"✓ Fetched odds from Covers (fallback)")
                        return scraped_game
            except Exception as e:
                logger.debug(f"Covers scraping failed: {e}")
            
        except Exception as e:
            logger.error(f"Error in scraper fallback: {e}")
        
        logger.warning(f"No odds found for game on {date}")
        return None
    
    def _query_perplexity(
        self,
        query: str,
        use_cache: bool = True,
        player_name: Optional[str] = None,
        game_date: Optional[str] = None,
        prop_type: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Query Perplexity API with aggressive caching.
        
        Only called for missing/ambiguous data enrichment.
        
        Args:
            query: Query string
            use_cache: Whether to use cache (default True)
            player_name: Optional player name for indexing
            game_date: Optional game date for indexing
            prop_type: Optional prop type
        
        Returns:
            Response dictionary or None
        """
        if not self.perplexity_api_key:
            logger.debug("No Perplexity API key - skipping enrichment")
            return None
        
        # Check cache first
        if use_cache:
            cached = self.perplexity_cache.get(query, player_name, game_date)
            if cached:
                return cached
        
        # Make API request
        try:
            url = "https://api.perplexity.ai/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.perplexity_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "llama-3.1-sonar-small-128k-online",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a sports data assistant. Provide accurate, concise answers with data sources."
                    },
                    {
                        "role": "user",
                        "content": query
                    }
                ]
            }
            
            response = self.session.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Cache the response
            if use_cache:
                self.perplexity_cache.set(
                    query=query,
                    response=data,
                    player_name=player_name,
                    game_date=game_date,
                    prop_type=prop_type
                )
            
            logger.info(f"✓ Fetched enrichment from Perplexity")
            return data
            
        except Exception as e:
            logger.error(f"Error querying Perplexity: {e}")
            return None
    
    def _integrate_perplexity(
        self,
        game: Dict[str, Any],
        missing_fields: List[str]
    ) -> Dict[str, Any]:
        """
        Use Perplexity to enrich missing or ambiguous game data.
        
        Only called when critical data is missing from primary sources.
        
        Args:
            game: Game data dictionary
            missing_fields: List of missing field names
        
        Returns:
            Enriched game dictionary
        """
        if not missing_fields:
            return game
        
        enriched = game.copy()
        
        for field in missing_fields:
            # Construct targeted query for missing data
            if field == "player_injury":
                query = f"Was {game.get('player_name')} injured on {game.get('date')}?"
            elif field == "lineup_change":
                query = f"Did {game.get('home_team')} vs {game.get('away_team')} on {game.get('date')} have lineup changes?"
            else:
                query = f"What is the {field} for {game.get('home_team')} vs {game.get('away_team')} on {game.get('date')}?"
            
            response = self._query_perplexity(
                query=query,
                player_name=game.get("player_name"),
                game_date=game.get("date")
            )
            
            if response:
                # Extract relevant data from response
                content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
                enriched[f"{field}_perplexity"] = content
        
        return enriched
    
    def verify_data_completeness(self, game: Dict[str, Any]) -> Dict[str, bool]:
        """
        Verify completeness of data to ensure we're not using mocked/sample data.
        
        Args:
            game: Game data to verify
            
        Returns:
            Dictionary indicating which data fields are present and valid
        """
        completeness = {
            "has_basic_info": all(k in game for k in [
                "game_id", "date", "sport", "home_team", "away_team"
            ]),
            "has_final_score": all(k in game for k in ["home_score", "away_score"]),
            "has_team_stats": "home_team_stats" in game and "away_team_stats" in game,
            "has_betting_lines": "moneyline" in game or "spread" in game or "total" in game,
            "has_venue_info": "venue" in game,
            "has_real_scores": (
                game.get("home_score", 0) > 0 and 
                game.get("away_score", 0) > 0 and
                game.get("status") == "final"
            ),
        }
        
        # Check for obviously mocked data patterns
        completeness["appears_real"] = (
            completeness["has_real_scores"] and
            completeness["has_basic_info"] and
            game.get("game_id", "").strip() != "" and
            game.get("home_team") != game.get("away_team")
        )
        
        return completeness
    
    def get_data_source_priority(self, sport: str, data_type: str) -> List[str]:
        """
        Get prioritized list of data sources for a given sport and data type.
        
        Args:
            sport: Sport name (NBA, NFL, etc.)
            data_type: Type of data needed (game_results, team_stats, player_stats, etc.)
            
        Returns:
            List of source names in priority order
        """
        # Define source priorities by sport and data type
        priorities = {
            "NBA": {
                "game_results": ["espn", "sports_reference"],
                "team_stats": ["espn", "sports_reference"],
                "player_stats": ["espn", "sports_reference"],
                "betting_lines": ["espn", "odds_api"],
                "advanced_stats": ["sports_reference"],
            },
            "NFL": {
                "game_results": ["espn", "sports_reference"],
                "team_stats": ["espn", "sports_reference"],
                "player_stats": ["espn", "sports_reference"],
                "betting_lines": ["espn", "odds_api"],
                "advanced_stats": ["sports_reference"],
            },
            "NCAAB": {
                "game_results": ["espn", "sports_reference"],
                "team_stats": ["espn", "sports_reference"],
                "player_stats": ["espn"],
                "betting_lines": ["espn"],
                "advanced_stats": ["sports_reference"],
            },
            "NCAAF": {
                "game_results": ["espn", "sports_reference"],
                "team_stats": ["espn", "sports_reference"],
                "player_stats": ["espn"],
                "betting_lines": ["espn"],
                "advanced_stats": ["sports_reference"],
            },
        }
        
        return priorities.get(sport, {}).get(data_type, ["espn"])
    
    def get_available_sources_status(self) -> Dict[str, bool]:
        """
        Get status of which data sources are currently available.
        
        Returns:
            Dictionary mapping source names to availability status
        """
        return self.available_sources.copy()


def validate_not_sample_data(game: Dict[str, Any]) -> bool:
    """
    Validate that game data is real, not sample/mocked data.
    
    Checks for:
    - Valid game IDs (not placeholder values)
    - Realistic scores
    - Real team names
    - Actual dates
    - Non-default values
    
    Args:
        game: Game data to validate
        
    Returns:
        True if data appears to be real, False if it appears to be sample/mocked
    """
    # Check for placeholder/sample indicators
    sample_indicators = [
        "sample", "test", "mock", "fake", "example", "demo",
        "placeholder", "xxx", "tbd", "n/a"
    ]
    
    game_id = str(game.get("game_id", "")).lower()
    home_team = str(game.get("home_team", "")).lower()
    away_team = str(game.get("away_team", "")).lower()
    
    # Check for sample indicators in key fields
    for indicator in sample_indicators:
        if (indicator in game_id or 
            indicator in home_team or 
            indicator in away_team):
            logger.warning(f"Game appears to be sample data: {game_id}")
            return False
    
    # Check for valid scores
    home_score = game.get("home_score", 0)
    away_score = game.get("away_score", 0)
    
    if home_score == 0 and away_score == 0 and game.get("status") == "final":
        logger.warning(f"Game has 0-0 final score (likely invalid): {game_id}")
        return False
    
    # Check for valid date
    try:
        game_date = datetime.fromisoformat(game.get("date", ""))
        current_year = datetime.now().year
        
        # Reject dates too far in future or past
        if game_date.year < 2000 or game_date.year > current_year + 1:
            logger.warning(f"Game has invalid year: {game_date.year}")
            return False
    except (ValueError, TypeError):
        logger.warning(f"Game has invalid date format: {game.get('date')}")
        return False
    
    # All checks passed
    return True
