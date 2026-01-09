"""
Data pipeline for ingesting, validating, and curating sports betting data.

This module provides comprehensive data ingestion from OmegaSports scraper engine,
with validation, caching, and historical database management.

Supports:
  - Game-level bets (moneyline, spread, total)
  - Player props (points, rebounds, assists, passing yards, TDs, etc.)
  - Multiple sports (NBA, NFL, NCAAB, NCAAF)
"""

import logging
import json
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class GameData:
    """Structured game data."""

    game_id: str
    date: str
    sport: str
    league: str
    home_team: str
    away_team: str
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    moneyline: Optional[Dict[str, Any]] = None
    spread: Optional[Dict[str, Any]] = None
    total: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class PlayerPropData:
    """Structured player prop data."""

    prop_id: str
    game_id: str
    date: str
    sport: str
    player_name: str
    player_team: str
    opponent_team: str
    prop_type: str  # e.g., 'points', 'rebounds', 'passing_yards'
    over_line: Optional[float] = None
    under_line: Optional[float] = None
    over_odds: Optional[float] = None
    under_odds: Optional[float] = None
    actual_value: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class DataValidator:
    """Validates game data and player prop data against schema requirements."""

    REQUIRED_GAME_FIELDS = [
        "game_id",
        "date",
        "sport",
        "league",
        "home_team",
        "away_team",
    ]

    REQUIRED_PROP_FIELDS = [
        "prop_id",
        "game_id",
        "date",
        "sport",
        "player_name",
        "player_team",
        "opponent_team",
        "prop_type",
    ]

    VALID_SPORTS = ["NBA", "NFL", "MLB", "NHL", "NCAAB", "NCAAF"]

    # Player prop types by sport
    BASKETBALL_PROPS = [
        "points",
        "rebounds",
        "assists",
        "three_pointers",  # Added
        "threes_made",  # Legacy, same as three_pointers
        "steals",  # Moved up
        "blocks",  # Moved up
        "points_rebounds",
        "points_assists",
        "rebounds_assists",
    ]

    FOOTBALL_PROPS = [
        "passing_yards",
        "rushing_yards",
        "receiving_yards",
        "receptions",  # Moved up
        "rushing_attempts",  # Added
        "passing_attempts",  # Added
        "passing_completions",  # Added
        "touchdowns",
        "passing_tds",
        "rushing_tds",
        "receiving_tds",
        "interceptions",
        "completion_pct",
        "sacks",
    ]

    @classmethod
    def validate_game(cls, game: Dict[str, Any]) -> tuple[bool, str]:
        """
        Validate game data.

        Args:
            game: Game data dictionary

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check required fields
        for field in cls.REQUIRED_GAME_FIELDS:
            if field not in game or game[field] is None:
                return False, f"Missing required field: {field}"

        # Validate sport
        if game["sport"] not in cls.VALID_SPORTS:
            return False, f"Invalid sport: {game['sport']}"

        # Validate date format
        try:
            datetime.strptime(game["date"], "%Y-%m-%d")
        except ValueError:
            return False, f"Invalid date format: {game['date']}"

        # Validate teams are non-empty strings
        if not isinstance(game["home_team"], str) or not game["home_team"]:
            return False, "home_team must be non-empty string"
        if not isinstance(game["away_team"], str) or not game["away_team"]:
            return False, "away_team must be non-empty string"

        # Check for duplicate teams
        if game["home_team"].lower() == game["away_team"].lower():
            return False, "home_team and away_team cannot be the same"

        return True, ""

    @classmethod
    def validate_prop(cls, prop: Dict[str, Any]) -> tuple[bool, str]:
        """
        Validate player prop data.

        Args:
            prop: Player prop data dictionary

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check required fields
        for field in cls.REQUIRED_PROP_FIELDS:
            if field not in prop or prop[field] is None:
                return False, f"Missing required field: {field}"

        # Validate sport
        if prop["sport"] not in cls.VALID_SPORTS:
            return False, f"Invalid sport: {prop['sport']}"

        # Validate prop type
        if prop["sport"] in ["NBA", "NCAAB"]:
            valid_props = cls.BASKETBALL_PROPS
        elif prop["sport"] in ["NFL", "NCAAF"]:
            valid_props = cls.FOOTBALL_PROPS
        else:
            return False, f"No prop types defined for {prop['sport']}"

        if prop["prop_type"] not in valid_props:
            return False, f"Invalid prop type for {prop['sport']}: {prop['prop_type']}"

        # Validate date format
        try:
            datetime.strptime(prop["date"], "%Y-%m-%d")
        except ValueError:
            return False, f"Invalid date format: {prop['date']}"

        # Validate player name
        if not isinstance(prop["player_name"], str) or not prop["player_name"]:
            return False, "player_name must be non-empty string"

        return True, ""


