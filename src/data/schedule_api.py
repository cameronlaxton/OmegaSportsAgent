"""
Schedule API Module

Functions to get game schedules using ESPN API (free).
"""

import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

import requests

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 8
RATE_LIMIT_DELAY = 0.3
_last_request_time = 0

ESPN_API_BASE = "https://site.api.espn.com/apis/site/v2/sports"

LEAGUE_PATHS = {
    "NBA": "basketball/nba",
    "NFL": "football/nfl",
    "MLB": "baseball/mlb",
    "NHL": "hockey/nhl",
    "NCAAB": "basketball/mens-college-basketball",
    "NCAAF": "football/college-football",
    "WNBA": "basketball/wnba",
    "MLS": "soccer/usa.1"
}


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


def _make_espn_request(endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
    """Make a request to the ESPN API."""
    _rate_limit()
    
    url = f"{ESPN_API_BASE}/{endpoint}"
    
    try:
        response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        
        if response.status_code != 200:
            logger.warning(f"ESPN API returned {response.status_code}")
            return None
        
        return response.json()
    
    except requests.exceptions.Timeout:
        logger.error("ESPN API request timed out")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"ESPN API request failed: {e}")
        return None


def get_todays_games(league: str) -> List[Dict[str, Any]]:
    """
    Get today's games for a league.
    
    Args:
        league: League code (NBA, NFL, MLB, NHL, NCAAB, NCAAF)
    
    Returns:
        List of games scheduled for today
    """
    league_path = _get_league_path(league)
    today = datetime.now().strftime("%Y%m%d")
    
    data = _make_espn_request(f"{league_path}/scoreboard", params={"dates": today})
    
    if data is None:
        return []
    
    games = []
    events = data.get("events", [])
    
    for event in events:
        competition = event.get("competitions", [{}])[0]
        competitors = competition.get("competitors", [])
        
        home_team = None
        away_team = None
        
        for comp in competitors:
            team_info = {
                "id": comp.get("id"),
                "name": comp.get("team", {}).get("displayName", ""),
                "abbreviation": comp.get("team", {}).get("abbreviation", ""),
                "score": comp.get("score", "0"),
                "record": comp.get("records", [{}])[0].get("summary", "") if comp.get("records") else ""
            }
            
            if comp.get("homeAway") == "home":
                home_team = team_info
            else:
                away_team = team_info
        
        odds_data = {}
        odds = competition.get("odds", [])
        if odds:
            odds_item = odds[0]
            odds_data = {
                "spread": odds_item.get("details", ""),
                "over_under": odds_item.get("overUnder"),
                "spread_home": odds_item.get("spread"),
                "provider": odds_item.get("provider", {}).get("name", "")
            }
        
        game = {
            "game_id": event.get("id", ""),
            "league": league.upper(),
            "name": event.get("name", ""),
            "short_name": event.get("shortName", ""),
            "date": event.get("date", ""),
            "status": event.get("status", {}).get("type", {}).get("description", ""),
            "status_detail": event.get("status", {}).get("type", {}).get("detail", ""),
            "venue": competition.get("venue", {}).get("fullName", ""),
            "home_team": home_team,
            "away_team": away_team,
            "odds": odds_data,
            "broadcast": competition.get("broadcasts", [{}])[0].get("names", []) if competition.get("broadcasts") else []
        }
        
        games.append(game)
    
    return games


