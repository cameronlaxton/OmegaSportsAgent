"""
The Odds API Client - CRITICAL for betting system validation.

Provides historical betting lines that are currently missing (all set to None).
Without this, you cannot properly backtest the Omega betting model.

API Documentation: https://the-odds-api.com/liveapi/guides/v4/
"""

import os
import requests
import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class TheOddsAPIClient:
    """
    Client for The Odds API - provides historical betting lines.
    
    This is CRITICAL for the validation lab because:
    1. Current system has NO betting lines (all None)
    2. Cannot calculate edge without market odds
    3. Cannot validate ROI without actual lines
    4. Cannot backtest betting strategies
    """
    
    BASE_URL = "https://api.the-odds-api.com/v4"
    
    # Sport key mapping
    SPORT_MAPPING = {
        "NBA": "basketball_nba",
        "NFL": "americanfootball_nfl",
        "NCAAB": "basketball_ncaab",
        "NCAAF": "americanfootball_ncaaf",
        "NHL": "icehockey_nhl",
        "MLB": "baseball_mlb"
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize The Odds API client.
        
        Args:
            api_key: The Odds API key (or will read from THE_ODDS_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("THE_ODDS_API_KEY")
        if not self.api_key:
            logger.warning("THE_ODDS_API_KEY not set - betting lines will not be available")
        else:
            logger.info("✓ The Odds API client initialized")
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'OmegaSports-Validation-Lab/1.0'
        })
        self.rate_limit_delay = 1.0  # 1 second between requests
        self.last_request_time = 0
    
    def _rate_limit(self):
        """Enforce rate limiting."""
        now = time.time()
        time_since_last = now - self.last_request_time
        if time_since_last < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - time_since_last)
        self.last_request_time = time.time()
    
    def get_historical_odds(
        self,
        sport: str,
        date: str,
        markets: Optional[List[str]] = None,
        regions: str = "us"
    ) -> List[Dict[str, Any]]:
        """
        Fetch historical odds for a specific date.
        
        Args:
            sport: Sport name (NBA, NFL, etc.)
            date: Date in YYYY-MM-DD format
            markets: List of markets (h2h=moneyline, spreads, totals)
            regions: Regions (us, uk, eu, au)
        
        Returns:
            List of games with betting odds
        """

        if not self.api_key:
            logger.debug("No API key - skipping odds fetch")
            return []
        
        if markets is None:
            markets = ["h2h", "spreads", "totals"]  # All betting markets
        
        # Map sport to API key
        api_sport = self.SPORT_MAPPING.get(sport.upper())
        if not api_sport:
            logger.warning(f"Sport {sport} not supported by The Odds API")
            return []
        
        self._rate_limit()
        
        try:
            # Note: Historical odds require a paid plan with historical data access
            # For testing, we'll try the current odds endpoint
            url = f"{self.BASE_URL}/sports/{api_sport}/odds"
            params = {
                "apiKey": self.api_key,
                "regions": regions,
                "markets": ",".join(markets),
                "oddsFormat": "american",  # American odds format (-110, +150, etc.)
            }
            
            # Try to get historical data if available (requires historical access plan)
            # Otherwise fall back to current/upcoming games
            try:
                hist_url = f"{self.BASE_URL}/historical/sports/{api_sport}/odds"
                hist_params = params.copy()
                hist_params["date"] = date + "T12:00:00Z"
                
                logger.debug(f"Trying historical endpoint: {hist_url}")
                response = self.session.get(hist_url, params=hist_params, timeout=30)
                
                if response.status_code == 401:
                    logger.warning("Historical endpoint requires authentication - trying current odds")
                    response = self.session.get(url, params=params, timeout=30)
                elif response.status_code == 404:
                    # Historical endpoint not available, use current odds
                    logger.warning(f"Historical odds not available for {date}, using current odds")
                    response = self.session.get(url, params=params, timeout=30)
                elif response.status_code == 403:
                    logger.warning("Historical data not included in API plan - using current odds")
                    response = self.session.get(url, params=params, timeout=30)
            except Exception as e:
                # Fall back to current odds
                logger.warning(f"Historical fetch failed ({e}), using current odds")
                response = self.session.get(url, params=params, timeout=30)
            
            # Check remaining requests
            remaining = response.headers.get('x-requests-remaining')
            if remaining:
                logger.debug(f"The Odds API requests remaining: {remaining}")
            
            if response.status_code == 401:
                logger.error(f"The Odds API authentication failed (Status: {response.status_code})")
                logger.error(f"Response: {response.text[:200]}")
                return []
            elif response.status_code == 422:
                logger.warning(f"Historical data not available for {date}")
                return []
            
            response.raise_for_status()
            data = response.json()
            
            # Handle both historical response format and current odds format
            if isinstance(data, dict) and 'data' in data:
                games_data = data.get('data', [])
            else:
                games_data = data if isinstance(data, list) else []
            
            logger.info(f"✓ Fetched odds for {len(games_data)} {sport} games on {date}")
            
            return self._parse_odds_response(games_data)
            
        except requests.RequestException as e:
            logger.error(f"Error fetching odds from The Odds API: {e}")
            return []

    def fetch_historical_odds(
        self,
        sport: str,
        date: str,
        markets: Optional[List[str]] = None,
        regions: str = "us"
    ) -> List[Dict[str, Any]]:
        """Compatibility wrapper used by older scripts."""
        return self.get_historical_odds(
            sport=sport,
            date=date,
            markets=markets,
            regions=regions
        )
    
    def _parse_odds_response(self, data: List[Dict]) -> List[Dict[str, Any]]:
        """Parse The Odds API response into our format."""
        parsed_games = []
        
        for game in data:
            try:
                # Extract teams
                home_team = game.get("home_team")
                away_team = game.get("away_team")
                commence_time = game.get("commence_time")
                
                if not home_team or not away_team:
                    continue
                
                # Extract bookmaker odds (average across bookmakers)
                bookmakers = game.get("bookmakers", [])
                if not bookmakers:
                    logger.debug(f"No bookmakers data for {away_team} @ {home_team}")
                    continue
                
                # Aggregate odds from all bookmakers
                moneyline_home_list = []
                moneyline_away_list = []
                spread_line_list = []
                spread_home_odds_list = []
                spread_away_odds_list = []
                total_line_list = []
                over_odds_list = []
                under_odds_list = []
                
                for bookmaker in bookmakers:
                    markets = bookmaker.get("markets", [])
                    
                    for market in markets:
                        market_key = market.get("key")
                        outcomes = market.get("outcomes", [])
                        
                        if market_key == "h2h":  # Moneyline
                            for outcome in outcomes:
                                team = outcome.get("name")
                                price = outcome.get("price")
                                if price and team == home_team:
                                    moneyline_home_list.append(price)
                                elif price and team == away_team:
                                    moneyline_away_list.append(price)
                        
                        elif market_key == "spreads":  # Point spread
                            for outcome in outcomes:
                                team = outcome.get("name")
                                point = outcome.get("point")
                                price = outcome.get("price")
                                if team == home_team and point is not None:
                                    spread_line_list.append(point)
                                    if price:
                                        spread_home_odds_list.append(price)
                                elif team == away_team and price:
                                    spread_away_odds_list.append(price)
                        
                        elif market_key == "totals":  # Over/Under
                            for outcome in outcomes:
                                name = outcome.get("name")
                                point = outcome.get("point")
                                price = outcome.get("price")
                                if name == "Over" and point is not None:
                                    total_line_list.append(point)
                                    if price:
                                        over_odds_list.append(price)
                                elif name == "Under" and price:
                                    under_odds_list.append(price)
                
                # Calculate averages
                def avg(lst):
                    return sum(lst) / len(lst) if lst else None
                
                parsed_game = {
                    "home_team": home_team,
                    "away_team": away_team,
                    "commence_time": commence_time,
                    "num_bookmakers": len(bookmakers),
                    "moneyline": {
                        "home": int(avg(moneyline_home_list)) if moneyline_home_list else None,
                        "away": int(avg(moneyline_away_list)) if moneyline_away_list else None
                    },
                    "spread": {
                        "line": round(avg(spread_line_list), 1) if spread_line_list else None,
                        "home_odds": int(avg(spread_home_odds_list)) if spread_home_odds_list else None,
                        "away_odds": int(avg(spread_away_odds_list)) if spread_away_odds_list else None
                    },
                    "total": {
                        "line": round(avg(total_line_list), 1) if total_line_list else None,
                        "over_odds": int(avg(over_odds_list)) if over_odds_list else None,
                        "under_odds": int(avg(under_odds_list)) if under_odds_list else None
                    }
                }
                
                parsed_games.append(parsed_game)
                
            except Exception as e:
                logger.debug(f"Error parsing odds for game: {e}")
                continue
        
        return parsed_games
    
    def enrich_game_with_odds(
        self,
        game: Dict[str, Any],
        odds_cache: Optional[Dict[str, List[Dict]]] = None
    ) -> Dict[str, Any]:
        """
        Enrich a game dictionary with betting odds.
        
        Takes a game from ESPN (which has no odds) and adds
        actual market odds from The Odds API.
        
        Args:
            game: Game dictionary without odds
            odds_cache: Optional cache of odds by date to avoid repeated API calls
        
        Returns:
            Game dictionary with odds added
        """
        if not self.api_key:
            return game
        
        sport = game.get("sport")
        date = game.get("date")
        home_team = game.get("home_team")
        away_team = game.get("away_team")
        
        if not all([sport, date, home_team, away_team]):
            return game
        
        # Check cache first
        if odds_cache and date in odds_cache:
            odds_games = odds_cache[date]
        else:
            # Fetch odds for this date
            odds_games = self.get_historical_odds(sport, date)
            if odds_cache is not None:
                odds_cache[date] = odds_games
        
        # Match game by teams (fuzzy matching for team name variations)
        for odds_game in odds_games:
            odds_home = odds_game["home_team"]
            odds_away = odds_game["away_team"]
            
            # Simple matching - can be made more sophisticated
            if (self._teams_match(odds_home, home_team) and 
                self._teams_match(odds_away, away_team)):
                # Found matching game - add odds
                game["moneyline"] = odds_game["moneyline"]
                game["spread"] = odds_game["spread"]
                game["total"] = odds_game["total"]
                game["num_bookmakers"] = odds_game.get("num_bookmakers", 0)
                logger.debug(f"✓ Added betting lines for {away_team} @ {home_team}")
                break
        
        return game
    
    def _teams_match(self, team1: str, team2: str) -> bool:
        """Check if two team names match (handles variations)."""
        # Normalize team names
        t1 = team1.lower().strip()
        t2 = team2.lower().strip()
        
        # Exact match
        if t1 == t2:
            return True
        
        # Remove common words
        for word in ['the', 'fc', 'sc']:
            t1 = t1.replace(word, '').strip()
            t2 = t2.replace(word, '').strip()
        
        # Check if one contains the other
        return t1 in t2 or t2 in t1
    
    def check_usage(self) -> Optional[Dict[str, Any]]:
        """
        Check API usage and remaining requests.
        
        Returns:
            Dictionary with usage information or None
        """
        if not self.api_key:
            return None
        
        try:
            url = f"{self.BASE_URL}/sports"
            params = {"apiKey": self.api_key}
            
            response = self.session.get(url, params=params, timeout=10)
            
            usage = {
                "requests_remaining": response.headers.get('x-requests-remaining'),
                "requests_used": response.headers.get('x-requests-used')
            }
            
            logger.info(f"The Odds API usage: {usage}")
            return usage
            
        except Exception as e:
            logger.error(f"Error checking API usage: {e}")
            return None
    
    def fetch_player_props(
        self,
        sport: str,
        date: str,
        markets: Optional[List[str]] = None,
        regions: str = "us"
    ) -> List[Dict[str, Any]]:
        """
        Fetch player prop odds for a specific date.
        
        Args:
            sport: Sport name (NBA, NFL, etc.)
            date: Date in YYYY-MM-DD format
            markets: List of player prop markets (player_points, player_rebounds, etc.)
            regions: Regions (us, uk, eu, au)
        
        Returns:
            List of player props with betting lines
        """
        if not self.api_key:
            logger.debug("No API key - skipping player props fetch")
            return []
        
        # Default markets based on sport
        if markets is None:
            if sport.upper() in ["NBA", "NCAAB"]:
                markets = [
                    "player_points",
                    "player_rebounds",
                    "player_assists",
                    "player_threes",
                    "player_blocks",
                    "player_steals"
                ]
            elif sport.upper() in ["NFL", "NCAAF"]:
                markets = [
                    "player_pass_yds",
                    "player_pass_tds",
                    "player_pass_attempts",
                    "player_pass_completions",
                    "player_rush_yds",
                    "player_rush_attempts",
                    "player_rush_tds",
                    "player_receptions",
                    "player_reception_yds",
                    "player_reception_tds",
                    "player_interceptions"
                ]
            else:
                logger.warning(f"No default player prop markets for sport: {sport}")
                return []
        
        # Map sport to API key
        api_sport = self.SPORT_MAPPING.get(sport.upper())
        if not api_sport:
            logger.warning(f"Sport {sport} not supported by The Odds API")
            return []
        
        all_props = []
        
        # Fetch each market separately (The Odds API may require this)
        for market in markets:
            self._rate_limit()
            
            try:
                url = f"{self.BASE_URL}/sports/{api_sport}/odds"
                params = {
                    "apiKey": self.api_key,
                    "regions": regions,
                    "markets": market,
                    "oddsFormat": "american"
                }
                
                # Try historical endpoint first
                try:
                    hist_url = f"{self.BASE_URL}/historical/sports/{api_sport}/odds"
                    hist_params = params.copy()
                    hist_params["date"] = date + "T12:00:00Z"
                    
                    response = self.session.get(hist_url, params=hist_params, timeout=30)
                    
                    if response.status_code in [401, 403, 404]:
                        # Fall back to current odds
                        response = self.session.get(url, params=params, timeout=30)
                except Exception:
                    # Fall back to current odds
                    response = self.session.get(url, params=params, timeout=30)
                
                # Check remaining requests
                remaining = response.headers.get('x-requests-remaining')
                if remaining:
                    logger.debug(f"The Odds API requests remaining: {remaining}")
                
                if response.status_code == 401:
                    logger.error(f"The Odds API authentication failed")
                    continue
                elif response.status_code == 422:
                    logger.warning(f"Player props not available for {date}")
                    continue
                
                response.raise_for_status()
                data = response.json()
                
                # Handle response format
                if isinstance(data, dict) and 'data' in data:
                    games_data = data.get('data', [])
                else:
                    games_data = data if isinstance(data, list) else []
                
                # Parse player props from response
                props = self._parse_player_props_response(games_data, market, date)
                all_props.extend(props)
                
                logger.info(f"✓ Fetched {len(props)} {market} props for {sport} on {date}")
                
            except requests.RequestException as e:
                logger.error(f"Error fetching player props for {market}: {e}")
                continue
        
        logger.info(f"✓ Total player props fetched: {len(all_props)}")
        return all_props
    
    def _parse_player_props_response(
        self,
        data: List[Dict],
        market: str,
        date: str
    ) -> List[Dict[str, Any]]:
        """
        Parse player props response from The Odds API.
        
        Args:
            data: API response data
            market: Market type (e.g., player_points)
            date: Game date
        
        Returns:
            List of parsed player prop dictionaries
        """
        props = []
        
        for game in data:
            game_id = game.get("id")
            home_team = game.get("home_team", "")
            away_team = game.get("away_team", "")
            
            # Extract bookmaker data
            bookmakers = game.get("bookmakers", [])
            
            for bookmaker in bookmakers:
                markets_data = bookmaker.get("markets", [])
                
                for market_data in markets_data:
                    if market_data.get("key") != market:
                        continue
                    
                    # Each outcome represents a player prop
                    outcomes = market_data.get("outcomes", [])
                    
                    for outcome in outcomes:
                        player_name = outcome.get("description", "")
                        prop_point = outcome.get("point")  # The line (e.g., 27.5 points)
                        prop_price = outcome.get("price")  # American odds
                        
                        # Determine over/under
                        outcome_name = outcome.get("name", "").lower()
                        is_over = "over" in outcome_name
                        
                        # Create prop dictionary
                        prop = {
                            "prop_id": f"{game_id}_{player_name}_{market}".replace(" ", "_"),
                            "game_id": game_id,
                            "date": date,
                            "home_team": home_team,
                            "away_team": away_team,
                            "player_name": player_name,
                            "prop_type": market.replace("player_", ""),
                            "line": prop_point,
                            "bookmaker": bookmaker.get("title", ""),
                            "timestamp": game.get("commence_time", "")
                        }
                        
                        if is_over:
                            prop["over_line"] = prop_point
                            prop["over_odds"] = prop_price
                        else:
                            prop["under_line"] = prop_point
                            prop["under_odds"] = prop_price
                        
                        props.append(prop)
        
        return props
