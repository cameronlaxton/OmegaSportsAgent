"""
Direct API router — fast path to existing src/data/ modules.

Tries existing structured API modules first before falling back to web search.
Each module is called in a try/except so a single failure never blocks the pipeline.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from agent.models import GatherSlot, ProviderResult
from src.data.sources.source_config import DIRECT_API_CAPABILITIES

logger = logging.getLogger("omega.data.acquisition.direct_api")


def try_direct_api(slot: GatherSlot) -> Optional[ProviderResult]:
    """Try existing API modules as a fast path for a gather slot.

    Returns a ProviderResult if a matching module succeeds, else None.
    Failures are logged but never raised.
    """
    league_upper = slot.league.upper()

    # Find matching modules
    candidates = _get_candidates(slot.data_type, league_upper)
    if not candidates:
        return None

    for module_name in candidates:
        try:
            result = _call_module(module_name, slot)
            if result is not None:
                logger.debug(
                    "Direct API hit: slot=%s module=%s", slot.key, module_name
                )
                return result
        except Exception as exc:
            logger.debug(
                "Direct API failed: slot=%s module=%s error=%s",
                slot.key, module_name, exc,
            )

    return None


def _get_candidates(data_type: str, league: str) -> List[str]:
    """Get module names that can serve this data_type + league combination."""
    candidates = []
    for module_name, caps in DIRECT_API_CAPABILITIES.items():
        if data_type in caps["data_types"] and league in caps["leagues"]:
            candidates.append(module_name)
    return candidates


def _call_module(module_name: str, slot: GatherSlot) -> Optional[ProviderResult]:
    """Dispatch to the appropriate src/data/ module function.

    Returns ProviderResult on success, None on failure or empty data.
    """
    if module_name == "schedule_api":
        return _call_schedule_api(slot)
    elif module_name == "odds_scraper":
        return _call_odds_scraper(slot)
    elif module_name == "stats_scraper":
        return _call_stats_scraper(slot)
    elif module_name == "nba_stats_api":
        return _call_nba_stats_api(slot)
    elif module_name == "player_game_log":
        return _call_player_game_log(slot)
    elif module_name == "injury_api":
        return _call_injury_api(slot)
    else:
        logger.debug("Unknown direct API module: %s", module_name)
        return None


# ---------------------------------------------------------------------------
# Module-specific call wrappers
# ---------------------------------------------------------------------------

def _call_schedule_api(slot: GatherSlot) -> Optional[ProviderResult]:
    from src.data.schedule_api import get_todays_games

    games = get_todays_games(slot.league)
    if not games:
        return None

    # If slot entity is specified AND it's not a slate query (entity == league),
    # filter to matching games. For slate queries we want ALL games.
    is_slate_query = slot.entity and slot.entity.lower() == slot.league.lower()
    if slot.entity and not is_slate_query:
        entity_lower = slot.entity.lower()
        matching = [
            g for g in games
            if entity_lower in g.get("home_team", "").lower()
            or entity_lower in g.get("away_team", "").lower()
            or entity_lower in g.get("home", "").lower()
            or entity_lower in g.get("away", "").lower()
        ]
        if matching:
            games = matching

    return ProviderResult(
        data={"games": games},
        source="schedule_api",
        fetched_at=datetime.utcnow(),
        confidence=0.95,
    )


def _call_odds_scraper(slot: GatherSlot) -> Optional[ProviderResult]:
    from src.data.odds_scraper import get_upcoming_games

    games = get_upcoming_games(slot.league)
    if not games:
        return None

    # Filter to entity if specified
    if slot.entity:
        entity_lower = slot.entity.lower()
        matching = [
            g for g in games
            if entity_lower in str(g.get("home_team", "")).lower()
            or entity_lower in str(g.get("away_team", "")).lower()
        ]
        if matching:
            games = matching

    # Only return as filled if games actually have bookmaker odds data.
    # The ESPN fallback returns games with empty bookmakers arrays, which
    # is useless for odds analysis — let the web search pipeline handle it.
    has_odds = any(g.get("bookmakers") for g in games)
    if not has_odds:
        logger.debug("Odds scraper returned games but no bookmaker data — skipping")
        return None

    return ProviderResult(
        data={"odds": games} if len(games) > 1 else games[0] if games else {"odds": games},
        source="odds_api",
        fetched_at=datetime.utcnow(),
        confidence=0.95,
    )


def _call_stats_scraper(slot: GatherSlot) -> Optional[ProviderResult]:
    from src.data.stats_scraper import get_team_stats, get_player_stats

    if slot.data_type == "player_stat":
        data = get_player_stats(slot.entity, slot.league)
    else:
        data = get_team_stats(slot.entity, slot.league)

    if not data:
        return None

    return ProviderResult(
        data=data,
        source="stats_scraper",
        fetched_at=datetime.utcnow(),
        confidence=0.90,
    )


def _call_nba_stats_api(slot: GatherSlot) -> Optional[ProviderResult]:
    from src.data.nba_stats_api import get_team_advanced_stats

    data = get_team_advanced_stats(slot.entity)
    if not data:
        return None

    return ProviderResult(
        data=data,
        source="nba_stats_api",
        fetched_at=datetime.utcnow(),
        confidence=0.95,
    )


def _call_player_game_log(slot: GatherSlot) -> Optional[ProviderResult]:
    from src.data.player_game_log import get_player_game_log

    games = get_player_game_log(slot.entity, slot.league)
    if not games:
        return None

    return ProviderResult(
        data={"game_log": games},
        source="player_game_log",
        fetched_at=datetime.utcnow(),
        confidence=0.90,
    )


def _call_injury_api(slot: GatherSlot) -> Optional[ProviderResult]:
    from src.data.injury_api import get_injuries

    data = get_injuries(slot.league)
    if not data:
        return None

    # Filter to entity if specified
    if slot.entity:
        entity_lower = slot.entity.lower()
        # Injury data is usually keyed by team
        filtered: Dict[str, Any] = {}
        if isinstance(data, dict):
            for key, val in data.items():
                if entity_lower in str(key).lower() or entity_lower in str(val).lower():
                    filtered[key] = val
            if filtered:
                data = filtered

    return ProviderResult(
        data=data if isinstance(data, dict) else {"injuries": data},
        source="injury_api",
        fetched_at=datetime.utcnow(),
        confidence=0.80,
    )
