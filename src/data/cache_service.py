"""
Data Cache Service

Caches sports data in PostgreSQL for fast pipeline reads.
Uses psycopg2 with connection pooling for efficient database access.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor, Json

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")

NBA_TEAMS = [
    "Atlanta Hawks", "Boston Celtics", "Brooklyn Nets", "Charlotte Hornets",
    "Chicago Bulls", "Cleveland Cavaliers", "Dallas Mavericks", "Denver Nuggets",
    "Detroit Pistons", "Golden State Warriors", "Houston Rockets", "Indiana Pacers",
    "LA Clippers", "Los Angeles Lakers", "Memphis Grizzlies", "Miami Heat",
    "Milwaukee Bucks", "Minnesota Timberwolves", "New Orleans Pelicans", "New York Knicks",
    "Oklahoma City Thunder", "Orlando Magic", "Philadelphia 76ers", "Phoenix Suns",
    "Portland Trail Blazers", "Sacramento Kings", "San Antonio Spurs", "Toronto Raptors",
    "Utah Jazz", "Washington Wizards"
]

NFL_TEAMS = [
    "Arizona Cardinals", "Atlanta Falcons", "Baltimore Ravens", "Buffalo Bills",
    "Carolina Panthers", "Chicago Bears", "Cincinnati Bengals", "Cleveland Browns",
    "Dallas Cowboys", "Denver Broncos", "Detroit Lions", "Green Bay Packers",
    "Houston Texans", "Indianapolis Colts", "Jacksonville Jaguars", "Kansas City Chiefs",
    "Las Vegas Raiders", "Los Angeles Chargers", "Los Angeles Rams", "Miami Dolphins",
    "Minnesota Vikings", "New England Patriots", "New Orleans Saints", "New York Giants",
    "New York Jets", "Philadelphia Eagles", "Pittsburgh Steelers", "San Francisco 49ers",
    "Seattle Seahawks", "Tampa Bay Buccaneers", "Tennessee Titans", "Washington Commanders"
]

LEAGUE_TEAMS = {
    "NBA": NBA_TEAMS,
    "NFL": NFL_TEAMS,
}


class DataCacheService:
    """
    Service for caching sports data in PostgreSQL.
    
    Provides methods to cache and retrieve team stats, odds, and injury data
    with configurable TTL (time-to-live) for automatic expiration.
    """
    
    def __init__(self, min_conn: int = 1, max_conn: int = 5):
        """
        Initialize the cache service with connection pooling.
        
        Args:
            min_conn: Minimum number of connections in the pool
            max_conn: Maximum number of connections in the pool
        """
        self._pool: Optional[pool.SimpleConnectionPool] = None
        self._min_conn = min_conn
        self._max_conn = max_conn
        self._init_pool()
    
    def _init_pool(self) -> None:
        """Initialize the connection pool."""
        if not DATABASE_URL:
            logger.error("DATABASE_URL environment variable not set")
            return
        
        try:
            self._pool = pool.SimpleConnectionPool(
                self._min_conn,
                self._max_conn,
                DATABASE_URL
            )
            logger.info("Database connection pool initialized")
        except Exception as e:
            logger.error(f"Failed to initialize connection pool: {e}")
            self._pool = None
    
    def _get_conn(self):
        """Get a connection from the pool."""
        if self._pool is None:
            self._init_pool()
        if self._pool is None:
            raise RuntimeError("Database connection pool not available")
        return self._pool.getconn()
    
    def _put_conn(self, conn) -> None:
        """Return a connection to the pool."""
        if self._pool is not None and conn is not None:
            self._pool.putconn(conn)
    
    def close(self) -> None:
        """Close all connections in the pool."""
        if self._pool is not None:
            self._pool.closeall()
            self._pool = None
            logger.info("Database connection pool closed")
    
    def get_cached(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached data if not expired.
        
        Args:
            key: The cache key to look up
            
        Returns:
            Cached data dictionary if found and not expired, None otherwise
        """
        conn = None
        try:
            conn = self._get_conn()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT data, fetched_at, expires_at
                    FROM data_cache
                    WHERE cache_key = %s AND expires_at > NOW()
                    """,
                    (key,)
                )
                row = cur.fetchone()
                if row:
                    logger.debug(f"Cache hit for key: {key}")
                    return dict(row["data"]) if row["data"] else None
                logger.debug(f"Cache miss for key: {key}")
                return None
        except Exception as e:
            logger.error(f"Error retrieving cache for key {key}: {e}")
            return None
        finally:
            self._put_conn(conn)
    
    def set_cached(self, key: str, data: Dict[str, Any], ttl_hours: int = 6) -> bool:
        """
        Store data in cache with expiration.
        
        Args:
            key: The cache key
            data: Dictionary of data to cache
            ttl_hours: Time-to-live in hours (default 6)
            
        Returns:
            True if successfully cached, False otherwise
        """
        conn = None
        try:
            conn = self._get_conn()
            now = datetime.utcnow()
            expires_at = now + timedelta(hours=ttl_hours)
            
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO data_cache (cache_key, data, fetched_at, expires_at, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (cache_key) DO UPDATE SET
                        data = EXCLUDED.data,
                        fetched_at = EXCLUDED.fetched_at,
                        expires_at = EXCLUDED.expires_at,
                        updated_at = EXCLUDED.updated_at
                    """,
                    (key, Json(data), now, expires_at, now, now)
                )
            conn.commit()
            logger.debug(f"Cached data for key: {key}, expires: {expires_at}")
            return True
        except Exception as e:
            logger.error(f"Error caching data for key {key}: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            self._put_conn(conn)
    
    def refresh_team_stats(self, league: str) -> Dict[str, Any]:
        """
        Fetch team stats from stats_ingestion and cache them.
        
        Args:
            league: League code (e.g., "NBA", "NFL")
            
        Returns:
            Dictionary with refresh results including cached teams and any errors
        """
        from src.data import stats_ingestion
        
        league = league.upper()
        teams = LEAGUE_TEAMS.get(league, [])
        today = datetime.now().strftime("%Y-%m-%d")
        
        result = {
            "league": league,
            "teams_cached": 0,
            "teams_failed": 0,
            "errors": [],
            "refreshed_at": datetime.utcnow().isoformat()
        }
        
        all_teams_data = {}
        
        for team_name in teams:
            try:
                team_context = stats_ingestion.get_team_context(team_name, league)
                if team_context:
                    team_data = team_context.to_dict()
                    team_data["fetched_at"] = datetime.utcnow().isoformat()
                    
                    cache_key = f"team_stats:{league}:{team_name}"
                    if self.set_cached(cache_key, team_data):
                        result["teams_cached"] += 1
                        all_teams_data[team_name] = team_data
                    else:
                        result["teams_failed"] += 1
                        result["errors"].append(f"Failed to cache {team_name}")
                else:
                    result["teams_failed"] += 1
                    result["errors"].append(f"No data for {team_name}")
            except Exception as e:
                result["teams_failed"] += 1
                result["errors"].append(f"{team_name}: {str(e)}")
                logger.error(f"Error refreshing team stats for {team_name}: {e}")
        
        if all_teams_data:
            all_key = f"team_stats:{league}:all"
            all_data = {
                "league": league,
                "teams": all_teams_data,
                "count": len(all_teams_data),
                "fetched_at": datetime.utcnow().isoformat()
            }
            self.set_cached(all_key, all_data)
        
        logger.info(f"Team stats refresh for {league}: {result['teams_cached']} cached, {result['teams_failed']} failed")
        return result
    
    def refresh_odds(self, league: str) -> Dict[str, Any]:
        """
        Fetch odds from odds_scraper and cache them.
        
        Args:
            league: League code (e.g., "NBA", "NFL")
            
        Returns:
            Dictionary with refresh results including games count and any errors
        """
        from src.data import odds_scraper
        
        league = league.upper()
        today = datetime.now().strftime("%Y-%m-%d")
        
        result = {
            "league": league,
            "games_cached": 0,
            "error": None,
            "refreshed_at": datetime.utcnow().isoformat()
        }
        
        try:
            games = odds_scraper.get_upcoming_games(league)
            
            if games:
                cache_key = f"odds:{league}:{today}"
                odds_data = {
                    "league": league,
                    "date": today,
                    "games": games,
                    "count": len(games),
                    "fetched_at": datetime.utcnow().isoformat()
                }
                
                if self.set_cached(cache_key, odds_data):
                    result["games_cached"] = len(games)
                else:
                    result["error"] = "Failed to cache odds data"
            else:
                result["error"] = "No games found"
                
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Error refreshing odds for {league}: {e}")
        
        logger.info(f"Odds refresh for {league}: {result['games_cached']} games cached")
        return result
    
    def refresh_injuries(self, league: str) -> Dict[str, Any]:
        """
        Fetch injuries from injury_api and cache them.
        
        Args:
            league: League code (e.g., "NBA", "NFL")
            
        Returns:
            Dictionary with refresh results including injury count and any errors
        """
        from src.data import injury_api
        
        league = league.upper()
        today = datetime.now().strftime("%Y-%m-%d")
        
        result = {
            "league": league,
            "injuries_cached": 0,
            "error": None,
            "refreshed_at": datetime.utcnow().isoformat()
        }
        
        try:
            injuries_data = injury_api.get_injuries(league, use_cache=False)
            injured_players = injury_api.get_injured_players(league)
            
            cache_key = f"injuries:{league}:{today}"
            cache_data = {
                "league": league,
                "date": today,
                "raw_data": injuries_data,
                "injured_players": injured_players,
                "count": len(injured_players),
                "fetched_at": datetime.utcnow().isoformat()
            }
            
            if self.set_cached(cache_key, cache_data):
                result["injuries_cached"] = len(injured_players)
            else:
                result["error"] = "Failed to cache injuries data"
                
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Error refreshing injuries for {league}: {e}")
        
        logger.info(f"Injuries refresh for {league}: {result['injuries_cached']} injuries cached")
        return result
    
    def refresh_all(self, leagues: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Refresh all caches for given leagues.
        
        Args:
            leagues: List of league codes (default: ["NBA", "NFL"])
            
        Returns:
            Dictionary with refresh results for each league and data type
        """
        if leagues is None:
            leagues = ["NBA", "NFL"]
        
        result = {
            "started_at": datetime.utcnow().isoformat(),
            "leagues": {},
            "completed_at": None
        }
        
        for league in leagues:
            league = league.upper()
            result["leagues"][league] = {
                "team_stats": self.refresh_team_stats(league),
                "odds": self.refresh_odds(league),
                "injuries": self.refresh_injuries(league)
            }
        
        result["completed_at"] = datetime.utcnow().isoformat()
        logger.info(f"Full cache refresh completed for leagues: {leagues}")
        return result
    
    def get_cache_status(self) -> Dict[str, Any]:
        """
        Get status of all cached items.
        
        Returns:
            Dictionary with cache entries including key, fetched_at, expires_at, and is_stale
        """
        conn = None
        try:
            conn = self._get_conn()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT 
                        cache_key,
                        fetched_at,
                        expires_at,
                        (expires_at <= NOW()) as is_stale,
                        created_at,
                        updated_at
                    FROM data_cache
                    ORDER BY cache_key
                    """
                )
                rows = cur.fetchall()
                
                entries = []
                for row in rows:
                    entries.append({
                        "key": row["cache_key"],
                        "fetched_at": row["fetched_at"].isoformat() if row["fetched_at"] else None,
                        "expires_at": row["expires_at"].isoformat() if row["expires_at"] else None,
                        "is_stale": row["is_stale"],
                        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None
                    })
                
                stale_count = sum(1 for e in entries if e["is_stale"])
                fresh_count = len(entries) - stale_count
                
                return {
                    "total_entries": len(entries),
                    "fresh_count": fresh_count,
                    "stale_count": stale_count,
                    "entries": entries,
                    "checked_at": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting cache status: {e}")
            return {
                "total_entries": 0,
                "fresh_count": 0,
                "stale_count": 0,
                "entries": [],
                "error": str(e),
                "checked_at": datetime.utcnow().isoformat()
            }
        finally:
            self._put_conn(conn)
    
    def delete_expired(self) -> int:
        """
        Delete expired cache entries.
        
        Returns:
            Number of entries deleted
        """
        conn = None
        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM data_cache
                    WHERE expires_at <= NOW()
                    """
                )
                deleted = cur.rowcount
            conn.commit()
            logger.info(f"Deleted {deleted} expired cache entries")
            return deleted
        except Exception as e:
            logger.error(f"Error deleting expired cache entries: {e}")
            if conn:
                conn.rollback()
            return 0
        finally:
            self._put_conn(conn)
    
    def clear_cache(self, key_pattern: Optional[str] = None) -> int:
        """
        Clear cache entries matching a pattern.
        
        Args:
            key_pattern: SQL LIKE pattern (e.g., "team_stats:NBA:%"). If None, clears all.
            
        Returns:
            Number of entries deleted
        """
        conn = None
        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                if key_pattern:
                    cur.execute(
                        "DELETE FROM data_cache WHERE cache_key LIKE %s",
                        (key_pattern,)
                    )
                else:
                    cur.execute("DELETE FROM data_cache")
                deleted = cur.rowcount
            conn.commit()
            logger.info(f"Cleared {deleted} cache entries" + (f" matching {key_pattern}" if key_pattern else ""))
            return deleted
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            if conn:
                conn.rollback()
            return 0
        finally:
            self._put_conn(conn)