def get_game_details(game_id: str, league: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get detailed information for a specific game.
    
    Args:
        game_id: ESPN event ID
        league: Optional league code (helps narrow search)
    
    Returns:
        Detailed game information or None
    """
    leagues_to_check = [league.upper()] if league else list(LEAGUE_PATHS.keys())
    
    for check_league in leagues_to_check:
        league_path = _get_league_path(check_league)
        
        data = _make_espn_request(f"{league_path}/summary", params={"event": game_id})
        
        if data:
            return _parse_game_details(data, game_id, check_league)
    
    return None


def _parse_game_details(data: Dict, game_id: str, league: str) -> Dict[str, Any]:
    """Parse detailed game data from ESPN response."""
    
    game_info = data.get("gameInfo", {})
    boxscore = data.get("boxscore", {})
    leaders = data.get("leaders", [])
    predictor = data.get("predictor", {})
    
    details = {
        "game_id": game_id,
        "league": league,
        "venue": game_info.get("venue", {}).get("fullName", ""),
        "attendance": game_info.get("attendance"),
        "weather": game_info.get("weather", {}),
        "officials": [
            official.get("displayName", "")
            for official in game_info.get("officials", [])
        ],
        "teams": [],
        "leaders": [],
        "win_probability": {}
    }
    
    for team_data in boxscore.get("teams", []):
        team = team_data.get("team", {})
        details["teams"].append({
            "id": team.get("id"),
            "name": team.get("displayName", ""),
            "abbreviation": team.get("abbreviation", ""),
            "logo": team.get("logo", ""),
            "stats": [
                {
                    "name": stat.get("label", ""),
                    "value": stat.get("displayValue", "")
                }
                for stat in team_data.get("statistics", [])
            ]
        })
    
    for leader in leaders:
        details["leaders"].append({
            "team": leader.get("team", {}).get("displayName", ""),
            "categories": [
                {
                    "name": cat.get("displayName", ""),
                    "leaders": [
                        {
                            "name": l.get("athlete", {}).get("displayName", ""),
                            "value": l.get("displayValue", "")
                        }
                        for l in cat.get("leaders", [])
                    ]
                }
                for cat in leader.get("leaders", [])
            ]
        })
    
    if predictor:
        details["win_probability"] = {
            "home": predictor.get("homeTeam", {}).get("gameProjection"),
            "away": predictor.get("awayTeam", {}).get("gameProjection")
        }
    
    return details


def get_upcoming_games(league: str, days: int = 7) -> List[Dict[str, Any]]:
    """
    Get upcoming games for a league over the next N days.
    
    Args:
        league: League code
        days: Number of days to look ahead (default 7)
    
    Returns:
        List of upcoming games
    """
    league_path = _get_league_path(league)
    
    all_games = []
    current_date = datetime.now()
    
    for i in range(days):
        date = current_date + timedelta(days=i)
        date_str = date.strftime("%Y%m%d")
        
        data = _make_espn_request(f"{league_path}/scoreboard", params={"dates": date_str})
        
        if data:
            events = data.get("events", [])
            for event in events:
                competition = event.get("competitions", [{}])[0]
                competitors = competition.get("competitors", [])
                
                home_team = None
                away_team = None
                
                for comp in competitors:
                    team_info = {
                        "id": comp.get("id"),
                        "name": comp.get("team", {}).get("displayName", ""),
                        "abbreviation": comp.get("team", {}).get("abbreviation", "")
                    }
                    
                    if comp.get("homeAway") == "home":
                        home_team = team_info
                    else:
                        away_team = team_info
                
                all_games.append({
                    "game_id": event.get("id", ""),
                    "league": league.upper(),
                    "name": event.get("name", ""),
                    "date": event.get("date", ""),
                    "status": event.get("status", {}).get("type", {}).get("description", ""),
                    "home_team": home_team,
                    "away_team": away_team
                })
    
    return all_games


def get_standings(league: str) -> List[Dict[str, Any]]:
    """
    Get current standings for a league.
    
    Args:
        league: League code
    
    Returns:
        List of team standings
    """
    league_path = _get_league_path(league)
    
    data = _make_espn_request(f"{league_path}/standings")
    
    if data is None:
        return []
    
    standings = []
    
    for group in data.get("children", []):
        division_name = group.get("name", "")
        
        for entry in group.get("standings", {}).get("entries", []):
            team = entry.get("team", {})
            stats = {
                stat.get("name"): stat.get("displayValue", "")
                for stat in entry.get("stats", [])
            }
            
            standings.append({
                "team_id": team.get("id"),
                "team_name": team.get("displayName", ""),
                "abbreviation": team.get("abbreviation", ""),
                "division": division_name,
                "stats": stats
            })
    
    return standings


def get_team_schedule(team_id: str, league: str) -> List[Dict[str, Any]]:
    """
    Get schedule for a specific team.
    
    Args:
        team_id: ESPN team ID
        league: League code
    
    Returns:
        List of scheduled games
    """
    league_path = _get_league_path(league)
    
    data = _make_espn_request(f"{league_path}/teams/{team_id}/schedule")
    
    if data is None:
        return []
    
    schedule = []
    
    for event in data.get("events", []):
        competition = event.get("competitions", [{}])[0]
        competitors = competition.get("competitors", [])
        
        opponent = None
        is_home = False
        
        for comp in competitors:
            if comp.get("id") == team_id:
                is_home = comp.get("homeAway") == "home"
            else:
                opponent = {
                    "id": comp.get("id"),
                    "name": comp.get("team", {}).get("displayName", ""),
                    "abbreviation": comp.get("team", {}).get("abbreviation", "")
                }
        
        schedule.append({
            "game_id": event.get("id", ""),
            "date": event.get("date", ""),
            "opponent": opponent,
            "is_home": is_home,
            "status": event.get("status", {}).get("type", {}).get("description", "")
        })
    
    return schedule


def check_api_status() -> Dict[str, Any]:
    """
    Check ESPN API availability.
    
    Returns:
        Dictionary with API status info
    """
    try:
        response = requests.get(
            f"{ESPN_API_BASE}/basketball/nba/scoreboard",
            timeout=REQUEST_TIMEOUT
        )
        
        return {
            "status": "ok" if response.status_code == 200 else "error",
            "status_code": response.status_code,
            "available_leagues": list(LEAGUE_PATHS.keys())
        }
    
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


def get_scoreboard(league: str, date: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get scoreboard with scores for a league on a specific date.
    
    Args:
        league: League code (NBA, NFL, etc.)
        date: Date in YYYYMMDD format (default: today)
    
    Returns:
        List of games with scores and status
    """
    league_path = _get_league_path(league)
    
    if date is None:
        date = datetime.now().strftime("%Y%m%d")
    
    data = _make_espn_request(f"{league_path}/scoreboard", params={"dates": date})
    
    if data is None:
        return []
    
    games = []
    
    for event in data.get("events", []):
        competition = event.get("competitions", [{}])[0]
        competitors = competition.get("competitors", [])
        status_obj = event.get("status", {})
        
        home_team = ""
        away_team = ""
        home_score = 0
        away_score = 0
        
        for comp in competitors:
            team_name = comp.get("team", {}).get("displayName", "")
            score_str = comp.get("score", "0")
            try:
                score = int(score_str) if score_str else 0
            except ValueError:
                score = 0
            
            if comp.get("homeAway") == "home":
                home_team = team_name
                home_score = score
            else:
                away_team = team_name
                away_score = score
        
        status_type = status_obj.get("type", {})
        is_final = status_type.get("completed", False) or status_type.get("name") == "STATUS_FINAL"
        
        games.append({
            "game_id": event.get("id", ""),
            "league": league.upper(),
            "home_team": home_team,
            "away_team": away_team,
            "home_score": home_score,
            "away_score": away_score,
            "status": "Final" if is_final else status_type.get("description", "Scheduled"),
            "date": event.get("date", "")
        })
    
    return games
