"""
API Data Enrichment Service.

Integrates The Odds API and BallDontLie API to enhance historical game data
with betting lines and advanced statistics.

This is CRITICAL because ESPN data has NO betting lines (all None).
The Odds API provides the missing market odds needed for backtesting.
"""

import logging
from typing import Dict, List, Any, Optional

from src.odds_api_client import TheOddsAPIClient
from src.balldontlie_client import BallDontLieAPIClient

logger = logging.getLogger(__name__)


class APIDataEnrichment:
    """
    Enriches historical game data with betting lines and advanced stats.
    
    This is CRITICAL because ESPN data has NO betting lines.
    The Odds API provides the missing market odds needed for backtesting.
    """
    
    def __init__(
        self,
        odds_api_key: Optional[str] = None,
        balldontlie_api_key: Optional[str] = None
    ):
        """
        Initialize API enrichment service.
        
        Args:
            odds_api_key: The Odds API key (optional, will use env var)
            balldontlie_api_key: BallDontLie API key (optional, will use env var)
        """
        self.odds_client = TheOddsAPIClient(api_key=odds_api_key)
        self.bdl_client = BallDontLieAPIClient(api_key=balldontlie_api_key)
        
        logger.info("="*80)
        logger.info("API Data Enrichment Service Initialized")
        logger.info("="*80)
        
        if self.odds_client.api_key:
            logger.info("✓ The Odds API enabled - will fetch betting lines")
            logger.info("  This is CRITICAL for betting system validation!")
        else:
            logger.warning("✗ The Odds API not configured - betting lines will be missing")
            logger.warning("  Set THE_ODDS_API_KEY environment variable to enable")
        
        if self.bdl_client.api_key:
            logger.info("✓ BallDontLie API enabled - will fetch enhanced NBA stats")
        else:
            logger.warning("✗ BallDontLie API not configured - using ESPN data only")
            logger.warning("  Set BALLDONTLIE_API_KEY environment variable to enable")
        
        logger.info("="*80)
    
    def enrich_games(
        self,
        games: List[Dict[str, Any]],
        add_betting_lines: bool = True,
        add_player_stats: bool = False,
        show_progress: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Enrich a list of games with betting lines and stats.
        
        Args:
            games: List of game dictionaries from ESPN
            add_betting_lines: Whether to add odds from The Odds API
            add_player_stats: Whether to add player stats from BallDontLie
            show_progress: Whether to log progress
        
        Returns:
            Enriched game list
        """
        if not games:
            return games
        
        enriched_games = []
        odds_cache = {}  # Cache odds by date to minimize API calls
        
        total = len(games)
        
        if show_progress:
            logger.info(f"Enriching {total} games with betting lines and statistics...")
        
        for idx, game in enumerate(games):
            enriched = game.copy()
            
            # Add betting lines (CRITICAL for validation)
            if add_betting_lines and self.odds_client.api_key:
                enriched = self.odds_client.enrich_game_with_odds(enriched, odds_cache)
            
            # Add player stats for NBA games
            if add_player_stats and self.bdl_client.api_key and game.get("sport") == "NBA":
                enriched = self.bdl_client.enrich_game_with_stats(enriched)
            
            enriched_games.append(enriched)
            
            # Progress logging
            if show_progress and (idx + 1) % 50 == 0:
                logger.info(f"  Progress: {idx + 1}/{total} games enriched")
        
        # Log enrichment statistics
        games_with_odds = sum(
            1 for g in enriched_games 
            if (g.get("moneyline") or {}).get("home") is not None
        )
        
        games_with_spread = sum(
            1 for g in enriched_games 
            if (g.get("spread") or {}).get("line") is not None
        )
        
        games_with_total = sum(
            1 for g in enriched_games 
            if (g.get("total") or {}).get("line") is not None
        )
        
        logger.info("")
        logger.info("="*80)
        logger.info("Enrichment Summary")
        logger.info("="*80)
        logger.info(f"Total games: {len(enriched_games)}")
        logger.info(f"Games with moneyline odds: {games_with_odds}/{total} ({games_with_odds/total*100:.1f}%)")
        logger.info(f"Games with spread: {games_with_spread}/{total} ({games_with_spread/total*100:.1f}%)")
        logger.info(f"Games with totals: {games_with_total}/{total} ({games_with_total/total*100:.1f}%)")
        
        if games_with_odds == 0 and add_betting_lines:
            logger.warning("")
            logger.warning("⚠️  WARNING: No betting lines added!")
            logger.warning("⚠️  Betting system validation requires market odds!")
            logger.warning("⚠️  Check The Odds API key and data availability")
        elif games_with_odds > 0:
            logger.info("")
            logger.info("✓ Betting lines successfully added - ready for validation!")
        
        logger.info("="*80)
        
        return enriched_games
    
    def enrich_single_game(
        self,
        game: Dict[str, Any],
        add_betting_lines: bool = True,
        add_player_stats: bool = False
    ) -> Dict[str, Any]:
        """
        Enrich a single game with betting lines and stats.
        
        Args:
            game: Game dictionary from ESPN
            add_betting_lines: Whether to add odds
            add_player_stats: Whether to add player stats
        
        Returns:
            Enriched game dictionary
        """
        enriched = game.copy()
        
        if add_betting_lines and self.odds_client.api_key:
            enriched = self.odds_client.enrich_game_with_odds(enriched)
        
        if add_player_stats and self.bdl_client.api_key and game.get("sport") == "NBA":
            enriched = self.bdl_client.enrich_game_with_stats(enriched)
        
        return enriched
    
    def check_api_status(self) -> Dict[str, Any]:
        """
        Check status and usage of all API services.
        
        Returns:
            Dictionary with API status information
        """
        status = {
            "odds_api": {
                "enabled": self.odds_client.api_key is not None,
                "usage": None
            },
            "balldontlie_api": {
                "enabled": self.bdl_client.api_key is not None,
                "usage": None
            }
        }
        
        # Check The Odds API usage
        if self.odds_client.api_key:
            usage = self.odds_client.check_usage()
            if usage:
                status["odds_api"]["usage"] = usage
        
        return status
