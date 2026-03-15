"""
Search planner — converts GatherSlots into targeted web search queries.

Generates 1-3 queries per slot, optimized for finding structured sports data.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List

from agent.models import GatherSlot

logger = logging.getLogger("omega.data.orchestration.search_planner")


def plan_searches(slot: GatherSlot) -> List[str]:
    """Generate targeted search queries for a gather slot.

    Args:
        slot: The gather slot that needs data.

    Returns:
        List of 1-3 search query strings.
    """
    entity = slot.entity
    league = slot.league.upper()
    data_type = slot.data_type
    current_year = datetime.now().year
    season = f"{current_year - 1}-{str(current_year)[2:]}"

    queries: List[str] = []

    if data_type == "team_stat":
        queries.append(f"{entity} {league} team stats {season} season")
        queries.append(f"{entity} offensive defensive rating {season}")

    elif data_type == "player_stat":
        queries.append(f"{entity} {league} player stats {season} season averages")
        queries.append(f"{entity} stats per game {current_year}")

    elif data_type == "player_game_log":
        queries.append(f"{entity} {league} game log last 10 games {current_year}")
        queries.append(f"{entity} recent game stats box scores")

    elif data_type == "odds":
        queries.append(f"{entity} {league} odds today betting lines")
        queries.append(f"{entity} moneyline spread total odds")

    elif data_type == "schedule":
        queries.append(f"{entity} {league} schedule today games")
        queries.append(f"{entity} next game {current_year}")

    elif data_type == "injury":
        queries.append(f"{entity} {league} injury report today")
        queries.append(f"{entity} injured players status {current_year}")

    else:
        # Generic fallback
        queries.append(f"{entity} {league} {data_type} {current_year}")

    logger.debug("Planned %d searches for slot %s: %s", len(queries), slot.key, queries)
    return queries
