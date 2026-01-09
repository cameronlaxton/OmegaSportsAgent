#!/usr/bin/env python
"""
Script to load and validate historical game data.

This script provides a command-line interface for loading historical game data
into the validation lab's database. The user is responsible for ensuring data
sources are available.

Usage:
    # Load data for specific sports and years
    python scripts/load_and_validate_games.py --sports NBA NFL --start-year 2020 --end-year 2024
    
    # Check existing data
    python scripts/load_and_validate_games.py --check-only
    
    # Validate minimum game counts
    python scripts/load_and_validate_games.py --check-only --min-count 1000
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.data_pipeline import DataPipeline
from utils.config import config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def check_existing_data(pipeline: DataPipeline, sports: list, start_year: int, end_year: int, min_count: int = 0):
    """
    Check existing data in the database.
    
    Args:
        pipeline: DataPipeline instance
        sports: List of sports to check
        start_year: Start year
        end_year: End year
        min_count: Minimum required game count
    """
    logger.info("\n" + "="*80)
    logger.info("Checking Existing Data")
    logger.info("="*80)
    
    results = {}
    for sport in sports:
        try:
            count = pipeline.get_game_count(sport, start_year, end_year)
            results[sport] = count
            
            status = "✓" if count >= min_count else "✗"
            logger.info(f"{status} {sport}: {count} games (requirement: >={min_count})")
        except Exception as e:
            logger.error(f"Error checking {sport}: {e}")
            results[sport] = 0
    
    # Summary
    total_games = sum(results.values())
    passing = sum(1 for count in results.values() if count >= min_count)
    
    logger.info("\n" + "-"*80)
    logger.info(f"Total games: {total_games}")
    logger.info(f"Sports meeting requirement: {passing}/{len(sports)}")
    
    if passing < len(sports):
        logger.warning(f"\n⚠ Warning: {len(sports) - passing} sport(s) below minimum game count")
        return False
    else:
        logger.info("\n✓ All sports meet minimum game count requirement")
        return True


def load_data(pipeline: DataPipeline, sports: list, start_year: int, end_year: int, force_refresh: bool = False):
    """
    Load historical game data.
    
    Args:
        pipeline: DataPipeline instance
        sports: List of sports to load
        start_year: Start year
        end_year: End year
        force_refresh: Whether to force refresh cached data
    """
    logger.info("\n" + "="*80)
    logger.info("Loading Historical Game Data")
    logger.info("="*80)
    logger.info(f"Sports: {', '.join(sports)}")
    logger.info(f"Years: {start_year}-{end_year}")
    logger.info(f"Force refresh: {force_refresh}")
    
    results = {}
    for sport in sports:
        logger.info(f"\n--- Loading {sport} ---")
        try:
            games = pipeline.fetch_and_cache_games(
                sport=sport,
                start_year=start_year,
                end_year=end_year,
                force_refresh=force_refresh
            )
            
            results[sport] = len(games)
            logger.info(f"✓ {sport}: Loaded {len(games)} games")
        except Exception as e:
            logger.error(f"✗ {sport}: Failed to load - {e}")
            results[sport] = 0
    
    # Summary
    total_games = sum(results.values())
    successful = sum(1 for count in results.values() if count > 0)
    
    logger.info("\n" + "="*80)
    logger.info("Load Summary")
    logger.info("="*80)
    
    for sport, count in results.items():
        status = "✓" if count > 0 else "✗"
        logger.info(f"{status} {sport}: {count} games")
    
    logger.info(f"\nTotal: {total_games} games across {successful}/{len(sports)} sports")
    
    return successful == len(sports)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Load and validate historical game data for OmegaSports Validation Lab"
    )
    
    parser.add_argument(
        "--sports",
        nargs="+",
        default=["NBA", "NFL", "NCAAB", "NCAAF"],
        help="Sports to load data for (default: NBA NFL NCAAB NCAAF)"
    )
    
    parser.add_argument(
        "--start-year",
        type=int,
        default=2020,
        help="Start year for data loading (default: 2020)"
    )
    
    parser.add_argument(
        "--end-year",
        type=int,
        default=2024,
        help="End year for data loading (default: 2024)"
    )
    
    parser.add_argument(
        "--min-count",
        type=int,
        default=0,
        help="Minimum required game count per sport (default: 0)"
    )
    
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check existing data, don't load new data"
    )
    
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Force refresh cached data"
    )
    
    args = parser.parse_args()
    
    logger.info("\n" + "="*80)
    logger.info("OmegaSports Validation Lab - Data Loading Tool")
    logger.info("="*80)
    
    # Initialize pipeline
    pipeline = DataPipeline(
        cache_dir=config.cache_path,
        data_dir=config.historical_data_path
    )
    
    # Check or load data
    if args.check_only:
        success = check_existing_data(
            pipeline,
            args.sports,
            args.start_year,
            args.end_year,
            args.min_count
        )
    else:
        # First check existing
        logger.info("Checking existing data before loading...")
        check_existing_data(
            pipeline,
            args.sports,
            args.start_year,
            args.end_year,
            args.min_count
        )
        
        # Then load
        success = load_data(
            pipeline,
            args.sports,
            args.start_year,
            args.end_year,
            args.force_refresh
        )
    
    logger.info("\n" + "="*80)
    if success:
        logger.info("✓ Data loading completed successfully")
        return 0
    else:
        logger.error("✗ Data loading encountered errors")
        return 1


if __name__ == "__main__":
    sys.exit(main())
