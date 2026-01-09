"""
ESPN API Direct Scraper for Historical Data.

This module directly calls ESPN's APIs to fetch historical game data,
bypassing Basketball Reference CloudFlare issues.

ESPN provides comprehensive historical data via their undocumented APIs.
"""

import logging
import time
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class ESPNHistoricalScraper:
    """
    Scraper for ESPN's historical game data APIs.
    
    ESPN provides free historical data via their internal APIs that power
    their website. This is REAL data, not mocked.
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        })
        self.base_delay = 1.0  # 1 second between requests
    
    def fetch_nba_games(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        Fetch NBA games for a date range from ESPN API.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
        
        Returns:
            List of game dictionaries with real historical data
        """
        games = []
        current_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        logger.info(f"Fetching NBA games from ESPN API: {start_date} to {end_date}")
        
        while current_date <= end_dt:
            date_str = current_date.strftime("%Y%m%d")
            
            try:
                # ESPN Scoreboard API
                url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
                params = {
                    "dates": date_str,
                    "limit": 100
                }
                
                time.sleep(self.base_delay)
                response = self.session.get(url, params=params, timeout=15)
                response.raise_for_status()
                
                data = response.json()
                
                if "events" in data:
                    for event in data["events"]:
                        game = self._parse_espn_nba_game(event)
                        if game:
                            games.append(game)
                
                logger.debug(f"Fetched {len(data.get('events', []))} games for {current_date.strftime('%Y-%m-%d')}")
                
            except Exception as e:
                logger.warning(f"Error fetching games for {current_date.strftime('%Y-%m-%d')}: {e}")
            
            current_date += timedelta(days=1)
        
        logger.info(f"Total NBA games fetched from ESPN: {len(games)}")
        return games
    
    def fetch_nfl_games(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        Fetch NFL games for a date range from ESPN API.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
        
        Returns:
            List of game dictionaries
        """
        games = []
        current_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        logger.info(f"Fetching NFL games from ESPN API: {start_date} to {end_date}")
        
        while current_date <= end_dt:
            date_str = current_date.strftime("%Y%m%d")
            
            try:
                url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
                params = {
                    "dates": date_str,
                    "limit": 100
                }
                
                time.sleep(self.base_delay)
                response = self.session.get(url, params=params, timeout=15)
                response.raise_for_status()
                
                data = response.json()
                
                if "events" in data:
                    for event in data["events"]:
                        game = self._parse_espn_nfl_game(event)
                        if game:
                            games.append(game)
                
                logger.debug(f"Fetched {len(data.get('events', []))} NFL games for {current_date.strftime('%Y-%m-%d')}")
                
            except Exception as e:
                logger.warning(f"Error fetching NFL games for {current_date.strftime('%Y-%m-%d')}: {e}")
            
            current_date += timedelta(days=1)
        
        logger.info(f"Total NFL games fetched from ESPN: {len(games)}")
        return games
    
    def _parse_espn_nba_game(self, event: Dict) -> Optional[Dict[str, Any]]:
        """Parse NBA game data from ESPN API response."""
        try:
            game_id = event.get("id", "")
            date_str = event.get("date", "")
            
            # Parse date
            if date_str:
                date_obj = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                game_date = date_obj.strftime("%Y-%m-%d")
            else:
                return None
            
            # Get teams
            competitions = event.get("competitions", [])
            if not competitions:
                return None
            
            competition = competitions[0]
            competitors = competition.get("competitors", [])
            
            if len(competitors) < 2:
                return None
            
            # Determine home/away
            home_team = None
            away_team = None
            home_score = None
            away_score = None
            
            for competitor in competitors:
                team = competitor.get("team", {})
                team_name = team.get("displayName", "")
                score = competitor.get("score", "")
                is_home = competitor.get("homeAway", "") == "home"
                
                if is_home:
                    home_team = team_name
                    home_score = int(score) if score and score.isdigit() else None
                else:
                    away_team = team_name
                    away_score = int(score) if score and score.isdigit() else None
            
            if not home_team or not away_team:
                return None
            
            return {
                "game_id": f"nba_espn_{game_id}",
                "date": game_date,
                "sport": "NBA",
                "league": "NBA",
                "home_team": home_team,
                "away_team": away_team,
                "home_score": home_score,
                "away_score": away_score,
                "moneyline": None,
                "spread": None,
                "total": None,
                "source": "espn-api"
            }
            
        except Exception as e:
            logger.debug(f"Error parsing ESPN NBA game: {e}")
            return None
    
    def _parse_espn_nfl_game(self, event: Dict) -> Optional[Dict[str, Any]]:
        """Parse NFL game data from ESPN API response."""
        try:
            game_id = event.get("id", "")
            date_str = event.get("date", "")
            
            if date_str:
                date_obj = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                game_date = date_obj.strftime("%Y-%m-%d")
            else:
                return None
            
            competitions = event.get("competitions", [])
            if not competitions:
                return None
            
            competition = competitions[0]
            competitors = competition.get("competitors", [])
            
            if len(competitors) < 2:
                return None
            
            home_team = None
            away_team = None
            home_score = None
            away_score = None
            
            for competitor in competitors:
                team = competitor.get("team", {})
                team_name = team.get("displayName", "")
                score = competitor.get("score", "")
                is_home = competitor.get("homeAway", "") == "home"
                
                if is_home:
                    home_team = team_name
                    home_score = int(score) if score and score.isdigit() else None
                else:
                    away_team = team_name
                    away_score = int(score) if score and score.isdigit() else None
            
            if not home_team or not away_team:
                return None
            
            return {
                "game_id": f"nfl_espn_{game_id}",
                "date": game_date,
                "sport": "NFL",
                "league": "NFL",
                "home_team": home_team,
                "away_team": away_team,
                "home_score": home_score,
                "away_score": away_score,
                "moneyline": None,
                "spread": None,
                "total": None,
                "source": "espn-api"
            }
            
        except Exception as e:
            logger.debug(f"Error parsing ESPN NFL game: {e}")
            return None
    
    def fetch_season_games(self, sport: str, year: int) -> List[Dict[str, Any]]:
        """
        Fetch all games for a season.
        
        Args:
            sport: Sport code (NBA, NFL)
            year: Season year
        
        Returns:
            List of games for the season
        """
        sport_upper = sport.upper()
        
        # Determine season date range
        if sport_upper == "NBA":
            # NBA season runs October to June
            start_date = f"{year-1}-10-01"
            end_date = f"{year}-06-30"
            return self.fetch_nba_games(start_date, end_date)
        elif sport_upper == "NFL":
            # NFL season runs September to February
            start_date = f"{year}-09-01"
            end_date = f"{year+1}-02-28"
            return self.fetch_nfl_games(start_date, end_date)
        else:
            logger.warning(f"Sport {sport_upper} not supported for ESPN scraping")
            return []
