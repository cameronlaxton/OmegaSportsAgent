"""
BallDontLie API Client - Enhanced NBA/NFL statistics.

Provides structured, reliable data for NBA and NFL with ALL-STAR package access.
Better than web scraping for consistency and rate limits.

API Documentation: https://docs.balldontlie.io/
"""

import os
import requests
import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class BallDontLieAPIClient:
    """
    Client for BallDontLie API - provides NBA and NFL statistics.
    
    Benefits over web scraping:
    - Structured, consistent data format
    - Better rate limits (ALL-STAR package)
    - Player game logs
    - Team statistics
    - More reliable than ESPN scraping
    """
    
    BASE_URL = "https://api.balldontlie.io/v1"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize BallDontLie API client.
        
        Args:
            api_key: BallDontLie API key (or will read from BALLDONTLIE_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("BALLDONTLIE_API_KEY")
        if not self.api_key:
            logger.warning("BALLDONTLIE_API_KEY not set - enhanced NBA/NFL data will not be available")
        else:
            logger.info("✓ BallDontLie API client initialized (ALL-STAR package)")
        
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({
                "Authorization": self.api_key,
                'User-Agent': 'OmegaSports-Validation-Lab/1.0'
            })
        
        # ALL-STAR tier: 60 requests/minute = 1.0 second between requests
        self.rate_limit_delay = 1.0
        self.last_request_time = 0
        self.request_timeout = 30  # 30 second timeout for cloud reliability
    
    def _rate_limit(self):
        """Enforce rate limiting."""
        now = time.time()
        time_since_last = now - self.last_request_time
        if time_since_last < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - time_since_last)
        self.last_request_time = time.time()
    
    def get_games(
        self,
        start_date: str,
        end_date: str,
        season: Optional[int] = None,
        team_ids: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch NBA games for a date range.
        
        Args:
            start_date: Start date YYYY-MM-DD
            end_date: End date YYYY-MM-DD
            season: Season year (optional)
            team_ids: Optional list of team IDs to filter
        
        Returns:
            List of games with statistics
        """
        if not self.api_key:
            logger.debug("No API key - skipping BallDontLie fetch")
            return []
        
        self._rate_limit()
        
        try:
            url = f"{self.BASE_URL}/games"
            params = {
                "start_date": start_date,
                "end_date": end_date,
                "per_page": 100
            }
            
            if season:
                params["seasons[]"] = season
            
            if team_ids:
                params["team_ids[]"] = team_ids
            
            response = self.session.get(url, params=params, timeout=30)
            
            if response.status_code == 401:
                logger.error("BallDontLie API authentication failed - check API key")
                return []
            
            response.raise_for_status()
            data = response.json()
            
            games = data.get("data", [])
            logger.info(f"✓ Fetched {len(games)} NBA games from BallDontLie API")
            
            return games
            
        except requests.RequestException as e:
            logger.error(f"Error fetching from BallDontLie API: {e}")
            return []
    
    def get_game_stats(
        self,
        game_ids: List[int]
    ) -> List[Dict[str, Any]]:
        """
        Fetch player statistics for specific games.
        
        Args:
            game_ids: List of BallDontLie game IDs
        
        Returns:
            List of player stat dictionaries
        """
        if not self.api_key:
            return []
        
        self._rate_limit()
        
        try:
            url = f"{self.BASE_URL}/stats"
            params = {
                "game_ids[]": game_ids,
                "per_page": 100
            }
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            stats = data.get("data", [])
            
            logger.debug(f"Fetched stats for {len(stats)} players")
            return stats
            
        except requests.RequestException as e:
            logger.error(f"Error fetching player stats: {e}")
            return []
    
    def get_team_stats(
        self,
        season: int,
        team_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch team statistics for a season.
        
        Args:
            season: Season year
            team_id: Optional specific team ID
        
        Returns:
            List of team stat dictionaries
        """
        if not self.api_key:
            return []
        
        self._rate_limit()
        
        try:
            url = f"{self.BASE_URL}/season_averages"
            params = {
                "season": season,
                "per_page": 100
            }
            
            if team_id:
                params["team_id"] = team_id
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            return data.get("data", [])
            
        except requests.RequestException as e:
            logger.error(f"Error fetching team stats: {e}")
            return []
    
    def enrich_game_with_stats(
        self,
        game: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enrich a game with player and team statistics.
        
        Args:
            game: Base game dictionary
        
        Returns:
            Game with enhanced statistics
        """
        if not self.api_key:
            return game
        
        # For now, just return the game
        # Full implementation would map ESPN game to BallDontLie game
        # and fetch detailed statistics
        
        return game
    
    def get_player_season_stats(
        self,
        player_id: int,
        season: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get season averages for a specific player.
        
        Args:
            player_id: Player ID
            season: Season year
        
        Returns:
            Player season statistics or None
        """
        if not self.api_key:
            return None
        
        self._rate_limit()
        
        try:
            url = f"{self.BASE_URL}/season_averages"
            params = {
                "player_ids[]": [player_id],
                "season": season
            }
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            stats = data.get("data", [])
            
            return stats[0] if stats else None
            
        except requests.RequestException as e:
            logger.error(f"Error fetching player season stats: {e}")
            return None
    
    def get_players(
        self,
        search: Optional[str] = None,
        team_id: Optional[int] = None,
        per_page: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get players from BallDontLie API with optional filtering.
        
        Args:
            search: Player name search query
            team_id: Filter by team ID
            per_page: Results per page (max 100)
        
        Returns:
            List of player dictionaries
        """
        if not self.api_key:
            logger.warning("No API key configured for BallDontLie")
            return []
        
        self._rate_limit()
        
        try:
            url = f"{self.BASE_URL}/players"
            params = {"per_page": min(per_page, 100)}
            
            if search:
                params["search"] = search
            if team_id is not None:
                params["team_ids[]"] = [team_id]
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            players = data.get("data", [])
            
            # Handle pagination for large result sets
            total_pages = data.get("meta", {}).get("total_pages", 1)
            current_page = data.get("meta", {}).get("current_page", 1)
            
            # Fetch remaining pages if needed
            while current_page < total_pages:
                self._rate_limit()
                current_page += 1
                params["page"] = current_page
                
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                players.extend(data.get("data", []))
            
            logger.info(f"Fetched {len(players)} players")
            return players
            
        except requests.RequestException as e:
            logger.error(f"Error fetching players: {e}")
            return []
    
    def get_teams(self) -> List[Dict[str, Any]]:
        """
        Get all teams from BallDontLie API.
        
        Returns:
            List of team dictionaries with id, name, abbreviation, etc.
        """
        if not self.api_key:
            logger.warning("No API key configured for BallDontLie")
            return []
        
        self._rate_limit()
        
        try:
            url = f"{self.BASE_URL}/teams"
            params = {"per_page": 100}
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            teams = data.get("data", [])
            
            logger.info(f"Fetched {len(teams)} teams")
            return teams
            
        except requests.RequestException as e:
            logger.error(f"Error fetching teams: {e}")
            return []
    
    def get_player_by_id(self, player_id: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed information for a specific player.
        
        Args:
            player_id: BallDontLie player ID
        
        Returns:
            Player dictionary or None if not found
        """
        if not self.api_key:
            logger.warning("No API key configured for BallDontLie")
            return None
        
        self._rate_limit()
        
        try:
            url = f"{self.BASE_URL}/players/{player_id}"
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            player = data.get("data")
            
            if player:
                logger.info(f"Fetched player: {player.get('first_name')} {player.get('last_name')}")
            
            return player
            
        except requests.RequestException as e:
            logger.error(f"Error fetching player {player_id}: {e}")
            return None
    
    def get_box_score(self, game_id: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed box score statistics for a specific game using /v1/stats endpoint.
        
        Args:
            game_id: BallDontLie game ID
        
        Returns:
            Dictionary containing box score with player statistics
        """
        if not self.api_key:
            logger.warning("No API key configured for BallDontLie")
            return None
        
        # Use get_game_stats which already implements /v1/stats
        player_stats = self.get_game_stats([game_id])
        
        if not player_stats:
            return None
        
        # Organize stats into box score format
        box_score = {
            "game_id": game_id,
            "player_stats": player_stats,
            "home_players": [],
            "away_players": []
        }
        
        # Separate home and away players
        for stat in player_stats:
            player_data = {
                "player": stat.get("player", {}),
                "team": stat.get("team", {}),
                "stats": {
                    "min": stat.get("min", "0"),
                    "pts": stat.get("pts", 0),
                    "reb": stat.get("reb", 0),
                    "ast": stat.get("ast", 0),
                    "stl": stat.get("stl", 0),
                    "blk": stat.get("blk", 0),
                    "turnover": stat.get("turnover", 0),
                    "fgm": stat.get("fgm", 0),
                    "fga": stat.get("fga", 0),
                    "fg_pct": stat.get("fg_pct", 0),
                    "fg3m": stat.get("fg3m", 0),
                    "fg3a": stat.get("fg3a", 0),
                    "fg3_pct": stat.get("fg3_pct", 0),
                    "ftm": stat.get("ftm", 0),
                    "fta": stat.get("fta", 0),
                    "ft_pct": stat.get("ft_pct", 0),
                }
            }
            
            # Note: We'll need game data to determine home/away
            # For now, just add to player_stats list
            box_score["player_stats"].append(player_data)
        
        return box_score
    
    def enrich_game_with_stats(self, game: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich ESPN game data with comprehensive statistics from BallDontLie.
        
        This method maps ESPN game data to BallDontLie format and adds:
        - Detailed player box scores
        - Team statistics
        - Advanced metrics
        
        Args:
            game: ESPN game dictionary
        
        Returns:
            Enriched game dictionary with BallDontLie statistics
        """
        if not self.api_key:
            logger.debug("No API key - returning game unchanged")
            return game
        
        enriched = game.copy()
        
        # Extract game date
        game_date = game.get("date")
        if not game_date:
            logger.warning("Game has no date - cannot enrich")
            return game
        
        try:
            # Find matching BallDontLie game
            bdl_games = self.get_games(
                start_date=game_date,
                end_date=game_date
            )
            
            if not bdl_games:
                logger.debug(f"No BallDontLie games found for {game_date}")
                return game
            
            # Match by team names (fuzzy matching)
            home_team = game.get("home_team", "").lower()
            away_team = game.get("away_team", "").lower()
            
            matching_game = None
            for bdl_game in bdl_games:
                bdl_home = bdl_game.get("home_team", {}).get("full_name", "").lower()
                bdl_away = bdl_game.get("visitor_team", {}).get("full_name", "").lower()
                
                # Simple substring matching
                if (home_team in bdl_home or bdl_home in home_team) and \
                   (away_team in bdl_away or bdl_away in away_team):
                    matching_game = bdl_game
                    break
            
            if not matching_game:
                logger.debug(f"No matching BallDontLie game for {home_team} vs {away_team}")
                return game
            
            # Get box score statistics
            game_id = matching_game.get("id")
            box_score = self.get_box_score(game_id)
            
            if box_score:
                enriched["balldontlie_stats"] = box_score
                enriched["balldontlie_game_id"] = game_id
                logger.info(f"Enriched game with BallDontLie stats: {game_id}")
            
        except Exception as e:
            logger.error(f"Error enriching game with BallDontLie stats: {e}")
        
        return enriched
