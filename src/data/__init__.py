"""
OMEGA Data Layer

Data scraping, API integration, and resilience for sports betting data.
Uses FREE APIs and web scraping only.

Modules:
- providers: Protocol definitions and schemas for injected data sources
- odds_scraper: Odds data from The Odds API and fallback sources
- stats_scraper: Player/team stats from Basketball/Football Reference
- stats_ingestion: Agent-only network layer (ESPN, Ball Don't Lie, Perplexity)
- schedule_api: Game schedules from ESPN API
- free_sources: Catalog of free data sources with unified interface
- player_game_log: ESPN player game log retrieval
- last_known_good: File-based persistence for stale-but-real data fallback

Deprecated modules removed in Phase B:
- data_recovery, cache_service, nfl_stats, games_analysis (deleted)
- injury_api: resurrected as src/providers/injury.py adapter
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
    clear_all_cache as clear_all_stats_cache
)

from src.data.player_game_log import (
    get_player_game_log,
    get_cached_player_game_log,
    get_espn_player_id
)

from src.data.providers import (
    TeamContextInput,
    PlayerContextInput,
    OddsQuote,
    WeatherNewsSignal,
    GamesProvider,
    TeamContextProvider,
    PlayerContextProvider,
    OddsProvider,
    WeatherNewsProvider,
)

__all__ = [
    # Odds
    "get_upcoming_games",
    "get_current_odds",
    "get_player_props",
    "get_available_sports",
    "check_odds_api_status",
    # Stats scraping
    "get_player_stats",
    "get_team_stats",
    "get_season_averages",
    "search_players",
    # Schedule
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
    # Stats ingestion (agent-only)
    "TeamContext",
    "PlayerContext",
    "get_team_context",
    "get_player_context",
    "get_game_context",
    "clear_stats_cache",
    "clear_all_stats_cache",
    # Player game logs
    "get_player_game_log",
    "get_cached_player_game_log",
    "get_espn_player_id",
    # Provider protocols and schemas
    "TeamContextInput",
    "PlayerContextInput",
    "OddsQuote",
    "WeatherNewsSignal",
    "GamesProvider",
    "TeamContextProvider",
    "PlayerContextProvider",
    "OddsProvider",
    "WeatherNewsProvider",
]
