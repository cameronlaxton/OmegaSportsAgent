"""
API Configuration Module

Centralized API key management for OmegaSports Engine.
Provides default API keys with environment variable override capability.

API Keys:
- BALL DONT LIE API: NBA and NFL player statistics and data
  - NBA: https://api.balldontlie.io/v1
  - NFL: https://nfl.balldontlie.io/
- THE ODDS API: Sports betting odds and lines

Usage:
    from omega.foundation.api_config import get_api_keys, get_balldontlie_url
    
    keys = get_api_keys()
    balldontlie_key = keys["BALLDONTLIE_API_KEY"]
    odds_key = keys["ODDS_API_KEY"]
    
    # Get league-specific URL
    nba_url = get_balldontlie_url("NBA")
    nfl_url = get_balldontlie_url("NFL")
"""

from __future__ import annotations
import os
from typing import Dict

# Default API Keys
# These keys are provided for the OmegaSports calibration system
# Environment variables will override these defaults if set
DEFAULT_API_KEYS = {
    "BALLDONTLIE_API_KEY": "d2e5f371-e817-4cac-8506-56c9df9d98b4",
    "ODDS_API_KEY": "f6e098cb773a5bc2972a55ac85bb01ef"
}

# Ball Don't Lie API URLs by league
BALLDONTLIE_API_URLS = {
    "NBA": "https://api.balldontlie.io/v1",
    "NFL": "https://nfl.balldontlie.io",
    "NCAAB": "https://api.balldontlie.io/v1",  # Uses NBA endpoint
}


def get_api_keys() -> Dict[str, str]:
    """
    Get API keys with environment variable override.
    
    Returns environment variable if set, otherwise returns default key.
    This allows for:
    - Default keys for calibration/development
    - Production override via environment variables
    - Easy key rotation without code changes
    
    Returns:
        Dict with API keys:
            - BALLDONTLIE_API_KEY: Ball Don't Lie API key for NBA/NFL stats
            - ODDS_API_KEY: The Odds API key for betting lines
    """
    return {
        "BALLDONTLIE_API_KEY": os.environ.get(
            "BALLDONTLIE_API_KEY",
            DEFAULT_API_KEYS["BALLDONTLIE_API_KEY"]
        ),
        "ODDS_API_KEY": os.environ.get(
            "ODDS_API_KEY",
            DEFAULT_API_KEYS["ODDS_API_KEY"]
        )
    }


def get_balldontlie_key() -> str:
    """
    Get Ball Don't Lie API key.
    
    Returns:
        API key string (from environment or default)
    """
    return os.environ.get(
        "BALLDONTLIE_API_KEY",
        DEFAULT_API_KEYS["BALLDONTLIE_API_KEY"]
    )


def get_balldontlie_url(league: str) -> str:
    """
    Get Ball Don't Lie API base URL for a specific league.
    
    Args:
        league: League code (NBA, NFL, NCAAB, etc.)
    
    Returns:
        Base URL for the Ball Don't Lie API for that league
    """
    league_upper = league.upper()
    return BALLDONTLIE_API_URLS.get(league_upper, BALLDONTLIE_API_URLS["NBA"])


def get_odds_api_key() -> str:
    """
    Get The Odds API key.
    
    Returns:
        API key string (from environment or default)
    """
    return os.environ.get(
        "ODDS_API_KEY",
        DEFAULT_API_KEYS["ODDS_API_KEY"]
    )


def set_api_key(key_name: str, key_value: str) -> None:
    """
    Set an API key in the environment (runtime override).
    
    Args:
        key_name: Name of the API key (BALLDONTLIE_API_KEY or ODDS_API_KEY)
        key_value: The API key value
    """
    if key_name not in DEFAULT_API_KEYS:
        raise ValueError(f"Unknown API key: {key_name}. Must be one of {list(DEFAULT_API_KEYS.keys())}")
    os.environ[key_name] = key_value


def check_api_keys() -> Dict[str, Dict[str, any]]:
    """
    Check API key status and sources.
    
    Returns:
        Dict with key information:
            - key_name: {
                "value": key value (masked),
                "source": "environment" or "default",
                "configured": True/False
            }
    """
    keys = get_api_keys()
    status = {}
    
    for key_name, key_value in keys.items():
        is_env = key_name in os.environ
        status[key_name] = {
            "value": f"{key_value[:8]}...{key_value[-4:]}" if key_value else None,
            "source": "environment" if is_env else "default",
            "configured": bool(key_value)
        }
    
    return status