class CacheManager:
    """Manages caching of API responses and processed data."""

    def __init__(self, cache_dir: Path):
        """
        Initialize cache manager.

        Args:
            cache_dir: Directory for cache storage
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"CacheManager initialized with cache_dir={cache_dir}")

    def _get_cache_key(self, prefix: str, params: Dict[str, Any]) -> str:
        """
        Generate cache key from prefix and parameters.

        Args:
            prefix: Cache key prefix
            params: Parameters dictionary

        Returns:
            Cache key (hash-based)
        """
        params_str = json.dumps(params, sort_keys=True)
        params_hash = hashlib.md5(params_str.encode()).hexdigest()
        return f"{prefix}_{params_hash}"

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve cached data.

        Args:
            key: Cache key

        Returns:
            Cached data or None if not found/expired
        """
        cache_file = self.cache_dir / f"{key}.json"
        if not cache_file.exists():
            return None

        # Check if cache is older than 24 hours
        file_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
        if file_age > timedelta(hours=24):
            logger.debug(f"Cache expired: {key}")
            return None

        try:
            with open(cache_file, "r") as f:
                data = json.load(f)
            logger.debug(f"Cache hit: {key}")
            return data
        except Exception as e:
            logger.warning(f"Error reading cache {key}: {e}")
            return None

    def set(self, key: str, data: Any) -> None:
        """
        Cache data.

        Args:
            key: Cache key
            data: Data to cache
        """
        cache_file = self.cache_dir / f"{key}.json"
        try:
            with open(cache_file, "w") as f:
                json.dump(data, f, default=str)
            logger.debug(f"Cache set: {key}")
        except Exception as e:
            logger.warning(f"Error writing cache {key}: {e}")

    def clear(self, prefix: Optional[str] = None) -> None:
        """
        Clear cache.

        Args:
            prefix: Clear only cache keys with this prefix. If None, clear all.
        """
        for cache_file in self.cache_dir.glob("*.json"):
            if prefix is None or cache_file.stem.startswith(prefix):
                cache_file.unlink()
        logger.info(f"Cache cleared (prefix={prefix})")


