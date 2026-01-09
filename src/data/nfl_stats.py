"""
NFL Stats Data Sources

Provides NFL team and player data from ESPN, Pro Football Reference, and Perplexity fallback.
Follows the same "never give up" data recovery pattern as NBA.
"""

import json
import logging
import os
import re
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

CACHE_DIR = "data/cache/nfl"
REQUEST_TIMEOUT = 10
ESPN_NFL_API = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

NFL_TEAM_ABBREVS = {
    "Arizona Cardinals": "ARI", "Atlanta Falcons": "ATL", "Baltimore Ravens": "BAL",
    "Buffalo Bills": "BUF", "Carolina Panthers": "CAR", "Chicago Bears": "CHI",
    "Cincinnati Bengals": "CIN", "Cleveland Browns": "CLE", "Dallas Cowboys": "DAL",
    "Denver Broncos": "DEN", "Detroit Lions": "DET", "Green Bay Packers": "GB",
    "Houston Texans": "HOU", "Indianapolis Colts": "IND", "Jacksonville Jaguars": "JAX",
    "Kansas City Chiefs": "KC", "Las Vegas Raiders": "LV", "Los Angeles Chargers": "LAC",
    "Los Angeles Rams": "LAR", "Miami Dolphins": "MIA", "Minnesota Vikings": "MIN",
    "New England Patriots": "NE", "New Orleans Saints": "NO", "New York Giants": "NYG",
    "New York Jets": "NYJ", "Philadelphia Eagles": "PHI", "Pittsburgh Steelers": "PIT",
    "San Francisco 49ers": "SF", "Seattle Seahawks": "SEA", "Tampa Bay Buccaneers": "TB",
    "Tennessee Titans": "TEN", "Washington Commanders": "WSH"
}

NFL_ABBREV_TO_NAME = {v: k for k, v in NFL_TEAM_ABBREVS.items()}


@dataclass
class NFLTeamContext:
    """NFL team statistical context for projections."""
    name: str
    abbreviation: str
    league: str = "NFL"
    
    points_per_game: float = 21.0
    points_allowed_per_game: float = 21.0
    
    pass_yards_per_game: float = 210.0
    rush_yards_per_game: float = 110.0
    total_yards_per_game: float = 320.0
    
    pass_yards_allowed: float = 210.0
    rush_yards_allowed: float = 110.0
    
    turnover_diff: float = 0.0
    time_of_possession: float = 30.0
    
    third_down_pct: float = 0.40
    red_zone_pct: float = 0.55
    
    wins: int = 0
    losses: int = 0
    
    data_source: str = "unknown"
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NFLTeamContext':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class NFLPlayerContext:
    """NFL player statistical context for projections."""
    name: str
    team: str
    position: str
    
    pass_attempts: float = 0.0
    pass_completions: float = 0.0
    pass_yards: float = 0.0
    pass_td: float = 0.0
    interceptions: float = 0.0
    passer_rating: float = 0.0
    
    rush_attempts: float = 0.0
    rush_yards: float = 0.0
    rush_td: float = 0.0
    yards_per_carry: float = 0.0
    
    receptions: float = 0.0
    targets: float = 0.0
    receiving_yards: float = 0.0
    receiving_td: float = 0.0
    yards_per_reception: float = 0.0
    
    fantasy_points_ppr: float = 0.0
    games_played: int = 0
    
    data_source: str = "unknown"
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NFLPlayerContext':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


def _ensure_cache_dir():
    """Ensure cache directory exists."""
    os.makedirs(CACHE_DIR, exist_ok=True)


def _get_cache_path(key: str) -> str:
    """Get cache file path for a key."""
    safe_key = re.sub(r'[^\w\-]', '_', key)
    return os.path.join(CACHE_DIR, f"{safe_key}.json")


