"""
Stats Ingestion Service

Provides structured context dataclasses and functions for ingesting
player and team statistics for use in projections and simulations.
"""

from __future__ import annotations
import json
import logging
import os
import re
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib.parse import quote

import requests

from omega.data import stats_scraper
from omega.data import nba_stats_api
from omega.data import last_known_good

logger = logging.getLogger(__name__)

CACHE_DIR = "data/cache"
REQUEST_TIMEOUT = 15
ESPN_API_BASE = "https://site.api.espn.com/apis/site/v2/sports"

PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY")
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
PERPLEXITY_CACHE_HOURS = 24
PERPLEXITY_RATE_LIMIT_DELAY = 2.0
_last_perplexity_call: float = 0

BALLDONTLIE_API_KEY = os.environ.get("BALLDONTLIE_API_KEY")
BALLDONTLIE_API_URL = "https://api.balldontlie.io/v1"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

LEAGUE_PATHS = {
    "NBA": "basketball/nba",
    "NFL": "football/nfl",
    "MLB": "baseball/mlb",
    "NHL": "hockey/nhl",
    "NCAAB": "basketball/mens-college-basketball",
    "NCAAF": "football/college-football"
}

NBA_DEFAULT_PACE = 100.0
NFL_POSSESSIONS_PER_GAME = 12.0


@dataclass
class TeamContext:
    """Team statistical context for projections."""
    name: str
    league: str
    off_rating: float
    def_rating: float
    pace: float
    pts_per_game: float
    fg_pct: float
    three_pt_pct: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TeamContext:
        """Create from dictionary."""
        return cls(
            name=data.get("name", "Unknown"),
            league=data.get("league", "NBA"),
            off_rating=data.get("off_rating", 100.0),
            def_rating=data.get("def_rating", 100.0),
            pace=data.get("pace", NBA_DEFAULT_PACE),
            pts_per_game=data.get("pts_per_game", 110.0),
            fg_pct=data.get("fg_pct", 0.45),
            three_pt_pct=data.get("three_pt_pct", 0.35)
        )


@dataclass
class PlayerContext:
    """Player statistical context for projections."""
    name: str
    team: str
    position: str
    usage_rate: float
    pts_mean: float
    pts_std: float
    reb_mean: float
    reb_std: float
    ast_mean: float
    ast_std: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PlayerContext:
        """Create from dictionary."""
        pts_mean = data.get("pts_mean", 10.0)
        reb_mean = data.get("reb_mean", 4.0)
        ast_mean = data.get("ast_mean", 3.0)
        return cls(
            name=data.get("name", "Unknown"),
            team=data.get("team", "Unknown"),
            position=data.get("position", "G"),
            usage_rate=data.get("usage_rate", 0.15),
            pts_mean=pts_mean,
            pts_std=data.get("pts_std", pts_mean * 0.25),
            reb_mean=reb_mean,
            reb_std=data.get("reb_std", reb_mean * 0.25),
            ast_mean=ast_mean,
            ast_std=data.get("ast_std", ast_mean * 0.25)
        )


def _ensure_cache_dir() -> None:
    """Ensure cache directory exists."""
    os.makedirs(CACHE_DIR, exist_ok=True)


def _get_cache_path(prefix: str, key: str) -> str:
    """Get cache file path for today."""
    today = datetime.now().strftime("%Y-%m-%d")
    safe_key = key.lower().replace(" ", "_").replace("/", "_")
    return os.path.join(CACHE_DIR, f"{prefix}_{safe_key}_{today}.json")


