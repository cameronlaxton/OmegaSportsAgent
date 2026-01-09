"""
Player Game Log Module

Fetches real player game-by-game stats from ESPN API with fallbacks to
Basketball Reference and Perplexity API.
"""

import os
import json
import time
import logging
import re
from typing import Dict, List, Optional, Any
from urllib.parse import quote
from datetime import datetime

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

ESPN_API_BASE = "https://site.api.espn.com/apis/site/v2/sports"
ESPN_WEB_API_BASE = "https://site.web.api.espn.com/apis/common/v3/sports"
ESPN_SEARCH_URL = "https://site.api.espn.com/apis/common/v3/search"
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"

REQUEST_TIMEOUT = 15
RATE_LIMIT_DELAY = 0.5
_last_request_time = 0

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

LEAGUE_PATHS = {
    "NBA": "basketball/nba",
    "WNBA": "basketball/wnba",
    "NFL": "football/nfl",
    "MLB": "baseball/mlb",
    "NHL": "hockey/nhl",
    "NCAAB": "basketball/mens-college-basketball",
    "NCAAF": "football/college-football"
}


def _rate_limit():
    """Enforce rate limiting between requests."""
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < RATE_LIMIT_DELAY:
        time.sleep(RATE_LIMIT_DELAY - elapsed)
    _last_request_time = time.time()


