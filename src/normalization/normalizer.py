"""
Name Normalizer — stateless name cleaning for entities.

Does NOT require the DB. Used before entity resolution to clean up
raw names from providers and user prompts.
"""

from __future__ import annotations

import re
from typing import Dict

# ---------------------------------------------------------------------------
# Team name normalization tables
# ---------------------------------------------------------------------------

# Common abbreviation → full name mappings (NBA)
_NBA_TEAM_NAMES: Dict[str, str] = {
    "lal": "Los Angeles Lakers", "lakers": "Los Angeles Lakers",
    "gsw": "Golden State Warriors", "warriors": "Golden State Warriors",
    "bos": "Boston Celtics", "celtics": "Boston Celtics",
    "mil": "Milwaukee Bucks", "bucks": "Milwaukee Bucks",
    "den": "Denver Nuggets", "nuggets": "Denver Nuggets",
    "phi": "Philadelphia 76ers", "76ers": "Philadelphia 76ers", "sixers": "Philadelphia 76ers",
    "mia": "Miami Heat", "heat": "Miami Heat",
    "nyk": "New York Knicks", "knicks": "New York Knicks",
    "dal": "Dallas Mavericks", "mavs": "Dallas Mavericks", "mavericks": "Dallas Mavericks",
    "phx": "Phoenix Suns", "suns": "Phoenix Suns",
    "lac": "Los Angeles Clippers", "clippers": "Los Angeles Clippers",
    "sac": "Sacramento Kings", "kings": "Sacramento Kings",
    "min": "Minnesota Timberwolves", "wolves": "Minnesota Timberwolves", "timberwolves": "Minnesota Timberwolves",
    "cle": "Cleveland Cavaliers", "cavs": "Cleveland Cavaliers", "cavaliers": "Cleveland Cavaliers",
    "atl": "Atlanta Hawks", "hawks": "Atlanta Hawks",
    "tor": "Toronto Raptors", "raptors": "Toronto Raptors",
    "chi": "Chicago Bulls", "bulls": "Chicago Bulls",
    "ind": "Indiana Pacers", "pacers": "Indiana Pacers",
    "okc": "Oklahoma City Thunder", "thunder": "Oklahoma City Thunder",
    "orl": "Orlando Magic", "magic": "Orlando Magic",
    "hou": "Houston Rockets", "rockets": "Houston Rockets",
    "mem": "Memphis Grizzlies", "grizzlies": "Memphis Grizzlies",
    "nor": "New Orleans Pelicans", "pelicans": "New Orleans Pelicans",
    "por": "Portland Trail Blazers", "blazers": "Portland Trail Blazers",
    "uta": "Utah Jazz", "jazz": "Utah Jazz",
    "was": "Washington Wizards", "wizards": "Washington Wizards",
    "det": "Detroit Pistons", "pistons": "Detroit Pistons",
    "cha": "Charlotte Hornets", "hornets": "Charlotte Hornets",
    "sas": "San Antonio Spurs", "spurs": "San Antonio Spurs",
    "bkn": "Brooklyn Nets", "nets": "Brooklyn Nets",
}

# City shorthand → canonical
_CITY_NORMALIZATIONS: Dict[str, str] = {
    "la lakers": "Los Angeles Lakers",
    "la clippers": "Los Angeles Clippers",
    "ny knicks": "New York Knicks",
    "gs warriors": "Golden State Warriors",
    "okc thunder": "Oklahoma City Thunder",
    "no pelicans": "New Orleans Pelicans",
    "sa spurs": "San Antonio Spurs",
}

# League code normalization
_LEAGUE_ALIASES: Dict[str, str] = {
    "nba": "NBA", "nfl": "NFL", "mlb": "MLB", "nhl": "NHL",
    "ncaab": "NCAAB", "ncaam": "NCAAB", "march madness": "NCAAB",
    "college basketball": "NCAAB", "ncaaf": "NCAAF",
    "college football": "NCAAF", "epl": "EPL",
    "premier league": "EPL", "ufc": "UFC", "mma": "UFC",
    "atp": "ATP", "wta": "WTA", "tennis": "ATP",
    "pga": "PGA", "pga tour": "PGA", "golf": "PGA",
    "cs2": "CS2", "csgo": "CS2", "esports": "ESPORTS",
    "wnba": "WNBA", "cfl": "CFL", "xfl": "XFL",
    "boxing": "BOXING", "bellator": "BELLATOR",
    "mls": "MLS", "la liga": "LA_LIGA", "laliga": "LA_LIGA",
    "bundesliga": "BUNDESLIGA", "serie a": "SERIE_A",
    "ligue 1": "LIGUE_1", "champions league": "CHAMPIONS_LEAGUE",
}


def normalize_team_name(raw: str, league: str) -> str:
    """Normalize a team name.

    Handles abbreviations, city shorthand, and common nicknames.
    Returns the best canonical form available, or the cleaned input
    if no mapping is found.
    """
    cleaned = raw.strip()
    if not cleaned:
        return cleaned

    lower = cleaned.lower()

    # Check direct mapping
    if lower in _NBA_TEAM_NAMES and league.upper() == "NBA":
        return _NBA_TEAM_NAMES[lower]

    # Check city normalizations
    if lower in _CITY_NORMALIZATIONS:
        return _CITY_NORMALIZATIONS[lower]

    # Strip "the " prefix
    if lower.startswith("the "):
        cleaned = cleaned[4:]

    # Title-case if all lowercase
    if cleaned == cleaned.lower():
        cleaned = cleaned.title()

    return cleaned


def normalize_player_name(raw: str) -> str:
    """Normalize a player name.

    Handles encoding issues, extra whitespace, and common prefixes/suffixes.
    Does NOT expand initials (that requires entity resolution).
    """
    cleaned = raw.strip()
    if not cleaned:
        return cleaned

    # Fix multiple spaces
    cleaned = re.sub(r"\s+", " ", cleaned)

    # Remove common suffixes like "Jr.", "Sr.", "III" — keep them but normalize
    # (Don't remove — they're disambiguating)

    # Fix encoding issues
    cleaned = cleaned.replace("\u2019", "'")  # smart quote
    cleaned = cleaned.replace("\u00e9", "e")  # accented e (common in European names)

    return cleaned


def normalize_league(raw: str) -> str:
    """Normalize a league code to uppercase canonical form.

    'nba' -> 'NBA', 'march madness' -> 'NCAAB', etc.
    """
    cleaned = raw.strip().lower()
    if cleaned in _LEAGUE_ALIASES:
        return _LEAGUE_ALIASES[cleaned]
    return raw.strip().upper()
