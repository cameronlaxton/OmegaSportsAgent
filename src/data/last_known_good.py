"""
Last Known Good Data Storage

Persistence layer that stores successful data fetches and returns stale data
when all live sources fail. NEVER returns None - always prefers stale real
data over no data.
"""

from __future__ import annotations
import json
import logging
import os
from datetime import datetime
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

LKG_CACHE_DIR = "data/cache/last_known_good"
LKG_TEAMS_DIR = os.path.join(LKG_CACHE_DIR, "teams")
LKG_PLAYERS_DIR = os.path.join(LKG_CACHE_DIR, "players")


def _ensure_dirs() -> None:
    """Ensure Last Known Good cache directories exist."""
    os.makedirs(LKG_TEAMS_DIR, exist_ok=True)
    os.makedirs(LKG_PLAYERS_DIR, exist_ok=True)


def _get_safe_key(name: str, league: str = "") -> str:
    """Generate a safe filename key."""
    safe_name = name.lower().replace(" ", "_").replace("/", "_").replace("'", "")
    if league:
        return f"{safe_name}_{league.lower()}"
    return safe_name


def _get_team_path(team_name: str, league: str) -> str:
    """Get file path for team LKG data."""
    key = _get_safe_key(team_name, league)
    return os.path.join(LKG_TEAMS_DIR, f"{key}.json")


def _get_player_path(player_name: str, league: str) -> str:
    """Get file path for player LKG data."""
    key = _get_safe_key(player_name, league)
    return os.path.join(LKG_PLAYERS_DIR, f"{key}.json")


def save_team_data(
    team_name: str,
    league: str,
    data: Dict[str, Any],
    source: str
) -> None:
    """
    Save successful team data fetch to Last Known Good storage.
    
    Args:
        team_name: Team name
        league: League code
        data: Team data dictionary (must have off_rating, def_rating, pace)
        source: Data source identifier (espn, nba_stats, perplexity, etc.)
    """
    try:
        _ensure_dirs()
        
        lkg_data = {
            "team_name": team_name,
            "league": league.upper(),
            "off_rating": data.get("off_rating"),
            "def_rating": data.get("def_rating"),
            "pace": data.get("pace"),
            "pts_per_game": data.get("pts_per_game", 0.0),
            "fg_pct": data.get("fg_pct", 0.0),
            "three_pt_pct": data.get("three_pt_pct", 0.0),
            "source": source,
            "saved_at": datetime.now().isoformat(),
            "is_stale": False
        }
        
        path = _get_team_path(team_name, league)
        with open(path, "w") as f:
            json.dump(lkg_data, f, indent=2)
        
        logger.debug(f"Saved LKG team data for {team_name} from {source}")
        
    except Exception as e:
        logger.warning(f"Failed to save LKG team data for {team_name}: {e}")


def load_team_data(team_name: str, league: str) -> Optional[Dict[str, Any]]:
    """
    Load Last Known Good team data. Returns data marked as stale but NEVER None
    if data exists.
    
    Args:
        team_name: Team name
        league: League code
    
    Returns:
        Dict with team data (is_stale=True) or None if never seen
    """
    path = _get_team_path(team_name, league)
    
    try:
        if not os.path.exists(path):
            alt_names = _get_alternative_team_names(team_name)
            for alt_name in alt_names:
                alt_path = _get_team_path(alt_name, league)
                if os.path.exists(alt_path):
                    path = alt_path
                    break
            else:
                logger.debug(f"No LKG data found for team {team_name}")
                return None
        
        with open(path, "r") as f:
            data = json.load(f)
        
        data["is_stale"] = True
        
        saved_at = data.get("saved_at", "")
        if saved_at:
            try:
                saved_time = datetime.fromisoformat(saved_at)
                age_hours = (datetime.now() - saved_time).total_seconds() / 3600
                data["stale_hours"] = round(age_hours, 1)
            except:
                data["stale_hours"] = None
        
        logger.info(f"Loaded STALE LKG team data for {team_name} (from {data.get('source', 'unknown')})")
        return data
        
    except Exception as e:
        logger.warning(f"Failed to load LKG team data for {team_name}: {e}")
        return None


