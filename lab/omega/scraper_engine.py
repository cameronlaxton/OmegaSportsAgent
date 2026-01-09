"""
ScraperEngine compatibility module for Validation Lab.

This module provides the ScraperEngine interface expected by the validation lab,
wrapping the actual OmegaScraper from OmegaSportsAgent.

SUPPORTED SPORTS:
- NBA (National Basketball Association)
- NFL (National Football League)
- NHL (National Hockey League)
- MLB (Major League Baseball)
- NCAAB (NCAA Men's Basketball)

RELATIONSHIP TO OMEGAAGENT:
This Validation Lab is a companion research platform to OmegaAgent. The lab:
- Tests and validates OmegaAgent's algorithms and parameters
- Optimizes model parameters through systematic experimentation
- Feeds validated improvements back into OmegaAgent production system
- Provides rigorous statistical validation of all optimizations
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add omega engine path to sys.path if configured
try:
    from utils.config import config
    omega_path = config.omega_engine_path
    if omega_path and omega_path.exists():
        if str(omega_path) not in sys.path:
            sys.path.insert(0, str(omega_path))
except Exception:
    pass

# Try to import the actual scraper
try:
    from scraper_engine import OmegaScraper
    OMEGA_SCRAPER_AVAILABLE = True
except ImportError:
    OMEGA_SCRAPER_AVAILABLE = False
    OmegaScraper = None


# Supported sports for omni-sports functionality
SUPPORTED_SPORTS = {
    'NBA': 'National Basketball Association',
    'NFL': 'National Football League',
    'NHL': 'National Hockey League',
    'MLB': 'Major League Baseball',
    'NCAAB': 'NCAA Men\'s Basketball',
    'NCAAF': 'NCAA Football',  # Also support NCAAF
    'WNBA': 'Women\'s National Basketball Association',
    'MLS': 'Major League Soccer'
}


class ScraperEngine:
    """
    Compatibility wrapper for ScraperEngine interface.
    
    This class provides the interface expected by the validation lab,
    wrapping the actual OmegaScraper implementation from OmegaAgent.
    
    Supports omni-sports functionality for NBA, NFL, NHL, MLB, and NCAAB.
    Uses OmegaAgent's schedule_api to fetch games from ESPN API.
    
    RELATIONSHIP TO OMEGAAGENT:
    This Validation Lab tests and improves OmegaAgent. Optimizations discovered
    here feed back into the OmegaAgent production system.
    """
    
    def __init__(self):
        """Initialize the scraper engine."""
        if not OMEGA_SCRAPER_AVAILABLE:
            # Don't raise error, just warn - the scraper may not be needed
            self._scraper = None
        else:
            self._scraper = OmegaScraper()
        
        # Initialize logger
        import logging
        self.logger = logging.getLogger(__name__)
        
        # Cache for loaded modules
        self._schedule_api = None
        self._stats_module = None
    
    def _load_schedule_api(self):
        """Load schedule_api module from OmegaSportsAgent."""
        if self._schedule_api is not None:
            return self._schedule_api
        
        try:
            # First attempt: Import from OmegaSportsAgent via configured path
            from utils.config import config
            omega_path = config.omega_engine_path
            
            if omega_path and omega_path.exists():
                import sys
                omega_str = str(omega_path)
                if omega_str not in sys.path:
                    sys.path.insert(0, omega_str)
                
                # Try importing from src.data.schedule_api
                try:
                    from src.data import schedule_api
                    self._schedule_api = schedule_api
                    self.logger.info(f"Successfully loaded schedule_api from {omega_path}")
                    return self._schedule_api
                except ImportError as e:
                    self.logger.warning(f"Could not import from src.data: {e}")
            
            # Fallback: Try direct import if omega package is available
            try:
                from src.data import schedule_api
                self._schedule_api = schedule_api
                self.logger.info("Successfully loaded schedule_api from system path")
                return self._schedule_api
            except ImportError:
                pass
                
        except Exception as e:
            self.logger.error(f"Error loading schedule_api: {e}")
        
        return None
    
    def fetch_games(
        self, 
        sport: str, 
        start_date: Optional[str] = None, 
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch games for a sport (omni-sports support).
        
        Supports: NBA, NFL, NHL, MLB, NCAAB, NCAAF, WNBA, MLS
        
        Args:
            sport: Sport code (NBA, NFL, NHL, MLB, NCAAB, etc.)
            start_date: Start date in YYYY-MM-DD format (optional, for historical data use get_scoreboard)
            limit: Maximum number of games to return (optional)
        
        Returns:
            List of game dictionaries in format expected by validation lab
        
        Raises:
            ValueError: If sport is not supported
        """
        # Validate sport
        sport_upper = sport.upper()
        if sport_upper not in SUPPORTED_SPORTS:
            raise ValueError(
                f"Sport '{sport}' not supported. Supported sports: {', '.join(SUPPORTED_SPORTS.keys())}"
            )
        
        # Load schedule API
        schedule_api = self._load_schedule_api()
        if schedule_api is None:
            self.logger.error(
                "Could not load schedule_api from OmegaSportsAgent. "
                "Ensure OMEGA_ENGINE_PATH is correctly configured in .env and points to OmegaSportsAgent repository."
            )
            return []
        
        try:
            from datetime import datetime, timedelta
            games = []
            
            # Determine if we're fetching historical or upcoming games
            if start_date:
                try:
                    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                    today = datetime.now()
                    
                    # If date is in the past, try to get scoreboard for that date
                    if start_dt.date() < today.date():
                        self.logger.info(f"Fetching historical games for {sport_upper} on {start_date}")
                        # Use scoreboard API for historical data
                        raw_games = schedule_api.get_scoreboard(sport_upper, date=start_date)
                        games = [self._format_game(g, sport_upper) for g in raw_games]
                    else:
                        # Future date - get upcoming games
                        days_ahead = (start_dt - today).days
                        days_to_fetch = max(1, min(days_ahead + 7, 30))  # Cap at 30 days
                        self.logger.info(f"Fetching upcoming games for {sport_upper} (next {days_to_fetch} days)")
                        raw_games = schedule_api.get_upcoming_games(sport_upper, days=days_to_fetch)
                        
                        # Filter to games on or after start_date
                        for game in raw_games:
                            try:
                                game_date_str = game.get("date", "")
                                if game_date_str:
                                    game_dt = datetime.fromisoformat(game_date_str.replace("Z", "+00:00"))
                                    if game_dt.date() >= start_dt.date():
                                        games.append(self._format_game(game, sport_upper))
                            except (ValueError, AttributeError):
                                games.append(self._format_game(game, sport_upper))
                
                except ValueError as e:
                    self.logger.warning(f"Invalid date format '{start_date}': {e}. Fetching upcoming games instead.")
                    raw_games = schedule_api.get_upcoming_games(sport_upper, days=7)
                    games = [self._format_game(g, sport_upper) for g in raw_games]
            else:
                # No date specified - get today's or upcoming games
                self.logger.info(f"Fetching today's games for {sport_upper}")
                try:
                    raw_games = schedule_api.get_todays_games(sport_upper)
                    games = [self._format_game(g, sport_upper) for g in raw_games]
                    
                    # If no games today, get upcoming
                    if not games:
                        self.logger.info(f"No games today, fetching upcoming games for {sport_upper}")
                        raw_games = schedule_api.get_upcoming_games(sport_upper, days=7)
                        games = [self._format_game(g, sport_upper) for g in raw_games]
                except Exception as e:
                    self.logger.warning(f"Error fetching today's games: {e}. Trying upcoming games.")
                    raw_games = schedule_api.get_upcoming_games(sport_upper, days=7)
                    games = [self._format_game(g, sport_upper) for g in raw_games]
            
            # Apply limit if specified
            if limit and limit > 0:
                games = games[:limit]
            
            self.logger.info(f"Returning {len(games)} games for {sport_upper}")
            return games
            
        except Exception as e:
            self.logger.error(f"Error fetching games for {sport_upper}: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
            return []
    
    def fetch_historical_games(
        self,
        sport: str,
        start_date: str,
        end_date: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch historical games for a date range.
        
        Args:
            sport: Sport code (NBA, NFL, etc.)
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format (optional, defaults to start_date)
            limit: Maximum number of games to return (optional)
        
        Returns:
            List of historical game dictionaries
        """
        schedule_api = self._load_schedule_api()
        if schedule_api is None:
            self.logger.error("Could not load schedule_api for historical data fetch")
            return []
        
        try:
            from datetime import datetime, timedelta
            
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else start_dt
            
            all_games = []
            current_dt = start_dt
            
            # Fetch games for each date in the range
            while current_dt <= end_dt:
                date_str = current_dt.strftime("%Y-%m-%d")
                try:
                    self.logger.debug(f"Fetching scoreboard for {sport} on {date_str}")
                    raw_games = schedule_api.get_scoreboard(sport.upper(), date=date_str)
                    formatted_games = [self._format_game(g, sport.upper()) for g in raw_games]
                    all_games.extend(formatted_games)
                except Exception as e:
                    self.logger.warning(f"Error fetching games for {date_str}: {e}")
                
                current_dt += timedelta(days=1)
            
            # Apply limit if specified
            if limit and limit > 0:
                all_games = all_games[:limit]
            
            self.logger.info(f"Fetched {len(all_games)} historical games for {sport}")
            return all_games
            
        except Exception as e:
            self.logger.error(f"Error fetching historical games: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
            return []
    
    def _format_game(self, game: Dict[str, Any], sport: str) -> Dict[str, Any]:
        """
        Format a game from OmegaSports format to validation lab format.
        
        Args:
            game: Game dictionary from OmegaSports
            sport: Sport name
        
        Returns:
            Formatted game dictionary
        """
        # Extract team names
        home_team_data = game.get("home_team", {})
        away_team_data = game.get("away_team", {})
        
        home_team = home_team_data.get("name", "") if isinstance(home_team_data, dict) else str(home_team_data)
        away_team = away_team_data.get("name", "") if isinstance(away_team_data, dict) else str(away_team_data)
        
        # Format date
        date_str = game.get("date", "")
        if date_str:
            try:
                from datetime import datetime
                # Parse ISO format and convert to YYYY-MM-DD
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                date_str = dt.strftime("%Y-%m-%d")
            except (ValueError, AttributeError):
                pass
        
        # Format game for validation lab
        formatted = {
            "game_id": game.get("game_id", ""),
            "date": date_str,
            "sport": sport.upper(),
            "league": sport.upper(),
            "home_team": home_team,
            "away_team": away_team,
            "home_score": None,
            "away_score": None,
            "moneyline": None,
            "spread": None,
            "total": None,
        }
        
        # Try to extract odds if available
        odds = game.get("odds", {})
        if odds:
            if isinstance(odds, dict):
                # Extract spread and total from odds
                spread = odds.get("spread")
                total = odds.get("over_under")
                
                if spread:
                    formatted["spread"] = {"home": spread}
                if total:
                    formatted["total"] = {"over": total, "under": total}
        
        return formatted
    
    def fetch_season_games(self, sport: str, season: int) -> List[Dict[str, Any]]:
        """
        Fetch games for a season.
        
        Args:
            sport: Sport name
            season: Season year
        
        Returns:
            List of game dictionaries
        """
        # Stub implementation
        return []