class HistoricalDatabase:
    """Manages persistent storage of historical game and player prop data."""

    def __init__(self, data_dir: Path):
        """
        Initialize historical database.

        Args:
            data_dir: Directory for data storage
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"HistoricalDatabase initialized with data_dir={data_dir}")

    def _get_game_file_path(self, sport: str, year: int) -> Path:
        """
        Get file path for game data by sport/year.

        Args:
            sport: Sport name
            year: Year

        Returns:
            Path to data file
        """
        return self.data_dir / f"{sport.lower()}_{year}_games.json"

    def _get_prop_file_path(self, sport: str, year: int) -> Path:
        """
        Get file path for player prop data by sport/year.

        Args:
            sport: Sport name
            year: Year

        Returns:
            Path to data file
        """
        return self.data_dir / f"{sport.lower()}_{year}_props.json"

    def save_games(self, games: List[Dict[str, Any]], sport: str, year: int) -> int:
        """
        Save games to database.

        Args:
            games: List of game dictionaries
            sport: Sport name
            year: Year

        Returns:
            Number of games saved
        """
        file_path = self._get_game_file_path(sport, year)

        # Validate all games
        valid_games = []
        for game in games:
            is_valid, error = DataValidator.validate_game(game)
            if is_valid:
                valid_games.append(game)
            else:
                logger.warning(f"Invalid game data: {error}")

        if not valid_games:
            logger.warning(f"No valid games to save for {sport} {year}")
            return 0

        # Save to file
        with open(file_path, "w") as f:
            json.dump(valid_games, f, indent=2, default=str)

        logger.info(f"Saved {len(valid_games)} games to {file_path}")
        return len(valid_games)

    def save_props(self, props: List[Dict[str, Any]], sport: str, year: int) -> int:
        """
        Save player props to database.

        Args:
            props: List of player prop dictionaries
            sport: Sport name
            year: Year

        Returns:
            Number of props saved
        """
        file_path = self._get_prop_file_path(sport, year)

        # Validate all props
        valid_props = []
        for prop in props:
            is_valid, error = DataValidator.validate_prop(prop)
            if is_valid:
                valid_props.append(prop)
            else:
                logger.warning(f"Invalid prop data: {error}")

        if not valid_props:
            logger.warning(f"No valid props to save for {sport} {year}")
            return 0

        # Save to file
        with open(file_path, "w") as f:
            json.dump(valid_props, f, indent=2, default=str)

        logger.info(f"Saved {len(valid_props)} props to {file_path}")
        return len(valid_props)

    def load_games(
        self, sport: str, start_year: int, end_year: int
    ) -> List[Dict[str, Any]]:
        """
        Load games from database.

        Args:
            sport: Sport name
            start_year: Start year (inclusive)
            end_year: End year (inclusive)

        Returns:
            List of game dictionaries
        """
        all_games = []

        for year in range(start_year, end_year + 1):
            file_path = self._get_game_file_path(sport, year)
            if not file_path.exists():
                logger.warning(f"No data file found: {file_path}")
                continue

            try:
                with open(file_path, "r") as f:
                    games = json.load(f)
                all_games.extend(games)
                logger.info(f"Loaded {len(games)} games from {file_path}")
            except Exception as e:
                logger.error(f"Error loading {file_path}: {e}")

        logger.info(f"Total games loaded: {len(all_games)} ({sport}, {start_year}-{end_year})")
        return all_games

    def load_props(
        self, sport: str, start_year: int, end_year: int, prop_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Load player props from database.

        Args:
            sport: Sport name
            start_year: Start year (inclusive)
            end_year: End year (inclusive)
            prop_type: Filter by prop type (optional)

        Returns:
            List of player prop dictionaries
        """
        all_props = []

        for year in range(start_year, end_year + 1):
            file_path = self._get_prop_file_path(sport, year)
            if not file_path.exists():
                logger.warning(f"No props file found: {file_path}")
                continue

            try:
                with open(file_path, "r") as f:
                    props = json.load(f)
                
                # Filter by prop type if specified
                if prop_type:
                    props = [p for p in props if p.get("prop_type") == prop_type]
                
                all_props.extend(props)
                logger.info(f"Loaded {len(props)} props from {file_path}")
            except Exception as e:
                logger.error(f"Error loading {file_path}: {e}")

        logger.info(f"Total props loaded: {len(all_props)} ({sport}, {start_year}-{end_year})")
        return all_props

    def game_count(self, sport: str, year: int) -> int:
        """
        Get count of games for sport/year.

        Args:
            sport: Sport name
            year: Year

        Returns:
            Number of games
        """
        file_path = self._get_game_file_path(sport, year)
        if not file_path.exists():
            return 0

        try:
            with open(file_path, "r") as f:
                games = json.load(f)
            return len(games)
        except Exception as e:
            logger.error(f"Error counting games in {file_path}: {e}")
            return 0

    def prop_count(self, sport: str, year: int, prop_type: Optional[str] = None) -> int:
        """
        Get count of player props for sport/year.

        Args:
            sport: Sport name
            year: Year
            prop_type: Filter by prop type (optional)

        Returns:
            Number of props
        """
        file_path = self._get_prop_file_path(sport, year)
        if not file_path.exists():
            return 0

        try:
            with open(file_path, "r") as f:
                props = json.load(f)
            
            if prop_type:
                props = [p for p in props if p.get("prop_type") == prop_type]
            
            return len(props)
        except Exception as e:
            logger.error(f"Error counting props in {file_path}: {e}")
            return 0


