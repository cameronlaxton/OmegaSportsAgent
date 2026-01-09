"""
NBA.com Stats API Adapter

Fetches team statistics from NBA.com's public stats API as a fallback source.
Handles rate limiting, User-Agent spoofing, and response parsing.
"""

from __future__ import annotations
import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, Optional, Any

import requests

logger = logging.getLogger(__name__)

CACHE_DIR = "data/cache"
NBA_STATS_BASE_URL = "https://stats.nba.com/stats"
REQUEST_TIMEOUT = 3
RATE_LIMIT_DELAY = 0.5
_last_nba_stats_call: float = 0

NBA_STATS_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Host": "stats.nba.com",
    "Origin": "https://www.nba.com",
    "Referer": "https://www.nba.com/",
    "Connection": "keep-alive",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token": "true"
}

CURRENT_SEASON = "2024-25"

NBA_TEAM_IDS = {
    "hawks": 1610612737, "atlanta hawks": 1610612737, "atl": 1610612737,
    "celtics": 1610612738, "boston celtics": 1610612738, "bos": 1610612738,
    "nets": 1610612751, "brooklyn nets": 1610612751, "bkn": 1610612751,
    "hornets": 1610612766, "charlotte hornets": 1610612766, "cha": 1610612766,
    "bulls": 1610612741, "chicago bulls": 1610612741, "chi": 1610612741,
    "cavaliers": 1610612739, "cleveland cavaliers": 1610612739, "cle": 1610612739, "cavs": 1610612739,
    "mavericks": 1610612742, "dallas mavericks": 1610612742, "dal": 1610612742, "mavs": 1610612742,
    "nuggets": 1610612743, "denver nuggets": 1610612743, "den": 1610612743,
    "pistons": 1610612765, "detroit pistons": 1610612765, "det": 1610612765,
    "warriors": 1610612744, "golden state warriors": 1610612744, "gsw": 1610612744, "golden state": 1610612744,
    "rockets": 1610612745, "houston rockets": 1610612745, "hou": 1610612745,
    "pacers": 1610612754, "indiana pacers": 1610612754, "ind": 1610612754,
    "clippers": 1610612746, "los angeles clippers": 1610612746, "lac": 1610612746, "la clippers": 1610612746,
    "lakers": 1610612747, "los angeles lakers": 1610612747, "lal": 1610612747, "la lakers": 1610612747,
    "grizzlies": 1610612763, "memphis grizzlies": 1610612763, "mem": 1610612763,
    "heat": 1610612748, "miami heat": 1610612748, "mia": 1610612748,
    "bucks": 1610612749, "milwaukee bucks": 1610612749, "mil": 1610612749,
    "timberwolves": 1610612750, "minnesota timberwolves": 1610612750, "min": 1610612750, "wolves": 1610612750,
    "pelicans": 1610612740, "new orleans pelicans": 1610612740, "nop": 1610612740,
    "knicks": 1610612752, "new york knicks": 1610612752, "nyk": 1610612752,
    "thunder": 1610612760, "oklahoma city thunder": 1610612760, "okc": 1610612760,
    "magic": 1610612753, "orlando magic": 1610612753, "orl": 1610612753,
    "76ers": 1610612755, "philadelphia 76ers": 1610612755, "phi": 1610612755, "sixers": 1610612755,
    "suns": 1610612756, "phoenix suns": 1610612756, "phx": 1610612756,
    "trail blazers": 1610612757, "portland trail blazers": 1610612757, "por": 1610612757, "blazers": 1610612757,
    "kings": 1610612758, "sacramento kings": 1610612758, "sac": 1610612758,
    "spurs": 1610612759, "san antonio spurs": 1610612759, "sas": 1610612759,
    "raptors": 1610612761, "toronto raptors": 1610612761, "tor": 1610612761,
    "jazz": 1610612762, "utah jazz": 1610612762, "uta": 1610612762,
    "wizards": 1610612764, "washington wizards": 1610612764, "was": 1610612764
}