def _make_request(url: str, params: Optional[Dict] = None, headers: Optional[Dict] = None) -> Optional[Dict]:
    """Make an HTTP request with rate limiting."""
    _rate_limit()
    try:
        resp = requests.get(url, params=params, headers=headers or HEADERS, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200:
            return resp.json()
        logger.warning(f"Request to {url} returned {resp.status_code}")
        return None
    except Exception as e:
        logger.error(f"Request failed: {e}")
        return None


def _parse_float(value: Any, default: float = 0.0) -> float:
    """Parse a value to float safely."""
    try:
        if value is None:
            return default
        cleaned = re.sub(r'[^\d.\-]', '', str(value))
        return float(cleaned) if cleaned else default
    except (ValueError, TypeError):
        return default


def _format_date(date_str: str) -> str:
    """Format date string to readable format."""
    try:
        if 'T' in date_str:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime("%b %d")
        return date_str
    except:
        return date_str


def get_espn_player_id(player_name: str, league: str = "NBA") -> Optional[str]:
    """Search for player ID on ESPN."""
    try:
        data = _make_request(
            ESPN_SEARCH_URL,
            params={"query": player_name, "limit": 5, "type": "player"}
        )
        
        if not data:
            return None
        
        items = data.get("items", [])
        league_lower = league.lower()
        
        for item in items:
            item_league = item.get("league", "").lower()
            if league_lower in item_league or item_league in league_lower:
                return item.get("id")
        
        if items:
            return items[0].get("id")
        
        return None
    except Exception as e:
        logger.error(f"Error searching for player {player_name}: {e}")
        return None


def get_player_game_log_espn(player_name: str, league: str = "NBA", n_games: int = 5) -> List[Dict[str, Any]]:
    """
    Fetch player game log from ESPN API.
    
    Args:
        player_name: Player's full name
        league: League code (NBA, NFL, etc.)
        n_games: Number of recent games to fetch
    
    Returns:
        List of game logs with detailed stats
    """
    league_path = LEAGUE_PATHS.get(league.upper())
    if not league_path:
        logger.warning(f"Unknown league: {league}")
        return []
    
    player_id = get_espn_player_id(player_name, league)
    if not player_id:
        logger.info(f"Could not find ESPN player ID for {player_name}")
        return []
    
    url = f"{ESPN_WEB_API_BASE}/{league_path}/athletes/{player_id}/gamelog"
    data = _make_request(url)
    
    if not data:
        url_fallback = f"{ESPN_API_BASE}/{league_path}/athletes/{player_id}/gamelog"
        data = _make_request(url_fallback)
        if not data:
            return []
    
    games = []
    labels = data.get("labels", [])
    
    season_types = data.get("seasonTypes", [])
    for season_type in season_types:
        categories = season_type.get("categories", [])
        for cat in categories:
            events = cat.get("events", [])
            for event in events:
                if len(games) >= n_games:
                    break
                game_data = _parse_espn_web_event(event, labels, league)
                if game_data:
                    games.append(game_data)
            if len(games) >= n_games:
                break
        if len(games) >= n_games:
            break
    
    if not games:
        events = data.get("events", [])
        for event in events[:n_games]:
            game_data = _parse_espn_event(event, labels, league)
            if game_data:
                games.append(game_data)
    
    return games[:n_games]


def _parse_espn_web_event(event: Dict, labels: List[str], league: str) -> Optional[Dict[str, Any]]:
    """Parse ESPN web API event from seasonTypes structure."""
    try:
        stats = event.get("stats", [])
        if not stats:
            return None
        
        stat_map = {}
        for i, label in enumerate(labels):
            if i < len(stats):
                stat_map[label.upper()] = stats[i]
        
        game = {
            "date": "",
            "opponent": "",
            "home_away": "",
            "result": ""
        }
        
        if league.upper() in ["NBA", "WNBA", "NCAAB"]:
            game.update({
                "min": stat_map.get("MIN", "-"),
                "pts": _parse_float(stat_map.get("PTS", 0)),
                "fg": stat_map.get("FG", "-"),
                "fg3": stat_map.get("3PT", "-"),
                "ft": stat_map.get("FT", "-"),
                "reb": _parse_float(stat_map.get("REB", 0)),
                "ast": _parse_float(stat_map.get("AST", 0)),
                "stl": _parse_float(stat_map.get("STL", 0)),
                "blk": _parse_float(stat_map.get("BLK", 0)),
                "to": _parse_float(stat_map.get("TO", 0)),
                "pf": _parse_float(stat_map.get("PF", 0)),
                "plus_minus": stat_map.get("+/-", "-")
            })
        
        return game
    except Exception as e:
        logger.debug(f"Error parsing ESPN web event: {e}")
        return None


def _parse_espn_event(event: Dict, stat_labels: List[str], league: str) -> Optional[Dict[str, Any]]:
    """Parse an ESPN event into a game log entry."""
    try:
        stats_list = event.get("stats", [])
        opponent = event.get("opponent", {})
        
        stat_values = {}
        for i, label in enumerate(stat_labels):
            if i < len(stats_list):
                stat_values[label.lower()] = stats_list[i]
        
        game = {
            "date": _format_date(event.get("eventDate", event.get("date", ""))),
            "opponent": opponent.get("abbreviation", opponent.get("displayName", ""))[:3] if opponent else "",
            "home_away": event.get("homeAway", ""),
            "result": event.get("gameResult", "")
        }
        
        if league.upper() in ["NBA", "WNBA", "NCAAB"]:
            game.update({
                "min": stat_values.get("min", stat_values.get("minutes", "-")),
                "pts": _parse_float(stat_values.get("pts", stat_values.get("points", 0))),
                "fg": stat_values.get("fg", f"{stat_values.get('fgm', 0)}-{stat_values.get('fga', 0)}"),
                "fg3": stat_values.get("3pt", stat_values.get("fg3", f"{stat_values.get('3pm', 0)}-{stat_values.get('3pa', 0)}")),
                "ft": stat_values.get("ft", f"{stat_values.get('ftm', 0)}-{stat_values.get('fta', 0)}"),
                "reb": _parse_float(stat_values.get("reb", stat_values.get("rebounds", 0))),
                "ast": _parse_float(stat_values.get("ast", stat_values.get("assists", 0))),
                "stl": _parse_float(stat_values.get("stl", stat_values.get("steals", 0))),
                "blk": _parse_float(stat_values.get("blk", stat_values.get("blocks", 0))),
                "to": _parse_float(stat_values.get("to", stat_values.get("turnovers", 0))),
                "pf": _parse_float(stat_values.get("pf", stat_values.get("fouls", 0))),
                "plus_minus": stat_values.get("+/-", stat_values.get("plusminus", "-"))
            })
        else:
            game.update({
                "pass_yds": _parse_float(stat_values.get("pass_yds", stat_values.get("passingyards", 0))),
                "pass_td": _parse_float(stat_values.get("pass_td", stat_values.get("passingtouchdowns", 0))),
                "rush_yds": _parse_float(stat_values.get("rush_yds", stat_values.get("rushingyards", 0))),
                "rush_td": _parse_float(stat_values.get("rush_td", stat_values.get("rushingtouchdowns", 0))),
                "rec_yds": _parse_float(stat_values.get("rec_yds", stat_values.get("receivingyards", 0))),
                "rec_td": _parse_float(stat_values.get("rec_td", stat_values.get("receivingtouchdowns", 0)))
            })
        
        return game
    except Exception as e:
        logger.debug(f"Error parsing ESPN event: {e}")
        return None


def _parse_espn_gamelog_event(event: Dict, league: str) -> Optional[Dict[str, Any]]:
    """Parse an ESPN gamelog event from seasonTypes structure."""
    try:
        stats = event.get("stats", {})
        opponent = event.get("opponent", {})
        
        game = {
            "date": _format_date(event.get("gameDate", event.get("eventDate", ""))),
            "opponent": opponent.get("abbreviation", opponent.get("displayName", ""))[:3] if isinstance(opponent, dict) else str(opponent)[:3],
            "home_away": event.get("atVs", event.get("homeAway", "")),
            "result": event.get("gameResult", "")
        }
        
        if league.upper() in ["NBA", "WNBA", "NCAAB"]:
            if isinstance(stats, list):
                game.update({
                    "min": stats[0] if len(stats) > 0 else "-",
                    "fg": stats[1] if len(stats) > 1 else "0-0",
                    "fg3": stats[4] if len(stats) > 4 else "0-0",
                    "ft": stats[7] if len(stats) > 7 else "0-0",
                    "reb": _parse_float(stats[10] if len(stats) > 10 else 0),
                    "ast": _parse_float(stats[11] if len(stats) > 11 else 0),
                    "stl": _parse_float(stats[12] if len(stats) > 12 else 0),
                    "blk": _parse_float(stats[13] if len(stats) > 13 else 0),
                    "to": _parse_float(stats[14] if len(stats) > 14 else 0),
                    "pf": _parse_float(stats[15] if len(stats) > 15 else 0),
                    "pts": _parse_float(stats[16] if len(stats) > 16 else 0),
                    "plus_minus": stats[17] if len(stats) > 17 else "-"
                })
            elif isinstance(stats, dict):
                game.update({
                    "min": stats.get("MIN", stats.get("minutes", "-")),
                    "pts": _parse_float(stats.get("PTS", stats.get("points", 0))),
                    "fg": f"{stats.get('FGM', 0)}-{stats.get('FGA', 0)}",
                    "fg3": f"{stats.get('3PM', stats.get('FG3M', 0))}-{stats.get('3PA', stats.get('FG3A', 0))}",
                    "ft": f"{stats.get('FTM', 0)}-{stats.get('FTA', 0)}",
                    "reb": _parse_float(stats.get("REB", stats.get("rebounds", 0))),
                    "ast": _parse_float(stats.get("AST", stats.get("assists", 0))),
                    "stl": _parse_float(stats.get("STL", stats.get("steals", 0))),
                    "blk": _parse_float(stats.get("BLK", stats.get("blocks", 0))),
                    "to": _parse_float(stats.get("TO", stats.get("turnovers", 0))),
                    "pf": _parse_float(stats.get("PF", stats.get("fouls", 0))),
                    "plus_minus": stats.get("+/-", stats.get("PLUSMINUS", "-"))
                })
        
        return game
    except Exception as e:
        logger.debug(f"Error parsing ESPN gamelog event: {e}")
        return None


def get_player_game_log_bref(player_name: str, n_games: int = 5) -> List[Dict[str, Any]]:
    """
    Fallback: Scrape player game log from Basketball Reference.
    
    Args:
        player_name: Player's full name (e.g., "LeBron James")
        n_games: Number of recent games to fetch
    
    Returns:
        List of game logs
    """
    _rate_limit()
    
    try:
        name_parts = player_name.lower().split()
        if len(name_parts) < 2:
            return []
        
        first_name = name_parts[0]
        last_name = name_parts[-1]
        first_letter = last_name[0]
        player_id = f"{last_name[:5]}{first_name[:2]}01"
        
        url = f"https://www.basketball-reference.com/players/{first_letter}/{player_id}/gamelog/2025"
        
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if response.status_code != 200:
            logger.info(f"Basketball Reference returned {response.status_code} for {player_name}")
            return []
        
        soup = BeautifulSoup(response.text, "lxml")
        
        table = soup.find("table", {"id": "pgl_basic"})
        if not table:
            return []
        
        games = []
        tbody = table.find("tbody")
        if not tbody:
            return []
        
        rows = tbody.find_all("tr")
        
        for row in reversed(rows):
            if row.get("class") and "thead" in row.get("class"):
                continue
            
            cells = row.find_all(["td", "th"])
            if len(cells) < 20:
                continue
            
            def get_stat(stat_name):
                cell = row.find("td", {"data-stat": stat_name})
                return cell.get_text().strip() if cell else ""
            
            game = {
                "date": _format_date(get_stat("date_game")),
                "opponent": get_stat("opp_id"),
                "home_away": "@" if get_stat("game_location") == "@" else "vs",
                "result": get_stat("game_result").split()[0] if get_stat("game_result") else "",
                "min": get_stat("mp"),
                "pts": _parse_float(get_stat("pts")),
                "fg": f"{get_stat('fg')}-{get_stat('fga')}",
                "fg3": f"{get_stat('fg3')}-{get_stat('fg3a')}",
                "ft": f"{get_stat('ft')}-{get_stat('fta')}",
                "reb": _parse_float(get_stat("trb")),
                "ast": _parse_float(get_stat("ast")),
                "stl": _parse_float(get_stat("stl")),
                "blk": _parse_float(get_stat("blk")),
                "to": _parse_float(get_stat("tov")),
                "pf": _parse_float(get_stat("pf")),
                "plus_minus": get_stat("plus_minus") or "-"
            }
            
            games.append(game)
            if len(games) >= n_games:
                break
        
        return games
    
    except Exception as e:
        logger.error(f"Error scraping Basketball Reference for {player_name}: {e}")
        return []


def get_player_game_log_perplexity(player_name: str, league: str = "NBA", n_games: int = 5) -> List[Dict[str, Any]]:
    """
    Fallback: Use Perplexity API to get player game log.
    
    Args:
        player_name: Player's full name
        league: League code
        n_games: Number of games to retrieve
    
    Returns:
        List of game logs (may be less detailed)
    """
    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if not api_key:
        logger.info("PERPLEXITY_API_KEY not configured")
        return []
    
    _rate_limit()
    
    prompt = f"""What were {player_name}'s stats in his last {n_games} {league} games?
    
For each game, provide:
- Date
- Opponent
- Minutes played
- Points
- Field goals (made-attempted)
- 3-pointers (made-attempted)
- Free throws (made-attempted)
- Rebounds
- Assists
- Steals
- Blocks
- Turnovers

Format as a structured list with each game on a new line."""

    try:
        response = requests.post(
            PERPLEXITY_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "sonar",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a sports statistics assistant. Provide accurate, recent player statistics."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 800,
                "temperature": 0.1
            },
            timeout=20
        )
        
        if response.status_code != 200:
            logger.warning(f"Perplexity API returned {response.status_code}")
            return []
        
        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        games = _parse_perplexity_response(content, n_games)
        return games
    
    except Exception as e:
        logger.error(f"Error calling Perplexity API for {player_name}: {e}")
        return []


