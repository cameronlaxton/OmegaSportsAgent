"""
Injury API Module

Functions to check player availability status using ESPN injury API.
Filters out injured/inactive players before suggesting bets or running simulations.
"""

import time
import logging
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta

import requests

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 10
RATE_LIMIT_DELAY = 0.5
_last_request_time = 0

ESPN_INJURIES_BASE = "https://site.api.espn.com/apis/site/v2/sports"

LEAGUE_PATHS = {
    "NBA": "basketball/nba",
    "NFL": "football/nfl",
    "MLB": "baseball/mlb",
    "NHL": "hockey/nhl",
    "NCAAB": "basketball/mens-college-basketball",
    "NCAAF": "football/college-football",
    "WNBA": "basketball/wnba"
}

OUT_STATUSES = {
    "out", "o", "doubtful", "d", "suspended", "injured reserve", "ir",
    "day-to-day", "dtd", "questionable", "q"
}

DEFINITELY_OUT = {"out", "o", "suspended", "injured reserve", "ir"}

_injury_cache: Dict[str, Dict] = {}
_cache_timestamp: Dict[str, float] = {}
CACHE_TTL = 300


def _rate_limit():
    """Enforce rate limiting between requests."""
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < RATE_LIMIT_DELAY:
        time.sleep(RATE_LIMIT_DELAY - elapsed)
    _last_request_time = time.time()


def _get_league_path(league: str) -> str:
    """Get ESPN API path for a league."""
    return LEAGUE_PATHS.get(league.upper(), f"basketball/{league.lower()}")


def get_injuries(league: str, teams: Optional[List[str]] = None, use_cache: bool = True) -> Dict[str, Any]:
    """
    Get current injury report for a league.
    
    Args:
        league: League code (NBA, NFL, MLB, NHL, etc.)
        teams: Optional list of team abbreviations to filter
        use_cache: Whether to use cached data (default True)
    
    Returns:
        Dictionary with injury data by team
    """
    cache_key = f"{league}_{'-'.join(sorted(teams or []))}"
    
    if use_cache and cache_key in _injury_cache:
        if time.time() - _cache_timestamp.get(cache_key, 0) < CACHE_TTL:
            return _injury_cache[cache_key]
    
    _rate_limit()
    
    league_path = _get_league_path(league)
    url = f"{ESPN_INJURIES_BASE}/{league_path}/injuries"
    
    params = {}
    if teams:
        params = {"team": teams}
    
    try:
        response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        
        if response.status_code != 200:
            logger.warning(f"ESPN Injuries API returned {response.status_code}")
            return {"teams": [], "error": f"API returned {response.status_code}"}
        
        data = response.json()
        
        _injury_cache[cache_key] = data
        _cache_timestamp[cache_key] = time.time()
        
        return data
    
    except requests.exceptions.Timeout:
        logger.error("ESPN Injuries API request timed out")
        return {"teams": [], "error": "Request timed out"}
    except requests.exceptions.RequestException as e:
        logger.error(f"ESPN Injuries API request failed: {e}")
        return {"teams": [], "error": str(e)}


