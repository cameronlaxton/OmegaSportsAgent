"""
Web/scrape provider stubs.

These are intentionally lightweight so LLM agents can plug in their own
search/scrape pipelines (e.g., ESPN, Rotowire, odds sites) and normalize
results for the AnalystEngine.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from src.data.providers import TeamContextInput, OddsQuote, WeatherNewsSignal


def fetch_team_context_web(team: str, league: str) -> Optional[TeamContextInput]:
    """
    Stub for web-derived team context.

    Replace with an implementation that:
    - Scrapes box scores/advanced stats (pace, off/def ratings, injury impacts).
    - Normalizes keys to match TeamContextInput.
    """
    # Placeholder: return None to allow graceful fallback.
    return None


def fetch_odds_web(game: Dict[str, Any], league: str) -> Optional[Dict[str, Any]]:
    """
    Stub for web-derived odds (current or historical).

    Return a dict compatible with AnalystEngine odds expectations:
    {
        "moneyline_home": ...,
        "moneyline_away": ...,
        "spread_home": ...,
        "spread": ...,
        "over_under": ...,
        "book": "...",
        "updated_at": "...",
    }
    """
    return None


def fetch_weather_news_web(game: Dict[str, Any], league: str) -> Optional[WeatherNewsSignal]:
    """
    Stub for web-derived weather/news signals.

    Example sources: stadium weather APIs, beat writers, injury updates.
    """
    return None