def _parse_perplexity_response(content: str, n_games: int) -> List[Dict[str, Any]]:
    """Parse Perplexity API response into game log format."""
    games = []
    
    lines = content.split('\n')
    current_game = {}
    
    for line in lines:
        line = line.strip()
        if not line:
            if current_game:
                games.append(current_game)
                current_game = {}
            continue
        
        line_lower = line.lower()
        
        if 'vs' in line_lower or '@' in line_lower or 'against' in line_lower:
            if current_game:
                games.append(current_game)
            current_game = {"date": "", "opponent": ""}
            
            parts = line.split()
            for i, part in enumerate(parts):
                if part.lower() in ['vs', '@', 'against', 'vs.']:
                    if i + 1 < len(parts):
                        current_game["opponent"] = parts[i + 1][:3].upper()
                    break
        
        pts_match = re.search(r'(\d+)\s*(?:points|pts)', line_lower)
        if pts_match:
            current_game["pts"] = int(pts_match.group(1))
        
        reb_match = re.search(r'(\d+)\s*(?:rebounds|reb)', line_lower)
        if reb_match:
            current_game["reb"] = int(reb_match.group(1))
        
        ast_match = re.search(r'(\d+)\s*(?:assists|ast)', line_lower)
        if ast_match:
            current_game["ast"] = int(ast_match.group(1))
        
        fg_match = re.search(r'(\d+)[/-](\d+)\s*(?:fg|field)', line_lower)
        if fg_match:
            current_game["fg"] = f"{fg_match.group(1)}-{fg_match.group(2)}"
        
        fg3_match = re.search(r'(\d+)[/-](\d+)\s*(?:3pt|three|3-point)', line_lower)
        if fg3_match:
            current_game["fg3"] = f"{fg3_match.group(1)}-{fg3_match.group(2)}"
        
        if len(games) >= n_games:
            break
    
    if current_game:
        games.append(current_game)
    
    for game in games:
        game.setdefault("pts", 0)
        game.setdefault("reb", 0)
        game.setdefault("ast", 0)
        game.setdefault("fg", "-")
        game.setdefault("fg3", "-")
        game.setdefault("ft", "-")
        game.setdefault("stl", 0)
        game.setdefault("blk", 0)
        game.setdefault("to", 0)
        game.setdefault("pf", 0)
        game.setdefault("min", "-")
        game.setdefault("plus_minus", "-")
    
    return games[:n_games]