def get_injured_players(league: str, teams: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
    """
    Get dictionary of injured players with their status.
    
    Args:
        league: League code
        teams: Optional list of team abbreviations
    
    Returns:
        Dictionary mapping player names (lowercase) to their injury info
    """
    data = get_injuries(league, teams)
    
    injured = {}
    
    injury_list = data.get("injuries", data.get("teams", []))
    
    for team_data in injury_list:
        team_name = team_data.get("displayName", team_data.get("team", {}).get("displayName", ""))
        team_abbrev = team_data.get("abbreviation", team_data.get("team", {}).get("abbreviation", ""))
        
        for injury in team_data.get("injuries", []):
            athlete = injury.get("athlete", {})
            player_name = athlete.get("displayName", "")
            status = injury.get("status", "").lower()
            injury_type = injury.get("type", {}).get("description", "")
            if not injury_type:
                injury_type = injury.get("description", "")
            details = injury.get("details", {})
            
            if player_name:
                injured[player_name.lower()] = {
                    "name": player_name,
                    "team": team_name,
                    "team_abbrev": team_abbrev,
                    "status": status,
                    "injury_type": injury_type,
                    "side": details.get("side", ""),
                    "return_date": details.get("returnDate", ""),
                    "is_out": status in DEFINITELY_OUT,
                    "is_questionable": status in OUT_STATUSES and status not in DEFINITELY_OUT
                }
    
    return injured


def is_player_available(player_name: str, league: str, team_abbrev: Optional[str] = None) -> Dict[str, Any]:
    """
    Check if a specific player is available to play.
    
    Args:
        player_name: Player's full name
        league: League code
        team_abbrev: Optional team abbreviation for faster lookup
    
    Returns:
        Dictionary with availability status and details
    """
    teams = [team_abbrev] if team_abbrev else None
    injured = get_injured_players(league, teams)
    
    player_lower = player_name.lower()
    
    if player_lower in injured:
        injury_info = injured[player_lower]
        return {
            "available": not injury_info["is_out"],
            "status": injury_info["status"],
            "injury_type": injury_info["injury_type"],
            "is_questionable": injury_info["is_questionable"],
            "details": injury_info
        }
    
    for name, info in injured.items():
        if player_lower in name or name in player_lower:
            return {
                "available": not info["is_out"],
                "status": info["status"],
                "injury_type": info["injury_type"],
                "is_questionable": info["is_questionable"],
                "details": info
            }
    
    return {
        "available": True,
        "status": "active",
        "injury_type": None,
        "is_questionable": False,
        "details": None
    }


def filter_available_players(players: List[Dict[str, Any]], league: str) -> List[Dict[str, Any]]:
    """
    Filter a list of players to only include those available to play.
    
    Args:
        players: List of player dictionaries (must have 'name' or 'player_name' key)
        league: League code
    
    Returns:
        Filtered list with only available players
    """
    injured = get_injured_players(league)
    
    available = []
    for player in players:
        name = player.get("name") or player.get("player_name", "")
        name_lower = name.lower()
        
        if name_lower in injured:
            if injured[name_lower]["is_out"]:
                logger.info(f"Filtering out {name} - {injured[name_lower]['status']}: {injured[name_lower]['injury_type']}")
                continue
        
        is_out = False
        for injured_name, info in injured.items():
            if name_lower in injured_name or injured_name in name_lower:
                if info["is_out"]:
                    logger.info(f"Filtering out {name} - {info['status']}: {info['injury_type']}")
                    is_out = True
                    break
        
        if not is_out:
            available.append(player)
    
    return available


def get_team_availability(team_abbrev: str, league: str) -> Dict[str, Any]:
    """
    Get full availability report for a team.
    
    Args:
        team_abbrev: Team abbreviation (e.g., 'LAL', 'BOS')
        league: League code
    
    Returns:
        Dictionary with team injury report
    """
    data = get_injuries(league, [team_abbrev])
    
    result = {
        "team": team_abbrev,
        "out": [],
        "questionable": [],
        "probable": [],
        "all_injuries": []
    }
    
    for team_data in data.get("teams", []):
        if team_data.get("team", {}).get("abbreviation", "").upper() == team_abbrev.upper():
            for injury in team_data.get("injuries", []):
                athlete = injury.get("athlete", {})
                status = injury.get("status", "").lower()
                
                injury_entry = {
                    "name": athlete.get("displayName", ""),
                    "position": athlete.get("position", {}).get("abbreviation", ""),
                    "status": status,
                    "injury": injury.get("type", {}).get("description", "")
                }
                
                result["all_injuries"].append(injury_entry)
                
                if status in DEFINITELY_OUT:
                    result["out"].append(injury_entry)
                elif status in {"questionable", "q", "doubtful", "d"}:
                    result["questionable"].append(injury_entry)
                elif status in {"probable", "p"}:
                    result["probable"].append(injury_entry)
    
    return result


def get_matchup_injuries(home_abbrev: str, away_abbrev: str, league: str) -> Dict[str, Any]:
    """
    Get injury report for both teams in a matchup.
    
    Args:
        home_abbrev: Home team abbreviation
        away_abbrev: Away team abbreviation
        league: League code
    
    Returns:
        Dictionary with both teams' injury reports
    """
    return {
        "home": get_team_availability(home_abbrev, league),
        "away": get_team_availability(away_abbrev, league),
        "fetched_at": datetime.now().isoformat()
    }


def clear_cache():
    """Clear the injury cache."""
    global _injury_cache, _cache_timestamp
    _injury_cache = {}
    _cache_timestamp = {}
    logger.info("Injury cache cleared")
