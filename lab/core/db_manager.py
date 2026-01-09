"""
SQLite Database Manager for Historical Sports Data Collection

This module provides a robust, concurrent-safe database layer for storing:
- Game results and statistics
- Player props and betting lines
- Historical odds from multiple bookmakers
- Perplexity API cache for enrichment data

Features:
- WAL mode for concurrent read/write operations
- Indexed queries for fast backtesting (10,000+ iterations)
- Thread-safe connection management
- Automatic schema creation and migration
"""

import sqlite3
import json
import os
import threading
from typing import Dict, List, Optional, Any
from datetime import datetime


class DatabaseManager:
    """
    Thread-safe SQLite database manager for sports betting calibration system.
    
    Implements Write-Ahead Logging (WAL) for concurrent access and provides
    connection pooling via thread-local storage.
    """
    
    def __init__(self, db_path: str = "data/sports_data.db"):
        """
        Initialize database manager with WAL mode enabled.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._local = threading.local()
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Initialize schema
        self._init_schema()
    
    def get_connection(self) -> sqlite3.Connection:
        """
        Get thread-local SQLite connection.
        
        Returns:
            sqlite3.Connection: Thread-safe database connection
        """
        if not hasattr(self._local, 'conn'):
            self._local.conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0
            )
            self._local.conn.row_factory = sqlite3.Row
            
            # Enable WAL mode for concurrent access
            self._local.conn.execute("PRAGMA journal_mode=WAL;")
            self._local.conn.execute("PRAGMA synchronous=NORMAL;")
            self._local.conn.execute("PRAGMA cache_size=-64000;")  # 64MB cache
            
        return self._local.conn
    
    def _init_schema(self):
        """Create all tables and indexes if they don't exist."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # ============================================================
        # GAMES TABLE - Core game results and statistics
        # ============================================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS games (
                game_id TEXT PRIMARY KEY,
                date TEXT NOT NULL,
                sport TEXT NOT NULL,
                league TEXT,
                season INTEGER,
                home_team TEXT NOT NULL,
                away_team TEXT NOT NULL,
                home_score INTEGER,
                away_score INTEGER,
                status TEXT,
                
                -- Betting Lines (flattened for fast queries)
                moneyline_home INTEGER,
                moneyline_away INTEGER,
                spread_line REAL,
                spread_home_odds INTEGER,
                spread_away_odds INTEGER,
                total_line REAL,
                total_over_odds INTEGER,
                total_under_odds INTEGER,
                
                -- Metadata
                venue TEXT,
                attendance INTEGER,
                
                -- Complex data stored as JSON
                home_team_stats TEXT,  -- JSON object
                away_team_stats TEXT,  -- JSON object
                player_stats TEXT,     -- JSON array
                
                -- Timestamps
                created_at INTEGER,
                updated_at INTEGER,
                
                -- Enrichment tracking
                has_player_stats INTEGER DEFAULT 0,
                has_odds INTEGER DEFAULT 0,
                has_perplexity INTEGER DEFAULT 0
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_games_date 
            ON games(date)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_games_sport 
            ON games(sport)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_games_sport_date 
            ON games(sport, date)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_games_sport_season 
            ON games(sport, season)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_games_status 
            ON games(sport, status)
        """)
        
        # ============================================================
        # PLAYER_PROPS TABLE - Betting lines for player performance
        # ============================================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS player_props (
                prop_id TEXT PRIMARY KEY,
                game_id TEXT NOT NULL,
                date TEXT NOT NULL,
                sport TEXT NOT NULL,
                player_name TEXT NOT NULL,
                player_id TEXT,
                player_team TEXT NOT NULL,
                opponent_team TEXT NOT NULL,
                prop_type TEXT NOT NULL,
                
                -- Betting lines
                over_line REAL,
                under_line REAL,
                over_odds INTEGER,
                under_odds INTEGER,
                
                -- Actual result (for validation)
                actual_value REAL,
                
                -- Metadata
                bookmaker TEXT,
                created_at INTEGER,
                updated_at INTEGER,
                
                FOREIGN KEY (game_id) REFERENCES games(game_id)
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_props_game 
            ON player_props(game_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_props_player 
            ON player_props(player_name)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_props_type 
            ON player_props(prop_type)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_props_sport_date 
            ON player_props(sport, date)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_props_player_date 
            ON player_props(player_name, date)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_props_player_type 
            ON player_props(player_name, prop_type)
        """)
        
        # ============================================================
        # ODDS_HISTORY TABLE - Historical Market Expectations Archive
        # ============================================================
        # CRITICAL: This is NOT just "odds cache" - it's the calibration baseline
        # 
        # Three layers of historical data:
        # 1. The Target (line): Market's expectation at time T (e.g., "Lakers -3.5")
        # 2. The Price (odds): Implied probability/confidence (e.g., "-110" = 52.4%)
        # 3. The Context (timestamp): When this expectation existed
        #
        # Calibration Formula:
        #   Result (from games table) vs Prediction (from this table)
        #   Example: Lakers won by 7 > line of -3.5 = Cover
        #
        # Line movement over time reveals late-breaking information (injuries, 
        # lineup changes, sharp money) - crucial for understanding market accuracy
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS odds_history (
                game_id TEXT NOT NULL,
                bookmaker TEXT NOT NULL,
                market_type TEXT NOT NULL,  -- 'moneyline', 'spread', 'total'
                
                -- CALIBRATION TARGET: What the market expected
                line REAL,              -- The expectation (spread/total line)
                
                -- CALIBRATION PRICE: Market's confidence level
                home_odds INTEGER,      -- American odds for home/favorite
                away_odds INTEGER,      -- American odds for away/underdog
                over_odds INTEGER,      -- American odds for over
                under_odds INTEGER,     -- American odds for under
                
                -- CALIBRATION CONTEXT: When expectation existed
                timestamp INTEGER,      -- Unix timestamp of snapshot
                source TEXT,            -- 'oddsapi', 'oddsportal', 'covers'
                
                PRIMARY KEY (game_id, bookmaker, market_type, timestamp)
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_odds_game 
            ON odds_history(game_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_odds_bookmaker 
            ON odds_history(bookmaker)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_odds_timestamp 
            ON odds_history(timestamp)
        """)
        
        # ============================================================
        # PLAYER_PROPS_ODDS TABLE - Historical Player Prop Market Expectations
        # ============================================================
        # CRITICAL: Core calibration data for player performance betting
        #
        # Calibration Formula:
        #   Actual Value (from player_stats in games table) vs Line (from this table)
        #   Example: LeBron scored 28 points > line of 24.5 = Over hit
        #
        # The line represents the market's collective expectation at time T.
        # Line movement (24.5 → 25.5) reveals late information flow.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS player_props_odds (
                game_id TEXT NOT NULL,
                bookmaker TEXT NOT NULL,
                player_name TEXT NOT NULL,
                prop_type TEXT NOT NULL,  -- 'points', 'rebounds', 'assists', etc.
                
                -- CALIBRATION TARGET: Market's expectation for player performance
                line REAL NOT NULL,       -- The expectation (e.g., 24.5 points)
                
                -- CALIBRATION PRICE: Market's confidence level
                over_odds INTEGER,        -- American odds for Over
                under_odds INTEGER,       -- American odds for Under
                
                -- CALIBRATION CONTEXT
                timestamp INTEGER,        -- When this expectation existed
                source TEXT,              -- Data source
                
                PRIMARY KEY (game_id, bookmaker, player_name, prop_type, line)
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_props_odds_game 
            ON player_props_odds(game_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_props_odds_player 
            ON player_props_odds(player_name)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_props_odds_type 
            ON player_props_odds(prop_type)
        """)
        
        # ============================================================
        # PERPLEXITY_CACHE TABLE - LLM enrichment cache
        # ============================================================
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
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_perplexity_player_date 
            ON perplexity_cache(player_name, game_date)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_perplexity_game_date 
            ON perplexity_cache(game_date)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_perplexity_timestamp 
            ON perplexity_cache(timestamp)
        """)
        
        conn.commit()
    
    # ============================================================
    # GAMES TABLE OPERATIONS
    # ============================================================
    
    def insert_game(self, game_data: Dict[str, Any]) -> bool:
        """
        Insert or update a game record.
        
        Args:
            game_data: Dictionary containing game fields
            
        Returns:
            bool: True if successful
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Serialize complex objects to JSON
        if 'home_team_stats' in game_data and isinstance(game_data['home_team_stats'], dict):
            game_data['home_team_stats'] = json.dumps(game_data['home_team_stats'])
        
        if 'away_team_stats' in game_data and isinstance(game_data['away_team_stats'], dict):
            game_data['away_team_stats'] = json.dumps(game_data['away_team_stats'])
        
        if 'player_stats' in game_data and isinstance(game_data['player_stats'], list):
            game_data['player_stats'] = json.dumps(game_data['player_stats'])
        
        # Extract moneyline/spread/total from nested objects if present
        if 'moneyline' in game_data and isinstance(game_data['moneyline'], dict):
            game_data['moneyline_home'] = game_data['moneyline'].get('home')
            game_data['moneyline_away'] = game_data['moneyline'].get('away')
            del game_data['moneyline']
        
        if 'spread' in game_data and isinstance(game_data['spread'], dict):
            game_data['spread_line'] = game_data['spread'].get('line')
            game_data['spread_home_odds'] = game_data['spread'].get('home_odds')
            game_data['spread_away_odds'] = game_data['spread'].get('away_odds')
            del game_data['spread']
        
        if 'total' in game_data and isinstance(game_data['total'], dict):
            game_data['total_line'] = game_data['total'].get('line')
            game_data['total_over_odds'] = game_data['total'].get('over_odds')
            game_data['total_under_odds'] = game_data['total'].get('under_odds')
            del game_data['total']
        
        # Set timestamps
        now = int(datetime.now().timestamp())
        if 'created_at' not in game_data:
            game_data['created_at'] = now
        game_data['updated_at'] = now
        
        # Build INSERT OR REPLACE query
        columns = list(game_data.keys())
        placeholders = ', '.join(['?' for _ in columns])
        columns_str = ', '.join(columns)
        
        query = f"""
            INSERT OR REPLACE INTO games ({columns_str})
            VALUES ({placeholders})
        """
        
        try:
            cursor.execute(query, [game_data[col] for col in columns])
            conn.commit()
            return True
        except Exception as e:
            print(f"Error inserting game {game_data.get('game_id')}: {e}")
            conn.rollback()
            return False
    
    def get_game(self, game_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a game by ID.
        
        Args:
            game_id: Unique game identifier
            
        Returns:
            Dict with game data or None
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM games WHERE game_id = ?", (game_id,))
        row = cursor.fetchone()
        
        if row:
            game = dict(row)
            
            # Deserialize JSON fields
            if game.get('home_team_stats'):
                game['home_team_stats'] = json.loads(game['home_team_stats'])
            if game.get('away_team_stats'):
                game['away_team_stats'] = json.loads(game['away_team_stats'])
            if game.get('player_stats'):
                game['player_stats'] = json.loads(game['player_stats'])
            
            return game
        
        return None
    
    def get_games(
        self,
        sport: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        season: Optional[int] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Query games with filters.
        
        Args:
            sport: Filter by sport (NBA, NFL, etc.)
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            season: Filter by season year
            status: Filter by status (final, scheduled, etc.)
            
        Returns:
            List of game dictionaries
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM games WHERE 1=1"
        params = []
        
        if sport:
            query += " AND sport = ?"
            params.append(sport)
        
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        
        if season:
            query += " AND season = ?"
            params.append(season)
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY date, game_id"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        games = []
        for row in rows:
            game = dict(row)
            
            # Deserialize JSON fields
            if game.get('home_team_stats'):
                game['home_team_stats'] = json.loads(game['home_team_stats'])
            if game.get('away_team_stats'):
                game['away_team_stats'] = json.loads(game['away_team_stats'])
            if game.get('player_stats'):
                game['player_stats'] = json.loads(game['player_stats'])
            
            games.append(game)
        
        return games
    
    def get_game_ids(
        self,
        sport: str,
        start_date: str,
        end_date: str
    ) -> List[str]:
        """
        Get list of game IDs for resume functionality.
        
        Args:
            sport: Sport type
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            List of game IDs
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT game_id FROM games
            WHERE sport = ? AND date >= ? AND date <= ?
            ORDER BY date
        """, (sport, start_date, end_date))
        
        return [row[0] for row in cursor.fetchall()]
    
    # ============================================================
    # PLAYER PROPS OPERATIONS
    # ============================================================
    
    def insert_prop(self, prop_data: Dict[str, Any]) -> bool:
        """
        Insert or update a player prop.
        
        Args:
            prop_data: Dictionary containing prop fields
            
        Returns:
            bool: True if successful
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Set timestamps
        now = int(datetime.now().timestamp())
        if 'created_at' not in prop_data:
            prop_data['created_at'] = now
        prop_data['updated_at'] = now
        
        columns = list(prop_data.keys())
        placeholders = ', '.join(['?' for _ in columns])
        columns_str = ', '.join(columns)
        
        query = f"""
            INSERT OR REPLACE INTO player_props ({columns_str})
            VALUES ({placeholders})
        """
        
        try:
            cursor.execute(query, [prop_data[col] for col in columns])
            conn.commit()
            return True
        except Exception as e:
            print(f"Error inserting prop {prop_data.get('prop_id')}: {e}")
            conn.rollback()
            return False
    
    def get_props(
        self,
        sport: Optional[str] = None,
        player_name: Optional[str] = None,
        prop_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Query player props with filters.
        
        Args:
            sport: Filter by sport
            player_name: Filter by player
            prop_type: Filter by prop type (points, rebounds, etc.)
            start_date: Start date
            end_date: End date
            
        Returns:
            List of prop dictionaries
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM player_props WHERE 1=1"
        params = []
        
        if sport:
            query += " AND sport = ?"
            params.append(sport)
        
        if player_name:
            query += " AND player_name = ?"
            params.append(player_name)
        
        if prop_type:
            query += " AND prop_type = ?"
            params.append(prop_type)
        
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        
        query += " ORDER BY date, player_name"
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    # ============================================================
    # ODDS HISTORY OPERATIONS
    # ============================================================
    
    def insert_odds_history(self, odds_data: Dict[str, Any]) -> bool:
        """
        Insert historical odds record.
        
        Args:
            odds_data: Dictionary containing odds fields
            
        Returns:
            bool: True if successful
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if 'timestamp' not in odds_data:
            odds_data['timestamp'] = int(datetime.now().timestamp())
        
        columns = list(odds_data.keys())
        placeholders = ', '.join(['?' for _ in columns])
        columns_str = ', '.join(columns)
        
        query = f"""
            INSERT OR IGNORE INTO odds_history ({columns_str})
            VALUES ({placeholders})
        """
        
        try:
            cursor.execute(query, [odds_data[col] for col in columns])
            conn.commit()
            return True
        except Exception as e:
            print(f"Error inserting odds: {e}")
            conn.rollback()
            return False
    
    # ============================================================
    # PERPLEXITY CACHE OPERATIONS
    # ============================================================
    
    def get_cached_perplexity(self, query_hash: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached Perplexity response.
        
        Args:
            query_hash: Hash of the query
            
        Returns:
            Dict with response or None if expired/missing
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM perplexity_cache
            WHERE query_hash = ?
        """, (query_hash,))
        
        row = cursor.fetchone()
        
        if row:
            cache = dict(row)
            
            # Check TTL
            now = int(datetime.now().timestamp())
            age = now - cache['timestamp']
            
            if age < cache['ttl']:
                # Cache hit
                if cache.get('response_json'):
                    cache['response_json'] = json.loads(cache['response_json'])
                return cache
            else:
                # Expired - delete it
                cursor.execute("DELETE FROM perplexity_cache WHERE query_hash = ?", (query_hash,))
                conn.commit()
        
        return None
    
    def insert_perplexity_cache(self, cache_data: Dict[str, Any]) -> bool:
        """
        Insert Perplexity response into cache.
        
        Args:
            cache_data: Dictionary with query_hash, response_json, etc.
            
        Returns:
            bool: True if successful
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Serialize response if needed
        if 'response_json' in cache_data and not isinstance(cache_data['response_json'], str):
            cache_data['response_json'] = json.dumps(cache_data['response_json'])
        
        if 'timestamp' not in cache_data:
            cache_data['timestamp'] = int(datetime.now().timestamp())
        
        columns = list(cache_data.keys())
        placeholders = ', '.join(['?' for _ in columns])
        columns_str = ', '.join(columns)
        
        query = f"""
            INSERT OR REPLACE INTO perplexity_cache ({columns_str})
            VALUES ({placeholders})
        """
        
        try:
            cursor.execute(query, [cache_data[col] for col in columns])
            conn.commit()
            return True
        except Exception as e:
            print(f"Error inserting perplexity cache: {e}")
            conn.rollback()
            return False
    
    def cleanup_expired_cache(self):
        """Remove expired Perplexity cache entries."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        now = int(datetime.now().timestamp())
        
        cursor.execute("""
            DELETE FROM perplexity_cache
            WHERE (timestamp + ttl) < ?
        """, (now,))
        
        deleted = cursor.rowcount
        conn.commit()
        
        return deleted
    
    # ============================================================
    # CALIBRATION QUERY HELPERS
    # ============================================================
    
    def get_calibration_data(
        self,
        sport: str,
        start_date: str,
        end_date: str,
        market_type: Optional[str] = None,
        snapshot: str = "closing",
        window_minutes: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get calibration data for market accuracy analysis.
        
        Joins games (actual results) with odds_history (market expectations)
        to enable calibration analysis.
        
        Args:
            sport: Sport type
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            market_type: Filter by market ('spread', 'total', 'moneyline')
            snapshot: Snapshot selection ("closing" for latest, "window" for time window)
            window_minutes: Minutes before game start to include when snapshot="window"
            
        Returns:
            List of dicts with {result, expectation, accuracy}
            
        Example:
            >>> calibration = db.get_calibration_data('NBA', '2024-01-01', '2024-12-31', 'spread')
            >>> for record in calibration:
            >>>     actual_margin = record['home_score'] - record['away_score']
            >>>     expected_line = record['line']
            >>>     covered = actual_margin > expected_line
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        if snapshot not in {"closing", "window"}:
            raise ValueError("snapshot must be 'closing' or 'window'")

        if snapshot == "window" and not window_minutes:
            raise ValueError("window_minutes must be provided when snapshot='window'")

        query = """
            WITH filtered_odds AS (
                SELECT o.*
                FROM odds_history o
                JOIN games g ON g.game_id = o.game_id
                WHERE g.sport = ?
                    AND g.date >= ?
                    AND g.date <= ?
                    AND g.home_score IS NOT NULL
                    AND g.away_score IS NOT NULL
        """

        params = [sport, start_date, end_date]

        if market_type:
            query += " AND o.market_type = ?"
            params.append(market_type)

        if snapshot == "window":
            query += """
                    AND o.timestamp BETWEEN (CAST(strftime('%s', g.date) AS INTEGER) - ?)
                    AND CAST(strftime('%s', g.date) AS INTEGER)
            """
            params.append(window_minutes * 60)

        query += """
            ),
            latest_odds AS (
                SELECT
                    game_id,
                    bookmaker,
                    market_type,
                    MAX(timestamp) AS max_timestamp
                FROM filtered_odds
                GROUP BY game_id, bookmaker, market_type
            )
            SELECT
                g.game_id,
                g.date,
                g.home_team,
                g.away_team,
                g.home_score,
                g.away_score,
                o.bookmaker,
                o.market_type,
                o.line AS market_expectation,
                o.home_odds,
                o.away_odds,
                o.over_odds,
                o.under_odds,
                o.timestamp AS market_snapshot_time
            FROM latest_odds lo
            JOIN filtered_odds o
                ON o.game_id = lo.game_id
                AND o.bookmaker = lo.bookmaker
                AND o.market_type = lo.market_type
                AND o.timestamp = lo.max_timestamp
            JOIN games g ON g.game_id = o.game_id
            ORDER BY g.date, g.game_id, o.timestamp
        """
        
        cursor.execute(query, params)
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_player_prop_calibration_data(
        self,
        sport: str,
        start_date: str,
        end_date: str,
        prop_type: Optional[str] = None,
        player_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get player prop calibration data.
        
        Joins player_stats (actual performance) with player_props_odds 
        (market expectations) for accuracy analysis.
        
        Args:
            sport: Sport type
            start_date: Start date
            end_date: End date
            prop_type: Filter by prop type ('points', 'rebounds', etc.)
            player_name: Filter by player
            
        Returns:
            List of dicts with {actual_value, market_line, result}
            
        Example:
            >>> props = db.get_player_prop_calibration_data('NBA', '2024-01-01', '2024-12-31', 'points')
            >>> for prop in props:
            >>>     actual = prop['actual_value']
            >>>     line = prop['market_expectation']
            >>>     result = 'OVER' if actual > line else 'UNDER' if actual < line else 'PUSH'
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT 
                prop_id,
                game_id,
                date,
                player_name,
                prop_type,
                actual_value,
                bookmaker,
                over_line AS market_expectation,
                over_odds,
                under_odds,
                created_at AS market_snapshot_time,
                CASE 
                    WHEN actual_value > over_line THEN 'OVER'
                    WHEN actual_value < over_line THEN 'UNDER'
                    ELSE 'PUSH'
                END AS result
            FROM player_props
            WHERE sport = ?
                AND date >= ?
                AND date <= ?
                AND actual_value IS NOT NULL
                AND over_line IS NOT NULL
                AND over_odds IS NOT NULL
                AND under_odds IS NOT NULL
        """
        
        params = [sport, start_date, end_date]
        
        if prop_type:
            query += " AND prop_type = ?"
            params.append(prop_type)
        
        if player_name:
            query += " AND player_name = ?"
            params.append(player_name)
        
        query += " ORDER BY date, player_name"
        
        cursor.execute(query, params)
        
        return [dict(row) for row in cursor.fetchall()]
    
    # ============================================================
    # UTILITY METHODS
    # ============================================================
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get database statistics.
        
        Returns:
            Dict with counts for each table
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        for table in ['games', 'player_props', 'odds_history', 'player_props_odds', 'perplexity_cache']:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            stats[table] = cursor.fetchone()[0]
        
        return stats
    
    def close(self):
        """Close database connection."""
        if hasattr(self._local, 'conn'):
            self._local.conn.close()
            del self._local.conn
