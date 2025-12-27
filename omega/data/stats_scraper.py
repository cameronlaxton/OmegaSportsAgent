"""
Stats Scraper Module

Functions to scrape player and team stats from free sources.
Uses Basketball Reference, Pro Football Reference, and ESPN APIs.
"""

import time
import logging
import re
from typing import Dict, List, Optional, Any
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 15
RATE_LIMIT_DELAY = 3.0
_last_request_time = 0

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def _rate_limit():
    """Enforce rate limiting between requests."""
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < RATE_LIMIT_DELAY:
        time.sleep(RATE_LIMIT_DELAY - elapsed)
    _last_request_time = time.time()


def _clean_text(text: str) -> str:
    """Clean extracted text."""
    if text is None:
        return ""
    return re.sub(r'\s+', ' ', text.strip())


def _parse_float(value: str, default: float = 0.0) -> float:
    """Parse a string to float, handling errors."""
    try:
        cleaned = re.sub(r'[^\d.\-]', '', str(value))
        return float(cleaned) if cleaned else default
    except (ValueError, TypeError):
        return default


def get_player_stats(player_name: str, league: str) -> Optional[Dict[str, Any]]:
    """
    Get player stats for a given player and league.
    
    Args:
        player_name: Player's full name
        league: League code (NBA, NFL, MLB, NHL)
    
    Returns:
        Dictionary with player stats or None if not found
    """
    league = league.upper()
    
    if league == "NBA":
        return _get_nba_player_stats(player_name)
    elif league == "NFL":
        return _get_nfl_player_stats(player_name)
    elif league == "MLB":
        return _get_mlb_player_stats(player_name)
    elif league == "NHL":
        return _get_nhl_player_stats(player_name)
    else:
        return _get_espn_player_stats(player_name, league)


def get_team_stats(team: str, league: str) -> Optional[Dict[str, Any]]:
    """
    Get team stats for a given team and league.
    
    Args:
        team: Team name or abbreviation
        league: League code (NBA, NFL, MLB, NHL)
    
    Returns:
        Dictionary with team stats or None if not found
    """
    league = league.upper()
    
    if league == "NBA":
        return _get_nba_team_stats(team)
    elif league == "NFL":
        return _get_nfl_team_stats(team)
    elif league == "MLB":
        return _get_mlb_team_stats(team)
    elif league == "NHL":
        return _get_nhl_team_stats(team)
    else:
        return _get_espn_team_stats(team, league)


def get_season_averages(player_name: str, league: str) -> Optional[Dict[str, Any]]:
    """
    Get current season averages for a player.
    
    Args:
        player_name: Player's full name
        league: League code
    
    Returns:
        Dictionary with season averages or None
    """
    stats = get_player_stats(player_name, league)
    if stats:
        return stats.get("season_averages", stats)
    return None


