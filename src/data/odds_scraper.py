"""
Odds Scraper Module

Functions to get odds data using The Odds API (free tier) with fallback scraping.
"""

import os
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from src.foundation.api_config import get_odds_api_key

logger = logging.getLogger(__name__)

ODDS_API_BASE_URL = "https://api.the-odds-api.com/v4"
ODDS_API_KEY = get_odds_api_key()

LEAGUE_SPORT_MAPPING = {
    "NBA": "basketball_nba",
    "NFL": "americanfootball_nfl",
    "MLB": "baseball_mlb",
    "NHL": "icehockey_nhl",
    "NCAAB": "basketball_ncaab",
    "NCAAF": "americanfootball_ncaaf",
}

REQUEST_TIMEOUT = 10
RATE_LIMIT_DELAY = 1.0
_last_request_time = 0


def _rate_limit():
    """Enforce rate limiting between requests."""
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < RATE_LIMIT_DELAY:
        time.sleep(RATE_LIMIT_DELAY - elapsed)
    _last_request_time = time.time()


def _get_sport_key(league: str) -> str:
    """Convert league name to Odds API sport key."""
    return LEAGUE_SPORT_MAPPING.get(league.upper(), f"basketball_{league.lower()}")


def _make_api_request(endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
    """Make a request to The Odds API."""
    if not ODDS_API_KEY:
        logger.warning("ODDS_API_KEY not set, API requests will fail")
        return None
    
    _rate_limit()
    
    url = f"{ODDS_API_BASE_URL}/{endpoint}"
    request_params = {"apiKey": ODDS_API_KEY}
    if params:
        request_params.update(params)
    
    try:
        response = requests.get(url, params=request_params, timeout=REQUEST_TIMEOUT)
        
        remaining = response.headers.get("x-requests-remaining", "unknown")
        logger.debug(f"Odds API requests remaining: {remaining}")
        
        if response.status_code == 401:
            logger.error("Invalid ODDS_API_KEY")
            return None
        elif response.status_code == 429:
            logger.warning("Odds API rate limit exceeded")
            return None
        elif response.status_code != 200:
            logger.error(f"Odds API error: {response.status_code}")
            return None
        
        return response.json()
    
    except requests.exceptions.Timeout:
        logger.error("Odds API request timed out")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Odds API request failed: {e}")
        return None


def get_upcoming_games(league: str) -> List[Dict[str, Any]]:
    """
    Get upcoming games with odds for a league.
    
    Args:
        league: League code (NBA, NFL, MLB, NHL, NCAAB, NCAAF)
    
    Returns:
        List of games with basic info and odds
    """
    sport_key = _get_sport_key(league)
    
    data = _make_api_request(
        f"sports/{sport_key}/odds",
        params={
            "regions": "us",
            "markets": "h2h,spreads,totals",
            "oddsFormat": "american"
        }
    )
    
    if data is None:
        logger.info(f"API unavailable, attempting fallback for {league}")
        return _scrape_upcoming_games_fallback(league)
    
    games = []
    for event in data:
        game = {
            "game_id": event.get("id", ""),
            "sport": event.get("sport_key", ""),
            "league": league.upper(),
            "commence_time": event.get("commence_time", ""),
            "home_team": event.get("home_team", ""),
            "away_team": event.get("away_team", ""),
            "bookmakers": []
        }
        
        for bookmaker in event.get("bookmakers", []):
            book_data = {
                "name": bookmaker.get("title", ""),
                "key": bookmaker.get("key", ""),
                "last_update": bookmaker.get("last_update", ""),
                "markets": {}
            }
            
            for market in bookmaker.get("markets", []):
                market_key = market.get("key", "")
                outcomes = []
                for outcome in market.get("outcomes", []):
                    outcomes.append({
                        "name": outcome.get("name", ""),
                        "price": outcome.get("price", 0),
                        "point": outcome.get("point")
                    })
                book_data["markets"][market_key] = outcomes
            
            game["bookmakers"].append(book_data)
        
        games.append(game)
    
    return games


def get_current_odds(game_id: str, league: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get current odds for a specific game.
    
    Args:
        game_id: The Odds API event ID
        league: Optional league code to narrow search
    
    Returns:
        Game odds data or None if not found
    """
    leagues_to_check = [league.upper()] if league else list(LEAGUE_SPORT_MAPPING.keys())
    
    for check_league in leagues_to_check:
        games = get_upcoming_games(check_league)
        for game in games:
            if game.get("game_id") == game_id:
                return game
    
    return None


def get_player_props(game_id: str, league: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get player props for a specific game.
    
    Note: Player props require higher API tiers. This function attempts to get them
    but will return empty list on free tier.
    
    Args:
        game_id: The Odds API event ID
        league: League code
    
    Returns:
        List of player prop markets (may be empty on free tier)
    """
    if not league:
        return []
    
    sport_key = _get_sport_key(league)
    
    prop_markets = [
        "player_points", "player_rebounds", "player_assists",
        "player_pass_yds", "player_rush_yds", "player_reception_yds"
    ]
    
    props = []
    
    for market in prop_markets:
        data = _make_api_request(
            f"sports/{sport_key}/events/{game_id}/odds",
            params={
                "regions": "us",
                "markets": market,
                "oddsFormat": "american"
            }
        )
        
        if data and isinstance(data, dict):
            for bookmaker in data.get("bookmakers", []):
                for mkt in bookmaker.get("markets", []):
                    props.append({
                        "bookmaker": bookmaker.get("title", ""),
                        "market": mkt.get("key", ""),
                        "outcomes": mkt.get("outcomes", [])
                    })
    
    return props


def _scrape_upcoming_games_fallback(league: str) -> List[Dict[str, Any]]:
    """
    Fallback scraping when API is unavailable.
    Attempts to get basic game info from public sources.
    """
    _rate_limit()
    
    games = []
    
    try:
        if league.upper() in ["NBA", "NCAAB"]:
            url = f"https://www.espn.com/{league.lower()}/scoreboard"
        elif league.upper() in ["NFL", "NCAAF"]:
            url = f"https://www.espn.com/{league.lower()}/scoreboard"
        elif league.upper() == "MLB":
            url = "https://www.espn.com/mlb/scoreboard"
        elif league.upper() == "NHL":
            url = "https://www.espn.com/nhl/scoreboard"
        else:
            return games
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        if response.status_code != 200:
            logger.warning(f"Fallback scrape failed with status {response.status_code}")
            return games
        
        soup = BeautifulSoup(response.text, "lxml")
        
        scoreboard_items = soup.find_all("section", class_="Scoreboard")
        
        for idx, item in enumerate(scoreboard_items):
            try:
                teams = item.find_all("div", class_="ScoreCell__TeamName")
                if len(teams) >= 2:
                    game = {
                        "game_id": f"fallback_{league}_{idx}_{datetime.now().strftime('%Y%m%d')}",
                        "league": league.upper(),
                        "away_team": teams[0].get_text(strip=True),
                        "home_team": teams[1].get_text(strip=True),
                        "bookmakers": [],
                        "source": "espn_fallback"
                    }
                    games.append(game)
            except Exception as e:
                logger.debug(f"Error parsing game: {e}")
                continue
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Fallback scrape request failed: {e}")
    except Exception as e:
        logger.error(f"Fallback scrape error: {e}")
    
    return games


def get_available_sports() -> List[Dict[str, Any]]:
    """
    Get list of available sports from The Odds API.
    
    Returns:
        List of sport info dictionaries
    """
    data = _make_api_request("sports")
    
    if data is None:
        return [
            {"key": v, "title": k, "active": True}
            for k, v in LEAGUE_SPORT_MAPPING.items()
        ]
    
    return data


def check_api_status() -> Dict[str, Any]:
    """
    Check Odds API status and remaining requests.
    
    Returns:
        Dictionary with API status info
    """
    if not ODDS_API_KEY:
        return {
            "status": "no_key",
            "message": "ODDS_API_KEY environment variable not set"
        }
    
    try:
        response = requests.get(
            f"{ODDS_API_BASE_URL}/sports",
            params={"apiKey": ODDS_API_KEY},
            timeout=REQUEST_TIMEOUT
        )
        
        return {
            "status": "ok" if response.status_code == 200 else "error",
            "status_code": response.status_code,
            "requests_remaining": response.headers.get("x-requests-remaining"),
            "requests_used": response.headers.get("x-requests-used")
        }
    
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
