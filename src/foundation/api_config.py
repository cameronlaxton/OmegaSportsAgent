"""
API configuration — reads keys from environment variables.

APIs are optional and not required for core flows (simulation/calibration work with
pre-loaded data). Only simple env reads and stubs here; provider/API usage is
explicitly configured and owned by the agent layer.
"""

from __future__ import annotations

import os
from typing import Any, Dict


_BALLDONTLIE_URLS: Dict[str, str] = {
    "NBA": "https://api.balldontlie.io/v1",
    "DEFAULT": "https://api.balldontlie.io/v1",
}


def get_api_keys() -> Dict[str, str]:
    """Return all configured API keys from environment."""
    return {
        "ODDS_API_KEY": get_odds_api_key(),
        "BALLDONTLIE_API_KEY": get_balldontlie_key(),
    }


def get_odds_api_key() -> str:
    """Return the Odds API key from the ODDS_API_KEY env var."""
    return os.environ.get("ODDS_API_KEY", "")


def get_balldontlie_key() -> str:
    """Return the BallDontLie API key from the BALLDONTLIE_API_KEY env var."""
    return os.environ.get("BALLDONTLIE_API_KEY", "")


def get_balldontlie_url(league: str = "NBA") -> str:
    """Return the base URL for the BallDontLie API given a league."""
    return _BALLDONTLIE_URLS.get(league.upper(), _BALLDONTLIE_URLS["DEFAULT"])


def check_api_keys() -> Dict[str, Dict[str, Any]]:
    """Check which API keys are configured. Stub — returns presence flags."""
    keys = get_api_keys()
    return {k: {"configured": bool(v), "length": len(v)} for k, v in keys.items()}


def check_api_status() -> Dict[str, Any]:
    """Check API connectivity status. Stub — returns key availability only."""
    return {"keys": check_api_keys(), "status": "unchecked"}