def _rate_limit_nba_stats() -> None:
    """Enforce rate limiting between NBA.com API calls."""
    global _last_nba_stats_call
    now = time.time()
    elapsed = now - _last_nba_stats_call
    if elapsed < RATE_LIMIT_DELAY:
        time.sleep(RATE_LIMIT_DELAY - elapsed)
    _last_nba_stats_call = time.time()


def _get_team_id(team_name: str) -> Optional[int]:
    """Get NBA.com team ID from team name."""
    team_lower = team_name.lower().strip()
    
    if team_lower in NBA_TEAM_IDS:
        return NBA_TEAM_IDS[team_lower]
    
    for key, team_id in NBA_TEAM_IDS.items():
        if key in team_lower or team_lower in key:
            return team_id
    
    return None


def _get_cache_path(team_name: str) -> str:
    """Get cache file path for NBA.com stats."""
    today = datetime.now().strftime("%Y-%m-%d")
    safe_key = team_name.lower().replace(" ", "_").replace("/", "_")
    return os.path.join(CACHE_DIR, f"nba_stats_{safe_key}_{today}.json")


def _load_cache(cache_path: str) -> Optional[Dict[str, Any]]:
    """Load data from cache if exists."""
    try:
        if os.path.exists(cache_path):
            with open(cache_path, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load NBA stats cache: {e}")
    return None


def _save_cache(cache_path: str, data: Dict[str, Any]) -> None:
    """Save data to cache."""
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(cache_path, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to save NBA stats cache: {e}")


def get_team_advanced_stats(team_name: str) -> Optional[Dict[str, Any]]:
    """
    Fetch team advanced stats from NBA.com Stats API.
    
    Args:
        team_name: Team name or abbreviation
    
    Returns:
        Dict with off_rating, def_rating, pace, source or None if failed
    """
    cache_path = _get_cache_path(team_name)
    cached = _load_cache(cache_path)
    if cached:
        logger.info(f"Loaded NBA.com stats from cache: {team_name}")
        return cached
    
    team_id = _get_team_id(team_name)
    if not team_id:
        logger.warning(f"Could not find NBA.com team ID for: {team_name}")
        return None
    
    _rate_limit_nba_stats()
    
    try:
        url = f"{NBA_STATS_BASE_URL}/teamdashboardbygeneralsplits"
        params = {
            "TeamID": team_id,
            "Season": CURRENT_SEASON,
            "SeasonType": "Regular Season",
            "MeasureType": "Advanced",
            "PerMode": "PerGame",
            "PlusMinus": "N",
            "PaceAdjust": "N",
            "Rank": "N",
            "LeagueID": "00",
            "DateFrom": "",
            "DateTo": "",
            "GameSegment": "",
            "LastNGames": 0,
            "Location": "",
            "Month": 0,
            "OpponentTeamID": 0,
            "Outcome": "",
            "Period": 0,
            "SeasonSegment": "",
            "VsConference": "",
            "VsDivision": ""
        }
        
        response = requests.get(
            url,
            headers=NBA_STATS_HEADERS,
            params=params,
            timeout=REQUEST_TIMEOUT
        )
        
        if response.status_code == 429:
            logger.warning(f"NBA.com rate limited for team {team_name}")
            return None
        
        if response.status_code != 200:
            logger.warning(f"NBA.com returned status {response.status_code} for team {team_name}")
            return None
        
        data = response.json()
        
        result_sets = data.get("resultSets", [])
        if not result_sets:
            logger.warning(f"No result sets in NBA.com response for {team_name}")
            return None
        
        overall_stats = None
        for result_set in result_sets:
            if result_set.get("name") == "OverallTeamDashboard":
                overall_stats = result_set
                break
        
        if not overall_stats:
            overall_stats = result_sets[0]
        
        headers = overall_stats.get("headers", [])
        row_sets = overall_stats.get("rowSet", [])
        
        if not row_sets:
            logger.warning(f"No row data in NBA.com response for {team_name}")
            return None
        
        row = row_sets[0]
        
        header_to_idx = {h: i for i, h in enumerate(headers)}
        
        off_rating = None
        def_rating = None
        pace = None
        
        off_rating_keys = ["OFF_RATING", "OFFENSIVE_RATING", "OFFRTG"]
        def_rating_keys = ["DEF_RATING", "DEFENSIVE_RATING", "DEFRTG"]
        pace_keys = ["PACE", "POSS"]
        
        for key in off_rating_keys:
            if key in header_to_idx:
                idx = header_to_idx[key]
                if idx < len(row) and row[idx] is not None:
                    off_rating = float(row[idx])
                    break
        
        for key in def_rating_keys:
            if key in header_to_idx:
                idx = header_to_idx[key]
                if idx < len(row) and row[idx] is not None:
                    def_rating = float(row[idx])
                    break
        
        for key in pace_keys:
            if key in header_to_idx:
                idx = header_to_idx[key]
                if idx < len(row) and row[idx] is not None:
                    pace = float(row[idx])
                    break
        
        if off_rating is None or def_rating is None or pace is None:
            logger.warning(f"Incomplete data from NBA.com for {team_name}: off={off_rating}, def={def_rating}, pace={pace}")
            return None
        
        result = {
            "team_name": team_name,
            "team_id": team_id,
            "off_rating": off_rating,
            "def_rating": def_rating,
            "pace": pace,
            "source": "nba_stats_api",
            "fetched_at": datetime.now().isoformat()
        }
        
        _save_cache(cache_path, result)
        logger.info(f"Fetched NBA.com stats for {team_name}: off={off_rating:.1f}, def={def_rating:.1f}, pace={pace:.1f}")
        
        return result
        
    except requests.exceptions.Timeout:
        logger.warning(f"NBA.com API timeout for team {team_name}")
        return None
    except requests.exceptions.RequestException as e:
        logger.warning(f"NBA.com API request error for {team_name}: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.warning(f"NBA.com API JSON decode error for {team_name}: {e}")
        return None
    except Exception as e:
        logger.error(f"NBA.com API unexpected error for {team_name}: {e}")
        return None


def get_team_basic_stats(team_name: str) -> Optional[Dict[str, Any]]:
    """
    Fetch basic team stats (points, FG%, 3P%) from NBA.com.
    
    Args:
        team_name: Team name or abbreviation
    
    Returns:
        Dict with basic stats or None if failed
    """
    team_id = _get_team_id(team_name)
    if not team_id:
        return None
    
    _rate_limit_nba_stats()
    
    try:
        url = f"{NBA_STATS_BASE_URL}/teamdashboardbygeneralsplits"
        params = {
            "TeamID": team_id,
            "Season": CURRENT_SEASON,
            "SeasonType": "Regular Season",
            "MeasureType": "Base",
            "PerMode": "PerGame",
            "LeagueID": "00"
        }
        
        response = requests.get(
            url,
            headers=NBA_STATS_HEADERS,
            params=params,
            timeout=REQUEST_TIMEOUT
        )
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        result_sets = data.get("resultSets", [])
        
        if not result_sets:
            return None
        
        overall_stats = result_sets[0]
        headers = overall_stats.get("headers", [])
        row_sets = overall_stats.get("rowSet", [])
        
        if not row_sets:
            return None
        
        row = row_sets[0]
        header_to_idx = {h: i for i, h in enumerate(headers)}
        
        pts = row[header_to_idx.get("PTS", -1)] if "PTS" in header_to_idx else None
        fg_pct = row[header_to_idx.get("FG_PCT", -1)] if "FG_PCT" in header_to_idx else None
        fg3_pct = row[header_to_idx.get("FG3_PCT", -1)] if "FG3_PCT" in header_to_idx else None
        
        return {
            "pts_per_game": float(pts) if pts else 0.0,
            "fg_pct": float(fg_pct) if fg_pct else 0.0,
            "three_pt_pct": float(fg3_pct) if fg3_pct else 0.0,
            "source": "nba_stats_api"
        }
        
    except Exception as e:
        logger.warning(f"Error fetching basic stats from NBA.com for {team_name}: {e}")
        return None