def save_player_data(
    player_name: str,
    league: str,
    data: Dict[str, Any],
    source: str
) -> None:
    """
    Save successful player data fetch to Last Known Good storage.
    
    Args:
        player_name: Player name
        league: League code
        data: Player data dictionary
        source: Data source identifier
    """
    try:
        _ensure_dirs()
        
        lkg_data = {
            "player_name": player_name,
            "league": league.upper(),
            "team": data.get("team", ""),
            "position": data.get("position", ""),
            "usage_rate": data.get("usage_rate", 0.15),
            "pts_mean": data.get("pts_mean"),
            "pts_std": data.get("pts_std", 0),
            "reb_mean": data.get("reb_mean", 0),
            "reb_std": data.get("reb_std", 0),
            "ast_mean": data.get("ast_mean", 0),
            "ast_std": data.get("ast_std", 0),
            "source": source,
            "saved_at": datetime.now().isoformat(),
            "is_stale": False
        }
        
        path = _get_player_path(player_name, league)
        with open(path, "w") as f:
            json.dump(lkg_data, f, indent=2)
        
        logger.debug(f"Saved LKG player data for {player_name} from {source}")
        
    except Exception as e:
        logger.warning(f"Failed to save LKG player data for {player_name}: {e}")


def load_player_data(player_name: str, league: str) -> Optional[Dict[str, Any]]:
    """
    Load Last Known Good player data. Returns data marked as stale but NEVER None
    if data exists.
    
    Args:
        player_name: Player name
        league: League code
    
    Returns:
        Dict with player data (is_stale=True) or None if never seen
    """
    path = _get_player_path(player_name, league)
    
    try:
        if not os.path.exists(path):
            alt_names = _get_alternative_player_names(player_name)
            for alt_name in alt_names:
                alt_path = _get_player_path(alt_name, league)
                if os.path.exists(alt_path):
                    path = alt_path
                    break
            else:
                logger.debug(f"No LKG data found for player {player_name}")
                return None
        
        with open(path, "r") as f:
            data = json.load(f)
        
        data["is_stale"] = True
        
        saved_at = data.get("saved_at", "")
        if saved_at:
            try:
                saved_time = datetime.fromisoformat(saved_at)
                age_hours = (datetime.now() - saved_time).total_seconds() / 3600
                data["stale_hours"] = round(age_hours, 1)
            except:
                data["stale_hours"] = None
        
        logger.info(f"Loaded STALE LKG player data for {player_name} (from {data.get('source', 'unknown')})")
        return data
        
    except Exception as e:
        logger.warning(f"Failed to load LKG player data for {player_name}: {e}")
        return None


def _get_alternative_team_names(team_name: str) -> list:
    """Get alternative team name variations to search."""
    name_lower = team_name.lower()
    alternatives = []
    
    team_aliases = {
        "lakers": ["los angeles lakers", "la lakers"],
        "los angeles lakers": ["lakers", "la lakers"],
        "clippers": ["los angeles clippers", "la clippers"],
        "los angeles clippers": ["clippers", "la clippers"],
        "warriors": ["golden state warriors", "golden state", "gsw"],
        "golden state warriors": ["warriors", "gsw"],
        "knicks": ["new york knicks", "ny knicks"],
        "new york knicks": ["knicks", "ny knicks"],
        "nets": ["brooklyn nets", "bkn"],
        "brooklyn nets": ["nets", "bkn"],
        "76ers": ["philadelphia 76ers", "sixers", "philly"],
        "philadelphia 76ers": ["76ers", "sixers"],
        "celtics": ["boston celtics", "bos"],
        "boston celtics": ["celtics", "bos"],
        "heat": ["miami heat", "mia"],
        "miami heat": ["heat", "mia"],
        "bulls": ["chicago bulls", "chi"],
        "chicago bulls": ["bulls", "chi"],
        "cavaliers": ["cleveland cavaliers", "cavs", "cle"],
        "cleveland cavaliers": ["cavaliers", "cavs", "cle"],
        "mavericks": ["dallas mavericks", "mavs", "dal"],
        "dallas mavericks": ["mavericks", "mavs", "dal"],
        "nuggets": ["denver nuggets", "den"],
        "denver nuggets": ["nuggets", "den"],
        "rockets": ["houston rockets", "hou"],
        "houston rockets": ["rockets", "hou"],
        "pacers": ["indiana pacers", "ind"],
        "indiana pacers": ["pacers", "ind"],
        "grizzlies": ["memphis grizzlies", "mem"],
        "memphis grizzlies": ["grizzlies", "mem"],
        "bucks": ["milwaukee bucks", "mil"],
        "milwaukee bucks": ["bucks", "mil"],
        "timberwolves": ["minnesota timberwolves", "wolves", "min"],
        "minnesota timberwolves": ["timberwolves", "wolves", "min"],
        "pelicans": ["new orleans pelicans", "nop"],
        "new orleans pelicans": ["pelicans", "nop"],
        "thunder": ["oklahoma city thunder", "okc"],
        "oklahoma city thunder": ["thunder", "okc"],
        "magic": ["orlando magic", "orl"],
        "orlando magic": ["magic", "orl"],
        "suns": ["phoenix suns", "phx"],
        "phoenix suns": ["suns", "phx"],
        "trail blazers": ["portland trail blazers", "blazers", "por"],
        "portland trail blazers": ["trail blazers", "blazers", "por"],
        "kings": ["sacramento kings", "sac"],
        "sacramento kings": ["kings", "sac"],
        "spurs": ["san antonio spurs", "sas"],
        "san antonio spurs": ["spurs", "sas"],
        "raptors": ["toronto raptors", "tor"],
        "toronto raptors": ["raptors", "tor"],
        "jazz": ["utah jazz", "uta"],
        "utah jazz": ["jazz", "uta"],
        "wizards": ["washington wizards", "was"],
        "washington wizards": ["wizards", "was"],
        "hawks": ["atlanta hawks", "atl"],
        "atlanta hawks": ["hawks", "atl"],
        "hornets": ["charlotte hornets", "cha"],
        "charlotte hornets": ["hornets", "cha"],
        "pistons": ["detroit pistons", "det"],
        "detroit pistons": ["pistons", "det"]
    }
    
    if name_lower in team_aliases:
        alternatives.extend(team_aliases[name_lower])
    
    return alternatives