class DataPipeline:
    """
    Main data pipeline for ingesting, validating, and curating sports data.
    
    Supports:
      - Game-level bets (moneyline, spread, total)
      - Player props (points, rebounds, assists, passing yards, etc.)
      - Multiple sports (NBA, NFL, NCAAB, NCAAF)
    """

    def __init__(self, cache_dir: Optional[Path] = None, data_dir: Optional[Path] = None):
        """
        Initialize data pipeline.

        Args:
            cache_dir: Directory for caching data
            data_dir: Directory for historical database
        """
        self.cache_dir = Path(cache_dir) if cache_dir else Path("./data/cache")
        self.data_dir = Path(data_dir) if data_dir else Path("./data/historical")

        self.cache = CacheManager(self.cache_dir)
        self.database = HistoricalDatabase(self.data_dir)
        self.validator = DataValidator()

        logger.info(
            f"DataPipeline initialized (cache={self.cache_dir}, data={self.data_dir})"
        )

    def fetch_historical_games(
        self, sport: str, start_year: int = 2020, end_year: int = 2024
    ) -> List[Dict[str, Any]]:
        """
        Fetch historical game data for a sport and year range.

        Args:
            sport: Sport name (NBA, NFL, etc.)
            start_year: Start year (inclusive)
            end_year: End year (inclusive)

        Returns:
            List of game dictionaries
        """
        logger.info(f"Fetching historical games: {sport} {start_year}-{end_year}")
        games = self.database.load_games(sport, start_year, end_year)
        if not games:
            logger.warning(f"No historical games found for {sport}")
        return games

    def fetch_historical_props(
        self, sport: str, start_year: int = 2020, end_year: int = 2024,
        prop_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch historical player prop data.

        Args:
            sport: Sport name
            start_year: Start year (inclusive)
            end_year: End year (inclusive)
            prop_type: Filter by prop type (optional)

        Returns:
            List of player prop dictionaries
        """
        logger.info(f"Fetching historical props: {sport} {start_year}-{end_year}")
        props = self.database.load_props(sport, start_year, end_year, prop_type)
        if not props:
            logger.warning(f"No historical props found for {sport}")
        return props

    def validate_game_data(self, game: Dict[str, Any]) -> tuple[bool, str]:
        """
        Validate game data against schema.

        Args:
            game: Game data dictionary

        Returns:
            Tuple of (is_valid, error_message)
        """
        return self.validator.validate_game(game)

    def validate_prop_data(self, prop: Dict[str, Any]) -> tuple[bool, str]:
        """
        Validate player prop data against schema.

        Args:
            prop: Player prop data dictionary

        Returns:
            Tuple of (is_valid, error_message)
        """
        return self.validator.validate_prop(prop)

    def save_games(
        self, games: List[Dict[str, Any]], sport: str, year: int
    ) -> int:
        """
        Save games to historical database.

        Args:
            games: List of game dictionaries
            sport: Sport name
            year: Year

        Returns:
            Number of games saved
        """
        logger.info(f"Saving {len(games)} games for {sport} {year}")
        return self.database.save_games(games, sport, year)

    def save_props(
        self, props: List[Dict[str, Any]], sport: str, year: int
    ) -> int:
        """
        Save player props to historical database.

        Args:
            props: List of player prop dictionaries
            sport: Sport name
            year: Year

        Returns:
            Number of props saved
        """
        logger.info(f"Saving {len(props)} props for {sport} {year}")
        return self.database.save_props(props, sport, year)

    def get_game_count(self, sport: str, start_year: int = 2020, end_year: int = 2024) -> int:
        """
        Get total count of games for sport/year range.

        Args:
            sport: Sport name
            start_year: Start year
            end_year: End year

        Returns:
            Total number of games
        """
        total = 0
        for year in range(start_year, end_year + 1):
            count = self.database.game_count(sport, year)
            total += count
        return total

    def get_prop_count(
        self, sport: str, start_year: int = 2020, end_year: int = 2024,
        prop_type: Optional[str] = None
    ) -> int:
        """
        Get total count of player props for sport/year range.

        Args:
            sport: Sport name
            start_year: Start year
            end_year: End year
            prop_type: Filter by prop type (optional)

        Returns:
            Total number of props
        """
        total = 0
        for year in range(start_year, end_year + 1):
            count = self.database.prop_count(sport, year, prop_type)
            total += count
        return total

    def cache_data(self, key: str, data: Any) -> None:
        """
        Cache data for future use.

        Args:
            key: Cache key
            data: Data to cache
        """
        self.cache.set(key, data)

    def get_cached_data(self, key: str) -> Optional[Any]:
        """
        Retrieve cached data.

        Args:
            key: Cache key

        Returns:
            Cached data or None if not found
        """
        return self.cache.get(key)

    def clear_cache(self, prefix: Optional[str] = None) -> None:
        """
        Clear cache.

        Args:
            prefix: Clear only cache keys with this prefix
        """
        self.cache.clear(prefix)
    
    def fetch_and_cache_games(
        self, sport: str, start_year: int, end_year: int, force_refresh: bool = False,
        enrich_with_odds: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Fetch games from multiple sources and cache them.
        
        Uses real historical data scrapers (Basketball Reference, Pro Football Reference, etc.)
        for historical data. NO MOCK OR SAMPLE DATA.
        
        CRITICAL: Enriches games with betting lines from The Odds API for proper validation.
        
        Args:
            sport: Sport name (NBA, NFL, etc.)
            start_year: Start year (inclusive)
            end_year: End year (inclusive)
            force_refresh: Whether to bypass cache and fetch fresh data
            enrich_with_odds: Whether to add betting lines from The Odds API (CRITICAL for validation)
        
        Returns:
            List of all game dictionaries with real historical data and betting lines
        """
        from src.historical_scrapers import MultiSourceHistoricalScraper
        from src.api_enrichment import APIDataEnrichment
        from datetime import datetime
        
        scraper = MultiSourceHistoricalScraper()
        enrichment = APIDataEnrichment() if enrich_with_odds else None
        
        all_games = []
        current_year = datetime.now().year
        
        logger.info(f"Fetching {sport} games from {start_year} to {end_year}")
        logger.info("Using REAL historical data from Sports Reference sites (NO MOCK DATA)")
        
        if enrich_with_odds:
            logger.info("BETTING LINES: Will enrich with odds from The Odds API")
        
        for year in range(start_year, end_year + 1):
            # Check cache first (unless force_refresh is True)
            cache_key = f"historical_games_enriched_{sport}_{year}" if enrich_with_odds else f"historical_games_{sport}_{year}"
            cached = self.get_cached_data(cache_key) if not force_refresh else None
            
            if cached:
                logger.info(f"Using cached data for {sport} {year} ({len(cached)} games)")
                all_games.extend(cached)
            else:
                if force_refresh:
                    logger.info(f"Force refresh: Fetching fresh historical data for {sport} {year}")
                else:
                    logger.info(f"Fetching historical data for {sport} {year}")
                
                # Use historical scrapers for past/current seasons
                # This scrapes REAL data from Basketball Reference, Pro Football Reference, etc.
                try:
                    year_games = scraper.fetch_games(sport, year, year)
                    
                    if year_games:
                        # Enrich with betting lines (CRITICAL for validation)
                        if enrich_with_odds and enrichment:
                            logger.info(f"Enriching {len(year_games)} games with betting lines...")
                            year_games = enrichment.enrich_games(
                                year_games,
                                add_betting_lines=True,
                                add_player_stats=False,
                                show_progress=True
                            )
                        
                        # Cache and save
                        self.cache_data(cache_key, year_games)
                        self.save_games(year_games, sport, year)
                        all_games.extend(year_games)
                        logger.info(f"✓ Scraped {len(year_games)} real games for {sport} {year}")
                    else:
                        logger.warning(f"No games found for {sport} {year}")
                
                except Exception as e:
                    logger.error(f"Error fetching historical data for {sport} {year}: {e}")
                    import traceback
                    logger.debug(traceback.format_exc())
        
        logger.info(f"Total games fetched for {sport}: {len(all_games)}")
        return all_games