def get_player_game_log(player_name: str, league: str = "NBA", n_games: int = 5) -> List[Dict[str, Any]]:
    """
    Get player game log with fallback chain: ESPN -> Basketball Reference -> Perplexity.
    
    Args:
        player_name: Player's full name
        league: League code (NBA, NFL, etc.)
        n_games: Number of recent games to fetch (default: 5)
    
    Returns:
        List of dictionaries containing game-by-game stats:
        - date: Game date (formatted)
        - opponent: Opponent abbreviation
        - min: Minutes played
        - pts: Points scored
        - fg: Field goals (made-attempted)
        - fg3: 3-pointers (made-attempted)
        - ft: Free throws (made-attempted)
        - reb: Total rebounds
        - ast: Assists
        - stl: Steals
        - blk: Blocks
        - to: Turnovers
        - pf: Personal fouls
        - plus_minus: Plus/minus rating
    """
    games = get_player_game_log_espn(player_name, league, n_games)
    if games:
        logger.info(f"Got {len(games)} games for {player_name} from ESPN")
        return games
    
    if league.upper() == "NBA":
        games = get_player_game_log_bref(player_name, n_games)
        if games:
            logger.info(f"Got {len(games)} games for {player_name} from Basketball Reference")
            return games
    
    games = get_player_game_log_perplexity(player_name, league, n_games)
    if games:
        logger.info(f"Got {len(games)} games for {player_name} from Perplexity")
        return games
    
    logger.warning(f"Could not find game log for {player_name}")
    return []


def get_cached_player_game_log(player_name: str, league: str = "NBA", n_games: int = 5) -> List[Dict[str, Any]]:
    """
    Get player game log with file caching.
    
    Args:
        player_name: Player's full name
        league: League code
        n_games: Number of games
    
    Returns:
        List of game logs
    """
    import os
    
    cache_dir = "data/cache"
    os.makedirs(cache_dir, exist_ok=True)
    
    today = datetime.now().strftime("%Y-%m-%d")
    safe_name = re.sub(r'[^a-z0-9_]', '_', player_name.lower())
    cache_file = f"{cache_dir}/gamelog_{safe_name}_{league}_{today}.json"
    
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                cached = json.load(f)
                if cached:
                    return cached[:n_games]
        except:
            pass
    
    games = get_player_game_log(player_name, league, n_games)
    
    if games:
        try:
            with open(cache_file, 'w') as f:
                json.dump(games, f)
        except:
            pass
    
    return games