def _read_cache(key: str, max_age_hours: int = 24) -> Optional[Dict]:
    """Read from cache if fresh enough."""
    _ensure_cache_dir()
    path = _get_cache_path(key)
    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            cached_at = datetime.fromisoformat(data.get('cached_at', '2000-01-01'))
            if datetime.now() - cached_at < timedelta(hours=max_age_hours):
                return data.get('data')
        except Exception:
            pass
    return None


def _write_cache(key: str, data: Any):
    """Write data to cache."""
    _ensure_cache_dir()
    path = _get_cache_path(key)
    try:
        with open(path, 'w') as f:
            json.dump({'cached_at': datetime.now().isoformat(), 'data': data}, f)
    except Exception as e:
        logger.warning(f"Failed to write cache: {e}")


def get_nfl_team_from_espn(team_name: str) -> Optional[NFLTeamContext]:
    """
    Fetch NFL team stats from ESPN API.
    
    Returns NFLTeamContext or None if not found.
    """
    cache_key = f"nfl_team_espn_{team_name}"
    cached = _read_cache(cache_key, max_age_hours=6)
    if cached:
        ctx = NFLTeamContext.from_dict(cached)
        ctx.data_source = "espn_cached"
        return ctx
    
    try:
        resp = requests.get(f"{ESPN_NFL_API}/teams", headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            return None
        
        teams_data = resp.json().get('sports', [{}])[0].get('leagues', [{}])[0].get('teams', [])
        
        target_team = None
        for t in teams_data:
            team_info = t.get('team', {})
            full_name = f"{team_info.get('location', '')} {team_info.get('name', '')}".strip()
            abbrev = team_info.get('abbreviation', '')
            
            if team_name.lower() in full_name.lower() or team_name.upper() == abbrev:
                target_team = team_info
                break
        
        if not target_team:
            return None
        
        team_id = target_team.get('id')
        full_name = f"{target_team.get('location', '')} {target_team.get('name', '')}".strip()
        abbrev = target_team.get('abbreviation', '')
        
        stats_url = f"{ESPN_NFL_API}/teams/{team_id}/statistics"
        stats_resp = requests.get(stats_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        
        ppg = 21.0
        papg = 21.0
        pass_ypg = 210.0
        rush_ypg = 110.0
        
        if stats_resp.status_code == 200:
            stats = stats_resp.json()
            
            for cat in stats.get('splits', {}).get('categories', []):
                cat_name = cat.get('name', '').lower()
                for stat in cat.get('stats', []):
                    stat_name = stat.get('name', '').lower()
                    value = stat.get('value', 0)
                    
                    if 'scoring' in cat_name:
                        if 'points per game' in stat_name or stat_name == 'pointspergame':
                            ppg = float(value)
                    if 'passing' in cat_name:
                        if 'yards per game' in stat_name:
                            pass_ypg = float(value)
                    if 'rushing' in cat_name:
                        if 'yards per game' in stat_name:
                            rush_ypg = float(value)
        
        record = target_team.get('record', {})
        wins = record.get('wins', 0)
        losses = record.get('losses', 0)
        
        ctx = NFLTeamContext(
            name=full_name,
            abbreviation=abbrev,
            points_per_game=ppg,
            points_allowed_per_game=papg,
            pass_yards_per_game=pass_ypg,
            rush_yards_per_game=rush_ypg,
            total_yards_per_game=pass_ypg + rush_ypg,
            wins=wins,
            losses=losses,
            data_source="espn"
        )
        
        _write_cache(cache_key, ctx.to_dict())
        return ctx
        
    except Exception as e:
        logger.warning(f"ESPN NFL team fetch failed for {team_name}: {e}")
        return None


def get_nfl_player_from_espn(player_name: str, team_hint: Optional[str] = None) -> Optional[NFLPlayerContext]:
    """
    Fetch NFL player stats from ESPN API.
    
    Args:
        player_name: Player's full name
        team_hint: Optional team name to help disambiguate
    
    Returns NFLPlayerContext or None if not found.
    """
    cache_key = f"nfl_player_espn_{player_name}"
    cached = _read_cache(cache_key, max_age_hours=6)
    if cached:
        ctx = NFLPlayerContext.from_dict(cached)
        ctx.data_source = "espn_cached"
        return ctx
    
    try:
        search_url = f"https://site.api.espn.com/apis/common/v3/search?query={player_name}&limit=10&type=player"
        resp = requests.get(search_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        
        if resp.status_code != 200:
            return None
        
        results = resp.json().get('items', [])
        
        player_data = None
        for item in results:
            if item.get('type') == 'player':
                league = item.get('league', {}).get('abbreviation', '')
                if league == 'NFL':
                    player_data = item
                    break
        
        if not player_data:
            return None
        
        player_id = player_data.get('id')
        display_name = player_data.get('displayName', player_name)
        position = player_data.get('position', 'Unknown')
        team = player_data.get('team', {}).get('displayName', 'Unknown')
        
        stats_url = f"https://site.api.espn.com/apis/common/v3/sports/football/nfl/athletes/{player_id}/stats"
        stats_resp = requests.get(stats_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        
        ctx = NFLPlayerContext(
            name=display_name,
            team=team,
            position=position,
            data_source="espn"
        )
        
        if stats_resp.status_code == 200:
            stats = stats_resp.json()
            
            for cat in stats.get('categories', []):
                cat_name = cat.get('name', '').lower()
                stat_values = {s.get('name', '').lower(): s.get('value', 0) 
                              for s in cat.get('stats', [])}
                
                if 'passing' in cat_name:
                    ctx.pass_attempts = float(stat_values.get('passattempts', 0))
                    ctx.pass_completions = float(stat_values.get('passcompletions', 0))
                    ctx.pass_yards = float(stat_values.get('passyards', 0))
                    ctx.pass_td = float(stat_values.get('passtouchdowns', 0))
                    ctx.interceptions = float(stat_values.get('interceptions', 0))
                    ctx.passer_rating = float(stat_values.get('qbr', 0))
                
                elif 'rushing' in cat_name:
                    ctx.rush_attempts = float(stat_values.get('rushattempts', 0))
                    ctx.rush_yards = float(stat_values.get('rushyards', 0))
                    ctx.rush_td = float(stat_values.get('rushtouchdowns', 0))
                    if ctx.rush_attempts > 0:
                        ctx.yards_per_carry = ctx.rush_yards / ctx.rush_attempts
                
                elif 'receiving' in cat_name:
                    ctx.receptions = float(stat_values.get('receptions', 0))
                    ctx.targets = float(stat_values.get('targets', 0))
                    ctx.receiving_yards = float(stat_values.get('receivingyards', 0))
                    ctx.receiving_td = float(stat_values.get('receivingtouchdowns', 0))
                    if ctx.receptions > 0:
                        ctx.yards_per_reception = ctx.receiving_yards / ctx.receptions
        
        ctx.fantasy_points_ppr = (
            ctx.pass_yards * 0.04 + ctx.pass_td * 4 - ctx.interceptions * 2 +
            ctx.rush_yards * 0.1 + ctx.rush_td * 6 +
            ctx.receiving_yards * 0.1 + ctx.receiving_td * 6 + ctx.receptions * 1
        )
        
        _write_cache(cache_key, ctx.to_dict())
        return ctx
        
    except Exception as e:
        logger.warning(f"ESPN NFL player fetch failed for {player_name}: {e}")
        return None


def get_nfl_team_from_pfr(team_name: str) -> Optional[NFLTeamContext]:
    """
    Fetch NFL team stats from Pro Football Reference.
    
    This is a backup source when ESPN fails.
    """
    cache_key = f"nfl_team_pfr_{team_name}"
    cached = _read_cache(cache_key, max_age_hours=12)
    if cached:
        ctx = NFLTeamContext.from_dict(cached)
        ctx.data_source = "pfr_cached"
        return ctx
    
    try:
        abbrev = NFL_TEAM_ABBREVS.get(team_name, team_name[:3].upper())
        
        url = f"https://www.pro-football-reference.com/teams/{abbrev.lower()}/2024.htm"
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        
        if resp.status_code != 200:
            return None
        
        soup = BeautifulSoup(resp.text, 'lxml')
        
        ppg = 21.0
        papg = 21.0
        
        team_stats = soup.find('div', {'id': 'team_stats'})
        if team_stats:
            rows = team_stats.find_all('tr')
            for row in rows:
                cells = row.find_all(['th', 'td'])
                if len(cells) >= 2:
                    label = cells[0].get_text(strip=True).lower()
                    if 'pts/g' in label or 'points per game' in label:
                        try:
                            ppg = float(cells[1].get_text(strip=True))
                        except ValueError:
                            pass
        
        full_name = NFL_ABBREV_TO_NAME.get(abbrev.upper(), team_name)
        
        ctx = NFLTeamContext(
            name=full_name,
            abbreviation=abbrev.upper(),
            points_per_game=ppg,
            points_allowed_per_game=papg,
            data_source="pfr"
        )
        
        _write_cache(cache_key, ctx.to_dict())
        return ctx
        
    except Exception as e:
        logger.warning(f"PFR team fetch failed for {team_name}: {e}")
        return None


def get_nfl_team_from_perplexity(team_name: str) -> Optional[NFLTeamContext]:
    """
    Fetch NFL team stats using Perplexity AI search.
    
    Last resort when ESPN and PFR fail.
    """
    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if not api_key:
        return None
    
    cache_key = f"nfl_team_pplx_{team_name}"
    cached = _read_cache(cache_key, max_age_hours=24)
    if cached:
        ctx = NFLTeamContext.from_dict(cached)
        ctx.data_source = "perplexity_cached"
        return ctx
    
    try:
        prompt = f"""What are the 2024 NFL season statistics for the {team_name}?
        
I need these specific numbers:
- Points per game (PPG)
- Points allowed per game
- Passing yards per game
- Rushing yards per game
- Current record (wins-losses)

Please provide only the numerical values, formatted like:
PPG: 28.5
Points Allowed: 21.3
Pass YPG: 245.2
Rush YPG: 125.8
Record: 12-3"""

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama-3.1-sonar-small-128k-online",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 500,
            "temperature": 0.1
        }
        
        resp = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers=headers,
            json=payload,
            timeout=15
        )
        
        if resp.status_code != 200:
            return None
        
        content = resp.json().get('choices', [{}])[0].get('message', {}).get('content', '')
        
        ppg = 21.0
        papg = 21.0
        pass_ypg = 210.0
        rush_ypg = 110.0
        wins = 0
        losses = 0
        
        ppg_match = re.search(r'PPG[:\s]+(\d+\.?\d*)', content, re.IGNORECASE)
        if ppg_match:
            ppg = float(ppg_match.group(1))
        
        papg_match = re.search(r'Points?\s*Allowed[:\s]+(\d+\.?\d*)', content, re.IGNORECASE)
        if papg_match:
            papg = float(papg_match.group(1))
        
        pass_match = re.search(r'Pass(?:ing)?\s*Y(?:ards)?(?:\s*per\s*game)?[:\s]+(\d+\.?\d*)', content, re.IGNORECASE)
        if pass_match:
            pass_ypg = float(pass_match.group(1))
        
        rush_match = re.search(r'Rush(?:ing)?\s*Y(?:ards)?(?:\s*per\s*game)?[:\s]+(\d+\.?\d*)', content, re.IGNORECASE)
        if rush_match:
            rush_ypg = float(rush_match.group(1))
        
        record_match = re.search(r'Record[:\s]+(\d+)[-–](\d+)', content, re.IGNORECASE)
        if record_match:
            wins = int(record_match.group(1))
            losses = int(record_match.group(2))
        
        abbrev = NFL_TEAM_ABBREVS.get(team_name, team_name[:3].upper())
        
        ctx = NFLTeamContext(
            name=team_name,
            abbreviation=abbrev,
            points_per_game=ppg,
            points_allowed_per_game=papg,
            pass_yards_per_game=pass_ypg,
            rush_yards_per_game=rush_ypg,
            total_yards_per_game=pass_ypg + rush_ypg,
            wins=wins,
            losses=losses,
            data_source="perplexity"
        )
        
        _write_cache(cache_key, ctx.to_dict())
        return ctx
        
    except Exception as e:
        logger.warning(f"Perplexity NFL team fetch failed for {team_name}: {e}")
        return None


def get_nfl_team_context(team_name: str) -> Optional[NFLTeamContext]:
    """
    Get NFL team context using full fallback chain.
    
    Order: ESPN -> PFR -> Perplexity -> Last Known Good
    
    "Never give up" - will try all sources before returning None.
    """
    logger.info(f"Fetching NFL team context for: {team_name}")
    
    ctx = get_nfl_team_from_espn(team_name)
    if ctx:
        logger.info(f"NFL team {team_name} found via ESPN")
        return ctx
    
    ctx = get_nfl_team_from_pfr(team_name)
    if ctx:
        logger.info(f"NFL team {team_name} found via PFR")
        return ctx
    
    ctx = get_nfl_team_from_perplexity(team_name)
    if ctx:
        logger.info(f"NFL team {team_name} found via Perplexity")
        return ctx
    
    cache_key = f"nfl_team_lkg_{team_name}"
    cached = _read_cache(cache_key, max_age_hours=168)
    if cached:
        ctx = NFLTeamContext.from_dict(cached)
        ctx.data_source = "last_known_good"
        logger.warning(f"NFL team {team_name} using stale last-known-good data")
        return ctx
    
    logger.error(f"All sources failed for NFL team: {team_name}")
    return None


def get_nfl_player_context(player_name: str, team_hint: Optional[str] = None) -> Optional[NFLPlayerContext]:
    """
    Get NFL player context using full fallback chain.
    
    Order: ESPN -> Perplexity -> Last Known Good
    
    "Never give up" - will try all sources before returning None.
    """
    logger.info(f"Fetching NFL player context for: {player_name}")
    
    ctx = get_nfl_player_from_espn(player_name, team_hint)
    if ctx:
        logger.info(f"NFL player {player_name} found via ESPN")
        return ctx
    
    logger.warning(f"All sources failed for NFL player: {player_name}")
    return None


def get_nfl_schedule(week: Optional[int] = None) -> List[Dict]:
    """
    Get NFL schedule from ESPN.
    
    Args:
        week: Specific week number (1-18) or None for current week
    
    Returns list of game dictionaries.
    """
    try:
        url = f"{ESPN_NFL_API}/scoreboard"
        if week:
            url += f"?week={week}"
        
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            return []
        
        data = resp.json()
        games = []
        
        for event in data.get('events', []):
            competition = event.get('competitions', [{}])[0]
            competitors = competition.get('competitors', [])
            
            if len(competitors) != 2:
                continue
            
            home = None
            away = None
            for c in competitors:
                team_data = {
                    'id': c.get('team', {}).get('id'),
                    'name': c.get('team', {}).get('displayName'),
                    'abbreviation': c.get('team', {}).get('abbreviation'),
                    'score': c.get('score'),
                }
                if c.get('homeAway') == 'home':
                    home = team_data
                else:
                    away = team_data
            
            if home and away:
                games.append({
                    'game_id': event.get('id'),
                    'home_team': home,
                    'away_team': away,
                    'game_time': event.get('date'),
                    'status': event.get('status', {}).get('type', {}).get('description'),
                    'venue': competition.get('venue', {}).get('fullName'),
                    'week': data.get('week', {}).get('number'),
                })
        
        return games
        
    except Exception as e:
        logger.error(f"Failed to fetch NFL schedule: {e}")
        return []