def _get_alternative_player_names(player_name: str) -> list:
    """Get alternative player name variations to search."""
    alternatives = []
    
    parts = player_name.split()
    if len(parts) >= 2:
        alternatives.append(f"{parts[0][0]}. {parts[-1]}")
        alternatives.append(parts[-1])
    
    name_lower = player_name.lower()
    if "jr" in name_lower:
        alternatives.append(name_lower.replace(" jr", "").replace(" jr.", ""))
    if "iii" in name_lower:
        alternatives.append(name_lower.replace(" iii", ""))
    
    return alternatives


def get_all_known_teams(league: str = "NBA") -> list:
    """Get list of all teams with Last Known Good data."""
    _ensure_dirs()
    teams = []
    league_lower = league.lower()
    
    try:
        for filename in os.listdir(LKG_TEAMS_DIR):
            if filename.endswith(".json") and league_lower in filename:
                try:
                    with open(os.path.join(LKG_TEAMS_DIR, filename), "r") as f:
                        data = json.load(f)
                        teams.append(data.get("team_name", filename.replace(".json", "")))
                except:
                    pass
    except Exception as e:
        logger.warning(f"Error listing LKG teams: {e}")
    
    return teams


def get_all_known_players(league: str = "NBA") -> list:
    """Get list of all players with Last Known Good data."""
    _ensure_dirs()
    players = []
    league_lower = league.lower()
    
    try:
        for filename in os.listdir(LKG_PLAYERS_DIR):
            if filename.endswith(".json") and league_lower in filename:
                try:
                    with open(os.path.join(LKG_PLAYERS_DIR, filename), "r") as f:
                        data = json.load(f)
                        players.append(data.get("player_name", filename.replace(".json", "")))
                except:
                    pass
    except Exception as e:
        logger.warning(f"Error listing LKG players: {e}")
    
    return players


def clear_stale_lkg_data(older_than_days: int = 30) -> int:
    """
    Clear very old Last Known Good data.
    
    Args:
        older_than_days: Remove data older than this many days
    
    Returns:
        Number of files removed
    """
    removed = 0
    now = datetime.now()
    
    for directory in [LKG_TEAMS_DIR, LKG_PLAYERS_DIR]:
        if not os.path.exists(directory):
            continue
            
        try:
            for filename in os.listdir(directory):
                if not filename.endswith(".json"):
                    continue
                    
                filepath = os.path.join(directory, filename)
                try:
                    with open(filepath, "r") as f:
                        data = json.load(f)
                    
                    saved_at = data.get("saved_at")
                    if saved_at:
                        saved_time = datetime.fromisoformat(saved_at)
                        age_days = (now - saved_time).days
                        
                        if age_days >= older_than_days:
                            os.remove(filepath)
                            removed += 1
                            logger.debug(f"Removed old LKG file: {filename}")
                except Exception as e:
                    logger.warning(f"Error processing LKG file {filename}: {e}")
        except Exception as e:
            logger.warning(f"Error clearing LKG directory {directory}: {e}")
    
    return removed
