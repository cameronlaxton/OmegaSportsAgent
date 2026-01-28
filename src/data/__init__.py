"""
OMEGA Data Layer

Data scraping and API integration for sports betting data.
Uses FREE APIs and web scraping only.

Modules:
- odds_scraper: Get odds data from The Odds API and fallback sources
- stats_scraper: Scrape player/team stats from Basketball/Football Reference
- schedule_api: Get game schedules from ESPN API
- free_sources: Catalog of free data sources with unified interface
"""

from src.data.odds_scraper import (
    get_upcoming_games,
    get_current_odds,
    get_player_props,
    get_available_sports,
    check_api_status as check_odds_api_status
)

from src.data.stats_scraper import (
    get_player_stats,
    get_team_stats,
    get_season_averages,
    search_players
)

from src.data.schedule_api import (
    get_todays_games,
    get_game_details,
    get_upcoming_games as get_upcoming_schedule,
    get_standings,
    get_team_schedule,
    check_api_status as check_espn_api_status
)

from src.data.free_sources import (
    DataCategory,
    DataSource,
    FREE_DATA_SOURCES,
    list_sources,
    get_source_info,
    UnifiedDataClient,
    create_client,
    get_supported_leagues,
    get_league_sources
)

from src.data.stats_ingestion import (
    TeamContext,
    PlayerContext,
    get_team_context,
    get_player_context,
    get_game_context,
    clear_cache as clear_stats_cache,
    clear_all_cache as clear_all_stats_cache,
    # Async functions (aiohttp-based)
    async_get_team_context,
    async_get_player_context,
    fetch_slate_context,
    fetch_slate_context_sync,
    AIOHTTP_AVAILABLE,
)

from src.data.player_game_log import (
    get_player_game_log,
    get_cached_player_game_log,
    get_espn_player_id
)

from src.data.data_recovery import (
    DataRecoveryService,
    get_recovery_service
)

__all__ = [
    # Odds scraper
    "get_upcoming_games",
    "get_current_odds",
    "get_player_props",
    "get_available_sports",
    "check_odds_api_status",
    # Stats scraper
    "get_player_stats",
    "get_team_stats",
    "get_season_averages",
    "search_players",
    # Schedule API
    "get_todays_games",
    "get_game_details",
    "get_upcoming_schedule",
    "get_standings",
    "get_team_schedule",
    "check_espn_api_status",
    # Free sources
    "DataCategory",
    "DataSource",
    "FREE_DATA_SOURCES",
    "list_sources",
    "get_source_info",
    "UnifiedDataClient",
    "create_client",
    "get_supported_leagues",
    "get_league_sources",
    # Stats ingestion (sync)
    "TeamContext",
    "PlayerContext",
    "get_team_context",
    "get_player_context",
    "get_game_context",
    "clear_stats_cache",
    "clear_all_stats_cache",
    # Stats ingestion (async)
    "async_get_team_context",
    "async_get_player_context",
    "fetch_slate_context",
    "fetch_slate_context_sync",
    "AIOHTTP_AVAILABLE",
    # Player game log
    "get_player_game_log",
    "get_cached_player_game_log",
    "get_espn_player_id",
    # Data recovery
    "DataRecoveryService",
    "get_recovery_service",
]