def _get_nba_player_stats(player_name: str) -> Optional[Dict[str, Any]]:
    """Scrape NBA player stats from Basketball Reference."""
    _rate_limit()
    
    try:
        search_url = f"https://www.basketball-reference.com/search/search.fcgi?search={quote(player_name)}"
        response = requests.get(search_url, headers=HEADERS, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        
        if response.status_code != 200:
            logger.warning(f"Basketball Reference search failed: {response.status_code}")
            return _get_espn_player_stats(player_name, "NBA")
        
        soup = BeautifulSoup(response.text, "lxml")
        
        player_info_div = soup.find("div", {"id": "meta"})
        if not player_info_div:
            logger.info(f"Player {player_name} not found on Basketball Reference")
            return _get_espn_player_stats(player_name, "NBA")
        
        stats = {
            "name": player_name,
            "league": "NBA",
            "source": "basketball-reference",
            "season_averages": {}
        }
        
        info_items = player_info_div.find_all("p")
        for item in info_items:
            text = _clean_text(item.get_text())
            if "Position:" in text:
                stats["position"] = text.split("Position:")[-1].split("▪")[0].strip()
            if "Team:" in text:
                link = item.find("a")
                if link:
                    stats["team"] = _clean_text(link.get_text())
        
        per_game_table = soup.find("table", {"id": "per_game"})
        if per_game_table:
            rows = per_game_table.find("tbody").find_all("tr")
            if rows:
                last_row = None
                for row in reversed(rows):
                    if row.get("class") and "thead" in row.get("class"):
                        continue
                    last_row = row
                    break
                
                if last_row:
                    cells = last_row.find_all(["td", "th"])
                    stat_map = {}
                    headers = per_game_table.find("thead").find_all("th")
                    for idx, header in enumerate(headers):
                        stat_map[idx] = header.get("data-stat", "")
                    
                    for idx, cell in enumerate(cells):
                        stat_name = stat_map.get(idx, "")
                        if stat_name in ["pts_per_g", "ast_per_g", "trb_per_g", "stl_per_g", "blk_per_g", "fg_pct", "fg3_pct", "ft_pct", "mp_per_g"]:
                            stats["season_averages"][stat_name] = _parse_float(cell.get_text())
        
        return stats
    
    except Exception as e:
        logger.error(f"Error scraping Basketball Reference: {e}")
        return _get_espn_player_stats(player_name, "NBA")


def _get_nfl_player_stats(player_name: str) -> Optional[Dict[str, Any]]:
    """Scrape NFL player stats from Pro Football Reference."""
    _rate_limit()
    
    try:
        search_url = f"https://www.pro-football-reference.com/search/search.fcgi?search={quote(player_name)}"
        response = requests.get(search_url, headers=HEADERS, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        
        if response.status_code != 200:
            logger.warning(f"Pro Football Reference search failed: {response.status_code}")
            return _get_espn_player_stats(player_name, "NFL")
        
        soup = BeautifulSoup(response.text, "lxml")
        
        player_info_div = soup.find("div", {"id": "meta"})
        if not player_info_div:
            return _get_espn_player_stats(player_name, "NFL")
        
        stats = {
            "name": player_name,
            "league": "NFL",
            "source": "pro-football-reference",
            "season_averages": {}
        }
        
        info_items = player_info_div.find_all("p")
        for item in info_items:
            text = _clean_text(item.get_text())
            if "Position:" in text:
                stats["position"] = text.split("Position:")[-1].split(":")[0].strip()
        
        passing_table = soup.find("table", {"id": "passing"})
        if passing_table:
            rows = passing_table.find("tbody").find_all("tr")
            if rows:
                for row in reversed(rows):
                    if row.get("class") and "thead" in row.get("class"):
                        continue
                    cells = {td.get("data-stat"): _parse_float(td.get_text()) for td in row.find_all("td")}
                    stats["season_averages"].update({
                        "pass_yds": cells.get("pass_yds", 0),
                        "pass_td": cells.get("pass_td", 0),
                        "pass_int": cells.get("pass_int", 0),
                        "pass_rating": cells.get("pass_rating", 0)
                    })
                    break
        
        rushing_table = soup.find("table", {"id": "rushing_and_receiving"})
        if rushing_table:
            rows = rushing_table.find("tbody").find_all("tr")
            if rows:
                for row in reversed(rows):
                    if row.get("class") and "thead" in row.get("class"):
                        continue
                    cells = {td.get("data-stat"): _parse_float(td.get_text()) for td in row.find_all("td")}
                    stats["season_averages"].update({
                        "rush_yds": cells.get("rush_yds", 0),
                        "rush_td": cells.get("rush_td", 0),
                        "rec_yds": cells.get("rec_yds", 0),
                        "rec_td": cells.get("rec_td", 0)
                    })
                    break
        
        return stats
    
    except Exception as e:
        logger.error(f"Error scraping Pro Football Reference: {e}")
        return _get_espn_player_stats(player_name, "NFL")


def _get_mlb_player_stats(player_name: str) -> Optional[Dict[str, Any]]:
    """Get MLB player stats via ESPN API fallback."""
    return _get_espn_player_stats(player_name, "MLB")


def _get_nhl_player_stats(player_name: str) -> Optional[Dict[str, Any]]:
    """Get NHL player stats via ESPN API fallback."""
    return _get_espn_player_stats(player_name, "NHL")


def _get_espn_player_stats(player_name: str, league: str) -> Optional[Dict[str, Any]]:
    """Get player stats from ESPN API."""
    _rate_limit()
    
    league_map = {
        "NBA": "basketball/nba",
        "NFL": "football/nfl",
        "MLB": "baseball/mlb",
        "NHL": "hockey/nhl",
        "NCAAB": "basketball/mens-college-basketball",
        "NCAAF": "football/college-football"
    }
    
    sport_path = league_map.get(league.upper(), "basketball/nba")
    
    try:
        search_url = f"https://site.api.espn.com/apis/common/v3/search?query={quote(player_name)}&limit=5&type=player"
        response = requests.get(search_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        items = data.get("items", [])
        
        if not items:
            return None
        
        player_item = items[0]
        
        return {
            "name": player_item.get("displayName", player_name),
            "league": league.upper(),
            "source": "espn",
            "id": player_item.get("id"),
            "team": player_item.get("teamName"),
            "position": player_item.get("position"),
            "season_averages": {}
        }
    
    except Exception as e:
        logger.error(f"Error fetching ESPN player stats: {e}")
        return None


def _get_nba_team_stats(team: str) -> Optional[Dict[str, Any]]:
    """Scrape NBA team stats from Basketball Reference."""
    _rate_limit()
    
    try:
        url = "https://www.basketball-reference.com/leagues/NBA_2025.html"
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        
        if response.status_code != 200:
            return _get_espn_team_stats(team, "NBA")
        
        soup = BeautifulSoup(response.text, "lxml")
        
        team_stats_table = soup.find("table", {"id": "per_game-team"})
        opp_stats_table = soup.find("table", {"id": "per_game-opponent"})
        
        team_lower = team.lower()
        
        if team_stats_table:
            rows = team_stats_table.find("tbody").find_all("tr")
            for row in rows:
                team_cell = row.find("td", {"data-stat": "team"})
                if team_cell:
                    team_name = _clean_text(team_cell.get_text())
                    if team_lower in team_name.lower():
                        cells = {td.get("data-stat"): _parse_float(td.get_text()) for td in row.find_all("td")}
                        
                        return {
                            "name": team_name,
                            "league": "NBA",
                            "source": "basketball-reference",
                            "stats": {
                                "pts_per_game": cells.get("pts_per_g", 0),
                                "fg_pct": cells.get("fg_pct", 0),
                                "fg3_pct": cells.get("fg3_pct", 0),
                                "ft_pct": cells.get("ft_pct", 0),
                                "reb_per_game": cells.get("trb_per_g", 0),
                                "ast_per_game": cells.get("ast_per_g", 0)
                            }
                        }
        
        return _get_espn_team_stats(team, "NBA")
    
    except Exception as e:
        logger.error(f"Error scraping Basketball Reference team stats: {e}")
        return _get_espn_team_stats(team, "NBA")


def _get_nfl_team_stats(team: str) -> Optional[Dict[str, Any]]:
    """Scrape NFL team stats from Pro Football Reference."""
    _rate_limit()
    
    try:
        url = "https://www.pro-football-reference.com/years/2024/"
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        
        if response.status_code != 200:
            return _get_espn_team_stats(team, "NFL")
        
        soup = BeautifulSoup(response.text, "lxml")
        
        team_lower = team.lower()
        
        afc_table = soup.find("table", {"id": "AFC"})
        nfc_table = soup.find("table", {"id": "NFC"})
        
        for table in [afc_table, nfc_table]:
            if not table:
                continue
            rows = table.find("tbody").find_all("tr")
            for row in rows:
                team_cell = row.find("th", {"data-stat": "team"})
                if team_cell:
                    team_name = _clean_text(team_cell.get_text())
                    if team_lower in team_name.lower():
                        cells = {td.get("data-stat"): _parse_float(td.get_text()) for td in row.find_all("td")}
                        
                        return {
                            "name": team_name,
                            "league": "NFL",
                            "source": "pro-football-reference",
                            "stats": {
                                "wins": cells.get("wins", 0),
                                "losses": cells.get("losses", 0),
                                "points_for": cells.get("pts_off", 0),
                                "points_against": cells.get("pts_def", 0)
                            }
                        }
        
        return _get_espn_team_stats(team, "NFL")
    
    except Exception as e:
        logger.error(f"Error scraping Pro Football Reference team stats: {e}")
        return _get_espn_team_stats(team, "NFL")


def _get_mlb_team_stats(team: str) -> Optional[Dict[str, Any]]:
    """Get MLB team stats via ESPN API fallback."""
    return _get_espn_team_stats(team, "MLB")


def _get_nhl_team_stats(team: str) -> Optional[Dict[str, Any]]:
    """Get NHL team stats via ESPN API fallback."""
    return _get_espn_team_stats(team, "NHL")


def _get_espn_team_stats(team: str, league: str) -> Optional[Dict[str, Any]]:
    """Get team stats from ESPN API."""
    _rate_limit()
    
    league_map = {
        "NBA": "basketball/nba",
        "NFL": "football/nfl",
        "MLB": "baseball/mlb",
        "NHL": "hockey/nhl"
    }
    
    sport_path = league_map.get(league.upper(), "basketball/nba")
    
    try:
        url = f"https://site.api.espn.com/apis/site/v2/sports/{sport_path}/teams"
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        teams = data.get("sports", [{}])[0].get("leagues", [{}])[0].get("teams", [])
        
        team_lower = team.lower()
        
        for team_data in teams:
            team_info = team_data.get("team", {})
            team_name = team_info.get("displayName", "")
            team_abbr = team_info.get("abbreviation", "")
            
            if team_lower in team_name.lower() or team_lower == team_abbr.lower():
                return {
                    "name": team_name,
                    "abbreviation": team_abbr,
                    "league": league.upper(),
                    "source": "espn",
                    "id": team_info.get("id"),
                    "stats": {}
                }
        
        return None
    
    except Exception as e:
        logger.error(f"Error fetching ESPN team stats: {e}")
        return None


def search_players(query: str, league: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search for players by name.
    
    Args:
        query: Search query
        league: League code
        limit: Maximum results to return
    
    Returns:
        List of matching players
    """
    _rate_limit()
    
    try:
        url = f"https://site.api.espn.com/apis/common/v3/search?query={quote(query)}&limit={limit}&type=player"
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        
        if response.status_code != 200:
            return []
        
        data = response.json()
        return [
            {
                "name": item.get("displayName"),
                "id": item.get("id"),
                "team": item.get("teamName"),
                "position": item.get("position"),
                "league": item.get("league", {}).get("abbreviation", league)
            }
            for item in data.get("items", [])
        ]
    
    except Exception as e:
        logger.error(f"Error searching players: {e}")
        return []