def _load_cache(cache_path: str) -> Optional[Dict[str, Any]]:
    """Load data from cache if it exists."""
    try:
        if os.path.exists(cache_path):
            with open(cache_path, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load cache from {cache_path}: {e}")
    return None


def _save_cache(cache_path: str, data: Dict[str, Any]) -> None:
    """Save data to cache."""
    try:
        _ensure_cache_dir()
        with open(cache_path, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to save cache to {cache_path}: {e}")


def _get_perplexity_cache_path(prefix: str, key: str) -> str:
    """Get cache file path for Perplexity results (24-hour cache)."""
    safe_key = key.lower().replace(" ", "_").replace("/", "_")
    return os.path.join(CACHE_DIR, f"perplexity_{prefix}_{safe_key}.json")


def _load_perplexity_cache(cache_path: str) -> Optional[Dict[str, Any]]:
    """Load Perplexity data from cache if it exists and is not stale (24 hours)."""
    try:
        if os.path.exists(cache_path):
            file_stat = os.stat(cache_path)
            file_time = datetime.fromtimestamp(file_stat.st_mtime)
            age_hours = (datetime.now() - file_time).total_seconds() / 3600
            
            if age_hours < PERPLEXITY_CACHE_HOURS:
                with open(cache_path, "r") as f:
                    return json.load(f)
            else:
                logger.debug(f"Perplexity cache expired: {cache_path}")
    except Exception as e:
        logger.warning(f"Failed to load Perplexity cache from {cache_path}: {e}")
    return None


def _rate_limit_perplexity() -> None:
    """Enforce 2-second delay between Perplexity API calls."""
    global _last_perplexity_call
    now = time.time()
    elapsed = now - _last_perplexity_call
    if elapsed < PERPLEXITY_RATE_LIMIT_DELAY:
        time.sleep(PERPLEXITY_RATE_LIMIT_DELAY - elapsed)
    _last_perplexity_call = time.time()


def _extract_number(text: str, pattern: str) -> Optional[float]:
    """Extract a numeric value from text using a regex pattern."""
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        try:
            return float(match.group(1))
        except (ValueError, IndexError):
            pass
    return None


LEAGUE_BASELINES = {
    "NBA": {
        "off_rating": 112.0,
        "def_rating": 112.0,
        "pace": 100.0
    },
    "NFL": {
        "off_rating": 100.0,
        "def_rating": 100.0,
        "pace": 12.0
    },
    "MLB": {
        "off_rating": 100.0,
        "def_rating": 100.0,
        "pace": 9.0
    },
    "NHL": {
        "off_rating": 100.0,
        "def_rating": 100.0,
        "pace": 60.0
    }
}

TEAM_RATING_RANGES = {
    "NBA": {
        "off_rating": (95.0, 130.0),
        "def_rating": (95.0, 120.0),
        "pace": (90.0, 110.0)
    },
    "NFL": {
        "off_rating": (60.0, 140.0),
        "def_rating": (60.0, 140.0),
        "pace": (8.0, 16.0)
    }
}


def _validate_team_rating(value: Optional[float], stat: str, league: str) -> Optional[float]:
    """Validate a team rating is within reasonable ranges."""
    if value is None:
        return None
    
    ranges = TEAM_RATING_RANGES.get(league.upper(), TEAM_RATING_RANGES.get("NBA"))
    stat_range = ranges.get(stat)
    
    if stat_range:
        min_val, max_val = stat_range
        if value < min_val or value > max_val:
            logger.warning(f"Team {stat} value {value} out of range [{min_val}, {max_val}], rejecting")
            return None
    
    return value


def _get_league_baseline(league: str) -> Dict[str, float]:
    """Get league baseline defaults for fallback."""
    return LEAGUE_BASELINES.get(league.upper(), LEAGUE_BASELINES["NBA"])


def _parse_json_from_response(content: str) -> Optional[Dict[str, Any]]:
    """Try to extract JSON from Perplexity response."""
    try:
        json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except json.JSONDecodeError:
        pass
    return None


def get_team_ratings_from_perplexity(team_name: str, league: str, attempt: int = 1) -> Optional[Dict[str, Any]]:
    """
    Query Perplexity API for team ratings when standard sources fail.
    Uses aggressive, multi-attempt prompts for maximum data extraction.
    
    Args:
        team_name: Team name
        league: League code (NBA, NFL, etc.)
        attempt: Attempt number (1-3) for query variation
    
    Returns:
        Dict with {off_rating, def_rating, pace, source} or None if failed
    """
    if not PERPLEXITY_API_KEY:
        logger.warning("PERPLEXITY_API_KEY not configured for team ratings fallback")
        return None
    
    cache_path = _get_perplexity_cache_path("team", f"{team_name}_{league}")
    cached = _load_perplexity_cache(cache_path)
    if cached:
        logger.info(f"Loaded team ratings from Perplexity cache: {team_name}")
        return cached
    
    _rate_limit_perplexity()
    
    prompts = [
        f"""CRITICAL: Find the EXACT offensive rating, defensive rating, and pace for the {team_name} in the {league} 2024-25 season.

Search ESPN, NBA.com, Basketball Reference, and sports databases for these EXACT statistics.

Respond with ONLY a JSON object:
{{"off_rating": <number>, "def_rating": <number>, "pace": <number>}}

For NBA teams: offensive rating 100-125, defensive rating 100-120, pace 95-105.
CITE YOUR SOURCE. Do NOT estimate - find real data.""",
        
        f"""What are the exact offensive rating (ORtg), defensive rating (DRtg), and pace statistics for the {team_name} NBA team in the 2024-25 season?

Look up on Basketball Reference or NBA.com stats. These are advanced team statistics.
- Offensive Rating = points scored per 100 possessions
- Defensive Rating = points allowed per 100 possessions  
- Pace = possessions per 48 minutes

Return ONLY JSON: {{"off_rating": X, "def_rating": Y, "pace": Z}}""",
        
        f"""Search for {team_name} team statistics 2024-25 NBA season.
Find: offensive efficiency rating, defensive efficiency rating, game pace.
Sources: nba.com/stats, basketball-reference.com, espn.com

JSON response only: {{"off_rating": <value>, "def_rating": <value>, "pace": <value>}}"""
    ]
    
    prompt = prompts[min(attempt - 1, len(prompts) - 1)]
    
    try:
        response = requests.post(
            PERPLEXITY_API_URL,
            headers={
                "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "sonar",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a sports statistics expert. Always respond with valid JSON objects only, no additional text or explanation."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 200,
                "temperature": 0.1
            },
            timeout=15
        )
        
        if response.status_code != 200:
            logger.error(f"Perplexity API returned {response.status_code} for team {team_name}")
            return None
        
        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        parsed_json = _parse_json_from_response(content)
        
        off_rating = None
        def_rating = None
        pace = None
        
        if parsed_json:
            off_rating = _validate_team_rating(
                parsed_json.get("off_rating") or parsed_json.get("offensive_rating"),
                "off_rating", league
            )
            def_rating = _validate_team_rating(
                parsed_json.get("def_rating") or parsed_json.get("defensive_rating"),
                "def_rating", league
            )
            pace = _validate_team_rating(
                parsed_json.get("pace"),
                "pace", league
            )
        
        if off_rating is None:
            off_rating = _validate_team_rating(
                _extract_number(content, r"offensive\s*rating[:\s]*(\d+\.?\d*)"),
                "off_rating", league
            )
            if off_rating is None:
                off_rating = _validate_team_rating(
                    _extract_number(content, r"off(?:ensive)?\s*(?:rating|rtg)[:\s]*(\d+\.?\d*)"),
                    "off_rating", league
                )
        
        if def_rating is None:
            def_rating = _validate_team_rating(
                _extract_number(content, r"defensive\s*rating[:\s]*(\d+\.?\d*)"),
                "def_rating", league
            )
            if def_rating is None:
                def_rating = _validate_team_rating(
                    _extract_number(content, r"def(?:ensive)?\s*(?:rating|rtg)[:\s]*(\d+\.?\d*)"),
                    "def_rating", league
                )
        
        if pace is None:
            pace = _validate_team_rating(
                _extract_number(content, r"pace[:\s]*(\d+\.?\d*)"),
                "pace", league
            )
        
        if off_rating is None and def_rating is None and pace is None:
            if attempt < 3:
                logger.info(f"Perplexity attempt {attempt} failed for {team_name}, trying variation {attempt + 1}")
                return get_team_ratings_from_perplexity(team_name, league, attempt + 1)
            logger.warning(f"Could not parse any team ratings from Perplexity response for {team_name} after {attempt} attempts")
            return None
        
        if off_rating is None or def_rating is None or pace is None:
            if attempt < 3:
                logger.info(f"Incomplete Perplexity data for {team_name}, trying variation {attempt + 1}")
                return get_team_ratings_from_perplexity(team_name, league, attempt + 1)
            logger.warning(f"Incomplete team ratings from Perplexity for {team_name}: off={off_rating}, def={def_rating}, pace={pace}")
            return None
        
        result = {
            "off_rating": off_rating,
            "def_rating": def_rating,
            "pace": pace,
            "source": "perplexity",
            "raw_response": content[:500],
            "fetched_at": datetime.now().isoformat()
        }
        
        _save_cache(cache_path, result)
        logger.info(f"Fetched team ratings from Perplexity for {team_name}: off={result['off_rating']}, def={result['def_rating']}, pace={result['pace']}")
        return result
    
    except requests.exceptions.Timeout:
        logger.error(f"Perplexity API timeout for team {team_name}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error for team {team_name}: {e}")
        return None
    except Exception as e:
        logger.error(f"Perplexity API error for team {team_name}: {e}")
        return None


PLAYER_STAT_RANGES = {
    "NBA": {
        "pts_mean": (0.0, 50.0),
        "reb_mean": (0.0, 20.0),
        "ast_mean": (0.0, 15.0)
    },
    "NFL": {
        "pts_mean": (0.0, 100.0),
        "reb_mean": (0.0, 20.0),
        "ast_mean": (0.0, 15.0)
    }
}

PLAYER_BASELINE_STATS = {
    "pts_mean": 10.0,
    "reb_mean": 4.0,
    "ast_mean": 3.0
}


def _validate_player_stat(value: Optional[float], stat: str, league: str) -> Optional[float]:
    """Validate a player stat is within reasonable ranges."""
    if value is None:
        return None
    
    ranges = PLAYER_STAT_RANGES.get(league.upper(), PLAYER_STAT_RANGES.get("NBA"))
    stat_range = ranges.get(stat)
    
    if stat_range:
        min_val, max_val = stat_range
        if value < min_val or value > max_val:
            logger.warning(f"Player {stat} value {value} out of range [{min_val}, {max_val}], rejecting")
            return None
    
    return value


def get_player_stats_from_balldontlie(player_name: str) -> Optional[Dict[str, Any]]:
    """
    Fetch NBA player stats from Ball Don't Lie API.
    
    Free API for NBA player statistics - added to fallback chain before Perplexity
    to save Perplexity credits.
    
    Args:
        player_name: Player's full name
    
    Returns:
        Dict with {pts_mean, reb_mean, ast_mean, source} or None if failed
    """
    if not BALLDONTLIE_API_KEY:
        logger.debug("BALLDONTLIE_API_KEY not configured")
        return None
    
    try:
        headers = {
            "Authorization": f"Bearer {BALLDONTLIE_API_KEY}"
        }
        
        search_url = f"{BALLDONTLIE_API_URL}/players"
        params = {"search": player_name}
        
        response = requests.get(
            search_url, 
            headers=headers, 
            params=params, 
            timeout=REQUEST_TIMEOUT
        )
        
        if response.status_code != 200:
            logger.warning(f"Ball Don't Lie API returned {response.status_code}")
            return None
        
        data = response.json()
        players = data.get("data", [])
        
        if not players:
            logger.debug(f"No player found on Ball Don't Lie for: {player_name}")
            return None
        
        player = players[0]
        player_id = player.get("id")
        
        if not player_id:
            return None
        
        stats_url = f"{BALLDONTLIE_API_URL}/season_averages"
        stats_params = {"season": 2024, "player_ids[]": player_id}
        
        stats_response = requests.get(
            stats_url, 
            headers=headers, 
            params=stats_params, 
            timeout=REQUEST_TIMEOUT
        )
        
        if stats_response.status_code != 200:
            logger.warning(f"Ball Don't Lie stats API returned {stats_response.status_code}")
            return None
        
        stats_data = stats_response.json()
        averages = stats_data.get("data", [])
        
        if not averages:
            logger.debug(f"No season averages found on Ball Don't Lie for: {player_name}")
            return None
        
        season_avg = averages[0]
        
        pts_mean = season_avg.get("pts", 0.0)
        reb_mean = season_avg.get("reb", 0.0)
        ast_mean = season_avg.get("ast", 0.0)
        
        if pts_mean <= 0:
            logger.debug(f"Invalid stats from Ball Don't Lie for: {player_name}")
            return None
        
        logger.info(f"Got player stats from Ball Don't Lie for {player_name}: {pts_mean} PPG, {reb_mean} RPG, {ast_mean} APG")
        
        return {
            "pts_mean": float(pts_mean),
            "reb_mean": float(reb_mean),
            "ast_mean": float(ast_mean),
            "team": player.get("team", {}).get("full_name", ""),
            "position": player.get("position", ""),
            "source": "balldontlie"
        }
        
    except requests.exceptions.Timeout:
        logger.warning(f"Ball Don't Lie API timeout for {player_name}")
        return None
    except Exception as e:
        logger.error(f"Ball Don't Lie API error for {player_name}: {e}")
        return None


def get_player_stats_from_perplexity(player_name: str, league: str, attempt: int = 1) -> Optional[Dict[str, Any]]:
    """
    Query Perplexity API for player stats when standard sources fail.
    Uses aggressive, multi-attempt prompts for maximum data extraction.
    
    Args:
        player_name: Player's full name
        league: League code (NBA, NFL, etc.)
        attempt: Attempt number (1-3) for query variation
    
    Returns:
        Dict with {pts_mean, reb_mean, ast_mean, source} or None if failed
    """
    if not PERPLEXITY_API_KEY:
        logger.warning("PERPLEXITY_API_KEY not configured for player stats fallback")
        return None
    
    cache_path = _get_perplexity_cache_path("player", f"{player_name}_{league}")
    cached = _load_perplexity_cache(cache_path)
    if cached:
        logger.info(f"Loaded player stats from Perplexity cache: {player_name}")
        return cached
    
    _rate_limit_perplexity()
    
    prompts = [
        f"""CRITICAL: Find the EXACT 2024-25 {league} season statistics for {player_name}.

Search ESPN, NBA.com, Basketball Reference for this player's current season averages.

I need: points per game (PPG), rebounds per game (RPG), assists per game (APG).

Respond with ONLY a JSON object:
{{"pts": <number>, "reb": <number>, "ast": <number>}}

CITE YOUR SOURCE. Return real data only.""",
        
        f"""What are {player_name}'s current 2024-25 NBA season averages?
Look up on basketball-reference.com or espn.com/nba/player.

Stats needed:
- Points per game (PPG)
- Rebounds per game (RPG)  
- Assists per game (APG)

Return ONLY JSON: {{"pts": X, "reb": Y, "ast": Z}}
If player has no stats this season, respond: {{"unknown": true}}""",
        
        f"""Search for {player_name} NBA player statistics 2024-25 season.
Find PPG, RPG, APG from ESPN, NBA.com, or Basketball Reference.

JSON response only: {{"pts": <value>, "reb": <value>, "ast": <value>}}"""
    ]
    
    prompt = prompts[min(attempt - 1, len(prompts) - 1)]
    
    try:
        response = requests.post(
            PERPLEXITY_API_URL,
            headers={
                "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "sonar",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a sports statistics expert. Always respond with valid JSON objects only, no additional text or explanation."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 150,
                "temperature": 0.1
            },
            timeout=15
        )
        
        if response.status_code != 200:
            logger.error(f"Perplexity API returned {response.status_code} for player {player_name}")
            return None
        
        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        parsed_json = _parse_json_from_response(content)
        
        pts_mean = None
        reb_mean = None
        ast_mean = None
        
        if parsed_json:
            if parsed_json.get("unknown"):
                logger.info(f"Perplexity reported unknown player stats for {player_name} - returning None (no defaults)")
                return None
            
            pts_mean = _validate_player_stat(
                parsed_json.get("pts") or parsed_json.get("points") or parsed_json.get("pts_mean"),
                "pts_mean", league
            )
            reb_mean = _validate_player_stat(
                parsed_json.get("reb") or parsed_json.get("rebounds") or parsed_json.get("reb_mean"),
                "reb_mean", league
            )
            ast_mean = _validate_player_stat(
                parsed_json.get("ast") or parsed_json.get("assists") or parsed_json.get("ast_mean"),
                "ast_mean", league
            )
        
        if pts_mean is None:
            pts_mean = _validate_player_stat(
                _extract_number(content, r"(\d+\.?\d*)\s*(?:points|ppg|pts)"),
                "pts_mean", league
            )
            if pts_mean is None:
                pts_mean = _validate_player_stat(
                    _extract_number(content, r"points[:\s]*(\d+\.?\d*)"),
                    "pts_mean", league
                )
        
        if reb_mean is None:
            reb_mean = _validate_player_stat(
                _extract_number(content, r"(\d+\.?\d*)\s*(?:rebounds|rpg|reb)"),
                "reb_mean", league
            )
            if reb_mean is None:
                reb_mean = _validate_player_stat(
                    _extract_number(content, r"rebounds[:\s]*(\d+\.?\d*)"),
                    "reb_mean", league
                )
        
        if ast_mean is None:
            ast_mean = _validate_player_stat(
                _extract_number(content, r"(\d+\.?\d*)\s*(?:assists|apg|ast)"),
                "ast_mean", league
            )
            if ast_mean is None:
                ast_mean = _validate_player_stat(
                    _extract_number(content, r"assists[:\s]*(\d+\.?\d*)"),
                    "ast_mean", league
                )
        
        if pts_mean is None and reb_mean is None and ast_mean is None:
            if attempt < 3:
                logger.info(f"Perplexity attempt {attempt} failed for player {player_name}, trying variation {attempt + 1}")
                return get_player_stats_from_perplexity(player_name, league, attempt + 1)
            logger.warning(f"Could not parse any player stats from Perplexity response for {player_name} after {attempt} attempts")
            return None
        
        if pts_mean is None:
            if attempt < 3:
                logger.info(f"Missing pts_mean for {player_name}, trying variation {attempt + 1}")
                return get_player_stats_from_perplexity(player_name, league, attempt + 1)
            logger.warning(f"Missing pts_mean for {player_name} after {attempt} attempts")
            return None
        
        result = {
            "pts_mean": pts_mean,
            "reb_mean": reb_mean if reb_mean else 0.0,
            "ast_mean": ast_mean if ast_mean else 0.0,
            "source": "perplexity",
            "raw_response": content[:500],
            "fetched_at": datetime.now().isoformat()
        }
        
        _save_cache(cache_path, result)
        logger.info(f"Fetched player stats from Perplexity for {player_name}: pts={result['pts_mean']}, reb={result['reb_mean']}, ast={result['ast_mean']}")
        return result
    
    except requests.exceptions.Timeout:
        logger.error(f"Perplexity API timeout for player {player_name}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error for player {player_name}: {e}")
        return None
    except Exception as e:
        logger.error(f"Perplexity API error for player {player_name}: {e}")
        return None


def _get_espn_team_stats_direct(team_name: str, league: str) -> Optional[Dict[str, Any]]:
    """Get team stats directly from ESPN API."""
    league_path = LEAGUE_PATHS.get(league.upper(), "basketball/nba")
    
    try:
        url = f"{ESPN_API_BASE}/{league_path}/teams"
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        teams = data.get("sports", [{}])[0].get("leagues", [{}])[0].get("teams", [])
        
        team_lower = team_name.lower()
        
        for team_data in teams:
            team_info = team_data.get("team", {})
            display_name = team_info.get("displayName", "")
            short_name = team_info.get("shortDisplayName", "")
            abbreviation = team_info.get("abbreviation", "")
            
            if (team_lower in display_name.lower() or 
                team_lower in short_name.lower() or 
                team_lower == abbreviation.lower()):
                
                team_id = team_info.get("id")
                if team_id:
                    stats = _get_espn_team_statistics(team_id, league)
                    return {
                        "name": display_name,
                        "abbreviation": abbreviation,
                        "id": team_id,
                        "league": league.upper(),
                        "source": "espn",
                        "stats": stats or {}
                    }
        
        return None
    except Exception as e:
        logger.error(f"Error fetching ESPN team stats for {team_name}: {e}")
        return None


def _get_espn_team_statistics(team_id: str, league: str) -> Optional[Dict[str, Any]]:
    """Get detailed team statistics from ESPN."""
    league_path = LEAGUE_PATHS.get(league.upper(), "basketball/nba")
    
    try:
        url = f"{ESPN_API_BASE}/{league_path}/teams/{team_id}/statistics"
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        stats = {}
        
        for category in data.get("splits", {}).get("categories", []):
            for stat in category.get("stats", []):
                stat_name = stat.get("name", "")
                stat_value = stat.get("value", 0)
                stats[stat_name] = stat_value
        
        return stats
    except Exception as e:
        logger.debug(f"Could not fetch detailed stats for team {team_id}: {e}")
        return None


def _estimate_nba_ratings(pts_per_game: float, pace: float) -> tuple:
    """Estimate offensive and defensive ratings for NBA teams."""
    if pace <= 0:
        pace = NBA_DEFAULT_PACE
    off_rating = (pts_per_game / pace) * 100
    def_rating = 100.0
    return off_rating, def_rating


def _estimate_nfl_ratings(points_for: float, points_against: float) -> tuple:
    """Estimate offensive and defensive ratings for NFL teams."""
    off_rating = points_for / NFL_POSSESSIONS_PER_GAME * 100 if points_for > 0 else 100.0
    def_rating = points_against / NFL_POSSESSIONS_PER_GAME * 100 if points_against > 0 else 100.0
    return off_rating, def_rating


def get_team_context(team_name: str, league: str) -> Optional[TeamContext]:
    """
    Get team context with offensive/defensive ratings and other stats.
    
    NEVER GIVE UP FALLBACK CHAIN:
    1. ESPN API
    2. Basketball Reference scraper
    3. NBA.com Stats API (for NBA)
    4. Perplexity AI (with enhanced multi-attempt prompts)
    5. Last Known Good data (stale but real)
    
    Only returns None if the team has NEVER been seen before.
    
    Args:
        team_name: Team name or abbreviation
        league: League code (NBA, NFL, etc.)
    
    Returns:
        TeamContext with team statistics (may be stale but always real data)
    """
    league = league.upper()
    cache_path = _get_cache_path("team_stats", f"{team_name}_{league}")
    sources_tried = []
    
    cached = _load_cache(cache_path)
    if cached and not cached.get("is_stale"):
        logger.debug(f"Loaded team context from cache: {team_name}")
        return TeamContext.from_dict(cached)
    
    context = None
    source = None
    
    sources_tried.append("espn")
    team_stats = _get_espn_team_stats_direct(team_name, league)
    if team_stats:
        context = _build_team_context_from_espn(team_name, league, team_stats)
        if context:
            source = "espn"
    
    if context is None:
        sources_tried.append("bbref")
        team_stats = stats_scraper.get_team_stats(team_name, league)
        if team_stats:
            context = _build_team_context_from_scraper(team_name, league, team_stats)
            if context:
                source = "bbref"
    
    if context is None and league == "NBA":
        sources_tried.append("nba_stats_api")
        try:
            nba_data = nba_stats_api.get_team_advanced_stats(team_name)
            if nba_data and nba_data.get("off_rating") and nba_data.get("def_rating") and nba_data.get("pace"):
                basic_stats = nba_stats_api.get_team_basic_stats(team_name) or {}
                context = TeamContext(
                    name=team_name,
                    league=league,
                    off_rating=nba_data["off_rating"],
                    def_rating=nba_data["def_rating"],
                    pace=nba_data["pace"],
                    pts_per_game=basic_stats.get("pts_per_game", 0.0),
                    fg_pct=basic_stats.get("fg_pct", 0.0),
                    three_pt_pct=basic_stats.get("three_pt_pct", 0.0)
                )
                source = "nba_stats_api"
                logger.info(f"Got team stats from NBA.com for {team_name}")
        except Exception as e:
            logger.warning(f"NBA.com Stats API failed for {team_name}: {e}")
    
    if context is None:
        sources_tried.append("perplexity")
        perplexity_data = get_team_ratings_from_perplexity(team_name, league)
        if perplexity_data and perplexity_data.get("off_rating") and perplexity_data.get("def_rating") and perplexity_data.get("pace"):
            context = TeamContext(
                name=team_name,
                league=league,
                off_rating=perplexity_data["off_rating"],
                def_rating=perplexity_data["def_rating"],
                pace=perplexity_data["pace"],
                pts_per_game=0.0,
                fg_pct=0.0,
                three_pt_pct=0.0
            )
            source = "perplexity"
            logger.info(f"Got team stats from Perplexity for {team_name}")
    
    if context is None:
        sources_tried.append("last_known_good")
        lkg_data = last_known_good.load_team_data(team_name, league)
        if lkg_data and lkg_data.get("off_rating") and lkg_data.get("def_rating") and lkg_data.get("pace"):
            context = TeamContext(
                name=lkg_data.get("team_name", team_name),
                league=league,
                off_rating=lkg_data["off_rating"],
                def_rating=lkg_data["def_rating"],
                pace=lkg_data["pace"],
                pts_per_game=lkg_data.get("pts_per_game", 0.0),
                fg_pct=lkg_data.get("fg_pct", 0.0),
                three_pt_pct=lkg_data.get("three_pt_pct", 0.0)
            )
            source = "last_known_good"
            logger.warning(f"Using STALE Last Known Good data for team {team_name} (age: {lkg_data.get('stale_hours', '?')} hours)")
    
    if context is None:
        logger.error(f"NEVER GIVE UP FAILED: No data found for team {team_name} after trying: {sources_tried}")
        return None
    
    cache_data = context.to_dict()
    cache_data["source"] = source
    cache_data["sources_tried"] = sources_tried
    cache_data["fetched_at"] = datetime.now().isoformat()
    cache_data["is_stale"] = (source == "last_known_good")
    _save_cache(cache_path, cache_data)
    
    if source != "last_known_good":
        last_known_good.save_team_data(team_name, league, context.to_dict(), source)
    
    logger.info(f"Team context for {team_name}: source={source}, off_rtg={context.off_rating:.1f}, def_rtg={context.def_rating:.1f}")
    return context


def _build_team_context_from_espn(team_name: str, league: str, team_stats: Dict[str, Any]) -> Optional[TeamContext]:
    """Build TeamContext from ESPN data."""
    stats = team_stats.get("stats", {})
    
    pts_per_game = stats.get("pts_per_game", stats.get("pointsPerGame", stats.get("avgPointsPerGame", 0)))
    if not pts_per_game or pts_per_game <= 0:
        return None
    
    fg_pct = stats.get("fg_pct", stats.get("fieldGoalPct", stats.get("avgFieldGoalsMade", 0)))
    if not fg_pct or fg_pct <= 0:
        fg_pct = 0.0
    elif fg_pct > 1:
        fg_pct = fg_pct / 100.0
    
    three_pt_pct = stats.get("fg3_pct", stats.get("threePointFieldGoalPct", stats.get("avgThreePointFieldGoalPct", 0)))
    if not three_pt_pct or three_pt_pct <= 0:
        three_pt_pct = 0.0
    elif three_pt_pct > 1:
        three_pt_pct = three_pt_pct / 100.0
    
    if league == "NBA":
        pace = stats.get("pace", 0)
        if not pace or pace <= 0:
            return None
        off_rating, def_rating = _estimate_nba_ratings(pts_per_game, pace)
        if off_rating <= 0 or def_rating <= 0:
            return None
    elif league == "NFL":
        points_for = stats.get("points_for", stats.get("pointsFor", 0))
        if not points_for or points_for <= 0:
            return None
        points_against = stats.get("points_against", stats.get("pointsAgainst", 0))
        if not points_against or points_against <= 0:
            return None
        pace = NFL_POSSESSIONS_PER_GAME
        off_rating, def_rating = _estimate_nfl_ratings(points_for, points_against)
        if off_rating <= 0 or def_rating <= 0:
            return None
        pts_per_game = points_for
    else:
        return None
    
    return TeamContext(
        name=team_stats.get("name", team_name),
        league=league,
        off_rating=off_rating,
        def_rating=def_rating,
        pace=pace,
        pts_per_game=pts_per_game,
        fg_pct=fg_pct,
        three_pt_pct=three_pt_pct
    )


def _build_team_context_from_scraper(team_name: str, league: str, team_stats: Dict[str, Any]) -> Optional[TeamContext]:
    """Build TeamContext from scraper data."""
    off_rating = team_stats.get("off_rating") or team_stats.get("offensive_rating")
    def_rating = team_stats.get("def_rating") or team_stats.get("defensive_rating")
    pace = team_stats.get("pace")
    
    if not off_rating or not def_rating or not pace:
        return None
    
    return TeamContext(
        name=team_name,
        league=league,
        off_rating=float(off_rating),
        def_rating=float(def_rating),
        pace=float(pace),
        pts_per_game=float(team_stats.get("pts_per_game", 0) or 0),
        fg_pct=float(team_stats.get("fg_pct", 0) or 0),
        three_pt_pct=float(team_stats.get("three_pt_pct", 0) or 0)
    )


def get_player_context(player_name: str, league: str) -> Optional[PlayerContext]:
    """
    Get player context with season averages and variance estimates.
    
    NEVER GIVE UP FALLBACK CHAIN:
    1. ESPN/BBRef scraper
    2. Ball Don't Lie API (NBA only - free, saves Perplexity credits)
    3. Perplexity AI (with enhanced multi-attempt prompts)
    4. Last Known Good data (stale but real)
    
    Only returns None if the player has NEVER been seen before.
    
    Args:
        player_name: Player's full name
        league: League code (NBA, NFL, etc.)
    
    Returns:
        PlayerContext with player statistics (may be stale but always real data)
    """
    league = league.upper()
    cache_path = _get_cache_path("player_stats", f"{player_name}_{league}")
    sources_tried = []
    
    cached = _load_cache(cache_path)
    if cached and not cached.get("is_stale"):
        logger.debug(f"Loaded player context from cache: {player_name}")
        return PlayerContext.from_dict(cached)
    
    context = None
    source = None
    
    sources_tried.append("bbref")
    player_stats = stats_scraper.get_player_stats(player_name, league)
    
    has_season_averages = (
        player_stats is not None and 
        player_stats.get("season_averages") and 
        len(player_stats.get("season_averages", {})) > 0
    )
    
    if has_season_averages:
        context = _build_player_context_from_scraper(player_name, player_stats)
        if context:
            source = "bbref"
    
    if context is None and league == "NBA":
        sources_tried.append("balldontlie")
        bdl_data = get_player_stats_from_balldontlie(player_name)
        
        if bdl_data and bdl_data.get("pts_mean"):
            pts_mean = bdl_data["pts_mean"]
            reb_mean = bdl_data.get("reb_mean", 0.0) or 0.0
            ast_mean = bdl_data.get("ast_mean", 0.0) or 0.0
            
            usage_rate = min(0.35, pts_mean / 50.0) if pts_mean > 0 else 0.15
            pts_std = pts_mean * 0.25 if pts_mean > 0 else 2.5
            reb_std = reb_mean * 0.25 if reb_mean > 0 else 1.0
            ast_std = ast_mean * 0.25 if ast_mean > 0 else 0.75
            
            context = PlayerContext(
                name=player_name,
                team=bdl_data.get("team", ""),
                position=bdl_data.get("position", ""),
                usage_rate=usage_rate,
                pts_mean=pts_mean,
                pts_std=pts_std,
                reb_mean=reb_mean,
                reb_std=reb_std,
                ast_mean=ast_mean,
                ast_std=ast_std
            )
            source = "balldontlie"
            logger.info(f"Got player stats from Ball Don't Lie for {player_name}")
    
    if context is None:
        sources_tried.append("perplexity")
        perplexity_data = get_player_stats_from_perplexity(player_name, league)
        
        if perplexity_data and perplexity_data.get("pts_mean"):
            pts_mean = perplexity_data["pts_mean"]
            reb_mean = perplexity_data.get("reb_mean", 0.0) or 0.0
            ast_mean = perplexity_data.get("ast_mean", 0.0) or 0.0
            
            usage_rate = min(0.35, pts_mean / 50.0) if pts_mean > 0 else 0.15
            pts_std = pts_mean * 0.25 if pts_mean > 0 else 2.5
            reb_std = reb_mean * 0.25 if reb_mean > 0 else 1.0
            ast_std = ast_mean * 0.25 if ast_mean > 0 else 0.75
            
            team = player_stats.get("team", "") if player_stats else ""
            position = player_stats.get("position", "") if player_stats else ""
            
            context = PlayerContext(
                name=player_name,
                team=team,
                position=position,
                usage_rate=usage_rate,
                pts_mean=pts_mean,
                pts_std=pts_std,
                reb_mean=reb_mean,
                reb_std=reb_std,
                ast_mean=ast_mean,
                ast_std=ast_std
            )
            source = "perplexity"
            logger.info(f"Got player stats from Perplexity for {player_name}")
    
    if context is None:
        sources_tried.append("last_known_good")
        lkg_data = last_known_good.load_player_data(player_name, league)
        if lkg_data and lkg_data.get("pts_mean"):
            context = PlayerContext(
                name=lkg_data.get("player_name", player_name),
                team=lkg_data.get("team", ""),
                position=lkg_data.get("position", ""),
                usage_rate=lkg_data.get("usage_rate", 0.15),
                pts_mean=lkg_data["pts_mean"],
                pts_std=lkg_data.get("pts_std", lkg_data["pts_mean"] * 0.25),
                reb_mean=lkg_data.get("reb_mean", 0.0),
                reb_std=lkg_data.get("reb_std", 0.0),
                ast_mean=lkg_data.get("ast_mean", 0.0),
                ast_std=lkg_data.get("ast_std", 0.0)
            )
            source = "last_known_good"
            logger.warning(f"Using STALE Last Known Good data for player {player_name} (age: {lkg_data.get('stale_hours', '?')} hours)")
    
    if context is None:
        logger.error(f"NEVER GIVE UP FAILED: No data found for player {player_name} after trying: {sources_tried}")
        return None
    
    cache_data = context.to_dict()
    cache_data["source"] = source
    cache_data["sources_tried"] = sources_tried
    cache_data["fetched_at"] = datetime.now().isoformat()
    cache_data["is_stale"] = (source == "last_known_good")
    _save_cache(cache_path, cache_data)
    
    if source != "last_known_good":
        last_known_good.save_player_data(player_name, league, context.to_dict(), source)
    
    logger.info(f"Player context for {player_name}: source={source}, pts={context.pts_mean:.1f}")
    return context


def _build_player_context_from_scraper(player_name: str, player_stats: Dict[str, Any]) -> Optional[PlayerContext]:
    """Build PlayerContext from scraper data."""
    season_avg = player_stats.get("season_averages", {})
    
    pts_mean = season_avg.get("pts_per_g") or season_avg.get("pts")
    reb_mean = season_avg.get("trb_per_g") or season_avg.get("reb") or 0.0
    ast_mean = season_avg.get("ast_per_g") or season_avg.get("ast") or 0.0
    
    if pts_mean is None or pts_mean <= 0:
        return None
    
    fga = season_avg.get("fga_per_g", 0)
    if fga > 0:
        team_fga = 85.0
        usage_rate = min(0.40, fga / team_fga)
    else:
        usage_rate = min(0.35, pts_mean / 50.0) if pts_mean > 0 else 0.15
    
    pts_std = pts_mean * 0.25 if pts_mean > 0 else 0.0
    reb_std = reb_mean * 0.25 if reb_mean > 0 else 0.0
    ast_std = ast_mean * 0.25 if ast_mean > 0 else 0.0
    
    return PlayerContext(
        name=player_stats.get("name", player_name),
        team=player_stats.get("team", ""),
        position=player_stats.get("position", ""),
        usage_rate=usage_rate,
        pts_mean=pts_mean,
        pts_std=pts_std,
        reb_mean=reb_mean,
        reb_std=reb_std,
        ast_mean=ast_mean,
        ast_std=ast_std
    )


def _get_espn_team_roster(team_id: str, league: str, limit: int = 8) -> List[Dict[str, Any]]:
    """Get top players from team roster via ESPN API."""
    league_path = LEAGUE_PATHS.get(league.upper(), "basketball/nba")
    
    try:
        url = f"{ESPN_API_BASE}/{league_path}/teams/{team_id}/roster"
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        
        if response.status_code != 200:
            return []
        
        data = response.json()
        athletes = data.get("athletes", [])
        
        players = []
        for athlete in athletes[:limit]:
            player_info = {
                "id": athlete.get("id"),
                "name": athlete.get("fullName", athlete.get("displayName", "")),
                "position": athlete.get("position", {}).get("abbreviation", ""),
                "jersey": athlete.get("jersey", "")
            }
            players.append(player_info)
        
        return players
    except Exception as e:
        logger.error(f"Error fetching ESPN roster for team {team_id}: {e}")
        return []


def _get_team_id_from_name(team_name: str, league: str) -> Optional[str]:
    """Look up ESPN team ID from team name."""
    league_path = LEAGUE_PATHS.get(league.upper(), "basketball/nba")
    
    try:
        url = f"{ESPN_API_BASE}/{league_path}/teams"
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        teams = data.get("sports", [{}])[0].get("leagues", [{}])[0].get("teams", [])
        
        team_lower = team_name.lower()
        
        for team_data in teams:
            team_info = team_data.get("team", {})
            display_name = team_info.get("displayName", "")
            short_name = team_info.get("shortDisplayName", "")
            abbreviation = team_info.get("abbreviation", "")
            
            if (team_lower in display_name.lower() or 
                team_lower in short_name.lower() or 
                team_lower == abbreviation.lower()):
                return team_info.get("id")
        
        return None
    except Exception as e:
        logger.error(f"Error looking up team ID for {team_name}: {e}")
        return None


def get_game_context(home_team: str, away_team: str, league: str) -> Dict[str, Any]:
    """
    Get full game context including both teams and top players.
    
    Args:
        home_team: Home team name or abbreviation
        away_team: Away team name or abbreviation
        league: League code (NBA, NFL, etc.)
    
    Returns:
        Dictionary with home_context, away_context, home_players, away_players
    """
    league = league.upper()
    
    home_context = get_team_context(home_team, league)
    away_context = get_team_context(away_team, league)
    
    home_team_id = _get_team_id_from_name(home_team, league)
    away_team_id = _get_team_id_from_name(away_team, league)
    
    home_roster = []
    away_roster = []
    
    if home_team_id:
        roster_players = _get_espn_team_roster(home_team_id, league, limit=8)
        for player_info in roster_players:
            try:
                player_context = get_player_context(player_info["name"], league)
                home_roster.append(player_context.to_dict())
            except Exception as e:
                logger.warning(f"Could not get context for {player_info.get('name')}: {e}")
                home_roster.append({
                    "name": player_info.get("name", "Unknown"),
                    "team": home_team,
                    "position": player_info.get("position", ""),
                    "usage_rate": 0.15,
                    "pts_mean": 10.0,
                    "pts_std": 2.5,
                    "reb_mean": 4.0,
                    "reb_std": 1.0,
                    "ast_mean": 3.0,
                    "ast_std": 0.75
                })
    
    if away_team_id:
        roster_players = _get_espn_team_roster(away_team_id, league, limit=8)
        for player_info in roster_players:
            try:
                player_context = get_player_context(player_info["name"], league)
                away_roster.append(player_context.to_dict())
            except Exception as e:
                logger.warning(f"Could not get context for {player_info.get('name')}: {e}")
                away_roster.append({
                    "name": player_info.get("name", "Unknown"),
                    "team": away_team,
                    "position": player_info.get("position", ""),
                    "usage_rate": 0.15,
                    "pts_mean": 10.0,
                    "pts_std": 2.5,
                    "reb_mean": 4.0,
                    "reb_std": 1.0,
                    "ast_mean": 3.0,
                    "ast_std": 0.75
                })
    
    return {
        "league": league,
        "home_team": home_team,
        "away_team": away_team,
        "home_context": home_context.to_dict(),
        "away_context": away_context.to_dict(),
        "home_players": home_roster,
        "away_players": away_roster,
        "timestamp": datetime.now().isoformat()
    }


def clear_cache(older_than_days: int = 1) -> int:
    """
    Clear stale cache files.
    
    Args:
        older_than_days: Remove files older than this many days (default 1)
    
    Returns:
        Number of files removed
    """
    if not os.path.exists(CACHE_DIR):
        return 0
    
    removed = 0
    now = datetime.now()
    
    try:
        for filename in os.listdir(CACHE_DIR):
            if not (filename.startswith("team_stats_") or filename.startswith("player_stats_")):
                continue
            
            filepath = os.path.join(CACHE_DIR, filename)
            
            try:
                file_stat = os.stat(filepath)
                file_time = datetime.fromtimestamp(file_stat.st_mtime)
                age_days = (now - file_time).days
                
                if age_days >= older_than_days:
                    os.remove(filepath)
                    removed += 1
                    logger.debug(f"Removed stale cache file: {filename}")
            except Exception as e:
                logger.warning(f"Error processing cache file {filename}: {e}")
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
    
    logger.info(f"Cleared {removed} stale cache files")
    return removed


def clear_all_cache() -> int:
    """
    Clear all stats ingestion cache files.
    
    Returns:
        Number of files removed
    """
    return clear_cache(older_than_days=0)
