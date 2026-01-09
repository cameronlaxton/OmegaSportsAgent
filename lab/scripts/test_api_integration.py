#!/usr/bin/env python
"""
Test script to verify API integration and betting lines enrichment.

This tests:
1. The Odds API connection and data fetch
2. BallDontLie API connection
3. Game enrichment with betting lines
4. Integration with data pipeline
"""

import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.odds_api_client import TheOddsAPIClient
from src.balldontlie_client import BallDontLieAPIClient
from src.api_enrichment import APIDataEnrichment
from src.espn_historical_scraper import ESPNHistoricalScraper

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def test_odds_api():
    """Test The Odds API connection."""
    logger.info("\n" + "="*80)
    logger.info("Testing The Odds API")
    logger.info("="*80)
    
    client = TheOddsAPIClient()
    
    if not client.api_key:
        logger.error("✗ The Odds API key not configured")
        return False
    
    # Check usage
    usage = client.check_usage()
    if usage:
        logger.info(f"✓ API connected - Remaining requests: {usage.get('requests_remaining')}")
    
    # Test fetching odds for a recent date
    logger.info("\nTesting odds fetch for NBA games on 2024-03-15...")
    odds = client.get_historical_odds("NBA", "2024-03-15")
    
    if odds:
        logger.info(f"✓ Fetched odds for {len(odds)} games")
        if odds:
            sample = odds[0]
            logger.info(f"\nSample odds:")
            logger.info(f"  Game: {sample['away_team']} @ {sample['home_team']}")
            logger.info(f"  Moneyline: {sample['moneyline']}")
            logger.info(f"  Spread: {sample['spread']}")
            logger.info(f"  Total: {sample['total']}")
            logger.info(f"  Bookmakers: {sample.get('num_bookmakers', 'N/A')}")
        return True
    else:
        logger.warning("✗ No odds data returned")
        return False


def test_balldontlie_api():
    """Test BallDontLie API connection."""
    logger.info("\n" + "="*80)
    logger.info("Testing BallDontLie API")
    logger.info("="*80)
    
    client = BallDontLieAPIClient()
    
    if not client.api_key:
        logger.error("✗ BallDontLie API key not configured")
        return False
    
    # Test fetching games
    logger.info("\nTesting game fetch for 2024-03-15...")
    games = client.get_games("2024-03-15", "2024-03-15")
    
    if games:
        logger.info(f"✓ Fetched {len(games)} NBA games")
        if games:
            sample = games[0]
            logger.info(f"\nSample game:")
            logger.info(f"  ID: {sample.get('id')}")
            logger.info(f"  Teams: {sample.get('visitor_team', {}).get('full_name')} @ {sample.get('home_team', {}).get('full_name')}")
            logger.info(f"  Score: {sample.get('visitor_team_score')} - {sample.get('home_team_score')}")
        return True
    else:
        logger.warning("✗ No games returned")
        return False


def test_enrichment():
    """Test game enrichment with betting lines."""
    logger.info("\n" + "="*80)
    logger.info("Testing Game Enrichment")
    logger.info("="*80)
    
    # Create sample games from ESPN
    espn_scraper = ESPNHistoricalScraper()
    logger.info("\nFetching sample NBA games from ESPN (2024-03-15 to 2024-03-17)...")
    games = espn_scraper.fetch_nba_games("2024-03-15", "2024-03-17")
    
    if not games:
        logger.error("✗ No games fetched from ESPN")
        return False
    
    logger.info(f"✓ Fetched {len(games)} games from ESPN")
    
    # Check if any have betting lines already
    games_with_odds_before = sum(1 for g in games if (g.get("moneyline") or {}).get("home") is not None)
    logger.info(f"  Games with odds before enrichment: {games_with_odds_before}/{len(games)}")
    
    # Enrich with betting lines
    enrichment = APIDataEnrichment()
    logger.info("\nEnriching games with betting lines from The Odds API...")
    enriched_games = enrichment.enrich_games(games, add_betting_lines=True)
    
    # Check results
    games_with_odds_after = sum(1 for g in enriched_games if (g.get("moneyline") or {}).get("home") is not None)
    logger.info(f"\n✓ Enrichment complete")
    logger.info(f"  Games with odds after enrichment: {games_with_odds_after}/{len(enriched_games)}")
    
    if games_with_odds_after > games_with_odds_before:
        logger.info(f"  ✓ Successfully added odds to {games_with_odds_after - games_with_odds_before} games")
        
        # Show sample enriched game
        for game in enriched_games:
            if (game.get("moneyline") or {}).get("home") is not None:
                logger.info(f"\nSample enriched game:")
                logger.info(f"  Matchup: {game['away_team']} @ {game['home_team']}")
                logger.info(f"  Score: {game['away_score']} - {game['home_score']}")
                logger.info(f"  Moneyline: {game['moneyline']}")
                logger.info(f"  Spread: {game['spread']}")
                logger.info(f"  Total: {game['total']}")
                break
        
        return True
    else:
        logger.warning("  ✗ No additional odds added")
        return False


def main():
    """Run all tests."""
    logger.info("\n" + "="*80)
    logger.info("API Integration Test Suite")
    logger.info("OmegaSports Validation Lab - Betting Lines Enrichment")
    logger.info("="*80)
    
    results = {
        "The Odds API": test_odds_api(),
        "BallDontLie API": test_balldontlie_api(),
        "Game Enrichment": test_enrichment()
    }
    
    logger.info("\n" + "="*80)
    logger.info("Test Results Summary")
    logger.info("="*80)
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"{status}: {test_name}")
    
    all_passed = all(results.values())
    
    if all_passed:
        logger.info("\n✓ All tests passed! API integration is working correctly.")
        logger.info("\n🎯 CRITICAL: Betting lines are now available for proper validation!")
        logger.info("   The Omega model can now be properly backtested with real market odds.")
        return 0
    else:
        logger.warning("\n✗ Some tests failed. Check API keys and network connectivity.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
