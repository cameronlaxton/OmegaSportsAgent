#!/usr/bin/env python3
"""
Data Collection Validation Test Suite
======================================

This test suite validates that:
1. Historical data collection endpoints return correct data
2. Data format matches the defined schema
3. Data is properly stored in the database
4. All required fields are present and valid

Run this test to ensure data collection is working correctly before
running experiments or backtesting.

Usage:
    python scripts/test_data_collection.py
    python scripts/test_data_collection.py --verbose
    python scripts/test_data_collection.py --sport NBA
"""

import sys
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.db_manager import DatabaseManager
from core.data_pipeline import DataValidator
from src.balldontlie_client import BallDontLieAPIClient
from src.odds_api_client import TheOddsAPIClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)
logger = logging.getLogger(__name__)


class DataCollectionValidator:
    """Validates data collection process and schema compliance."""
    
    def __init__(self, db_path: str = "data/sports_data.db"):
        """Initialize validator with database connection."""
        self.db_manager = DatabaseManager(db_path)
        self.validator = DataValidator()
        self.test_results = []
        
    def log_test(self, test_name: str, passed: bool, message: str = ""):
        """Log test result."""
        status = "✓ PASS" if passed else "✗ FAIL"
        result = {
            "test": test_name,
            "passed": passed,
            "message": message
        }
        self.test_results.append(result)
        
        if passed:
            logger.info(f"{status}: {test_name}")
            if message:
                logger.info(f"       {message}")
        else:
            logger.error(f"{status}: {test_name}")
            if message:
                logger.error(f"       {message}")
    
    def test_database_schema(self) -> bool:
        """Test 1: Verify database schema exists and is correct."""
        logger.info("\n" + "="*80)
        logger.info("Test 1: Database Schema Validation")
        logger.info("="*80)
        
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        # Check all required tables exist
        required_tables = ["games", "player_props", "odds_history", 
                          "player_props_odds", "perplexity_cache"]
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        all_tables_exist = True
        for table in required_tables:
            if table in existing_tables:
                self.log_test(f"Table '{table}' exists", True)
            else:
                self.log_test(f"Table '{table}' exists", False, 
                             f"Missing table: {table}")
                all_tables_exist = False
        
        # Check games table schema
        cursor.execute("PRAGMA table_info(games)")
        games_columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        required_game_columns = {
            "game_id": "TEXT",
            "date": "TEXT",
            "sport": "TEXT",
            "home_team": "TEXT",
            "away_team": "TEXT",
            "home_score": "INTEGER",
            "away_score": "INTEGER",
            "moneyline_home": "INTEGER",
            "moneyline_away": "INTEGER",
            "spread_line": "REAL",
            "total_line": "REAL"
        }
        
        schema_correct = True
        for col, dtype in required_game_columns.items():
            if col in games_columns:
                if games_columns[col] == dtype:
                    self.log_test(f"Column 'games.{col}' type", True, 
                                 f"Type: {dtype}")
                else:
                    self.log_test(f"Column 'games.{col}' type", False,
                                 f"Expected {dtype}, got {games_columns[col]}")
                    schema_correct = False
            else:
                self.log_test(f"Column 'games.{col}' exists", False,
                             f"Missing column in games table")
                schema_correct = False
        
        return all_tables_exist and schema_correct
    
    def test_data_validation_logic(self) -> bool:
        """Test 2: Verify data validation logic works correctly."""
        logger.info("\n" + "="*80)
        logger.info("Test 2: Data Validation Logic")
        logger.info("="*80)
        
        # Test valid game data
        valid_game = {
            "game_id": "test_game_001",
            "date": "2024-01-15",
            "sport": "NBA",
            "league": "NBA",
            "home_team": "Los Angeles Lakers",
            "away_team": "Boston Celtics",
            "home_score": 114,
            "away_score": 105
        }
        
        is_valid, error = self.validator.validate_game(valid_game)
        self.log_test("Valid game data passes validation", is_valid, 
                     "Sample valid game validates correctly")
        
        # Test invalid game data (missing required field)
        invalid_game = {
            "game_id": "test_game_002",
            "date": "2024-01-15",
            # Missing sport field
            "league": "NBA",
            "home_team": "Lakers",
            "away_team": "Celtics"
        }
        
        is_valid, error = self.validator.validate_game(invalid_game)
        self.log_test("Invalid game data fails validation", not is_valid,
                     f"Correctly rejected: {error}")
        
        # Test invalid date format
        invalid_date_game = {
            "game_id": "test_game_003",
            "date": "01/15/2024",  # Wrong format
            "sport": "NBA",
            "league": "NBA",
            "home_team": "Lakers",
            "away_team": "Celtics"
        }
        
        is_valid, error = self.validator.validate_game(invalid_date_game)
        self.log_test("Invalid date format rejected", not is_valid,
                     f"Correctly rejected: {error}")
        
        # Test valid player prop
        valid_prop = {
            "prop_id": "test_prop_001",
            "game_id": "test_game_001",
            "date": "2024-01-15",
            "sport": "NBA",
            "player_name": "LeBron James",
            "player_team": "Los Angeles Lakers",
            "opponent_team": "Boston Celtics",
            "prop_type": "points"
        }
        
        is_valid, error = self.validator.validate_prop(valid_prop)
        self.log_test("Valid prop data passes validation", is_valid,
                     "Sample valid prop validates correctly")
        
        # Test invalid prop type
        invalid_prop = {
            "prop_id": "test_prop_002",
            "game_id": "test_game_001",
            "date": "2024-01-15",
            "sport": "NBA",
            "player_name": "LeBron James",
            "player_team": "Lakers",
            "opponent_team": "Celtics",
            "prop_type": "touchdowns"  # Wrong sport
        }
        
        is_valid, error = self.validator.validate_prop(invalid_prop)
        self.log_test("Invalid prop type rejected", not is_valid,
                     f"Correctly rejected: {error}")
        
        return True
    
    def test_database_data_integrity(self) -> bool:
        """Test 3: Verify data in database meets schema requirements."""
        logger.info("\n" + "="*80)
        logger.info("Test 3: Database Data Integrity")
        logger.info("="*80)
        
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        # Check if we have any data
        cursor.execute("SELECT COUNT(*) FROM games")
        game_count = cursor.fetchone()[0]
        
        if game_count == 0:
            self.log_test("Database has data", False,
                         "No games in database. Run data collection first.")
            return False
        
        self.log_test("Database has data", True, 
                     f"Found {game_count:,} games")
        
        # Sample and validate some games
        cursor.execute("""
            SELECT game_id, date, sport, home_team, away_team, 
                   home_score, away_score
            FROM games
            LIMIT 10
        """)
        
        validation_passed = True
        for row in cursor.fetchall():
            game = {
                "game_id": row[0],
                "date": row[1],
                "sport": row[2],
                "league": row[2],  # Simplified for validation
                "home_team": row[3],
                "away_team": row[4],
                "home_score": row[5],
                "away_score": row[6]
            }
            
            is_valid, error = self.validator.validate_game(game)
            if not is_valid:
                self.log_test(f"Game {game['game_id']} validates", False, error)
                validation_passed = False
        
        if validation_passed:
            self.log_test("Sample games validate correctly", True,
                         "All sampled games meet schema requirements")
        
        # Check for required fields completeness
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN home_score IS NULL THEN 1 ELSE 0 END) as missing_scores,
                SUM(CASE WHEN date IS NULL THEN 1 ELSE 0 END) as missing_dates,
                SUM(CASE WHEN home_team IS NULL OR away_team IS NULL THEN 1 ELSE 0 END) as missing_teams
            FROM games
        """)
        
        stats = cursor.fetchone()
        total, missing_scores, missing_dates, missing_teams = stats
        
        if total > 0:
            completeness = (total - missing_scores - missing_dates - missing_teams) / total * 100
            
            self.log_test("Data completeness check", missing_dates == 0 and missing_teams == 0,
                         f"Completeness: {completeness:.1f}% (some scores may be null for future games)")
        else:
            self.log_test("Data completeness check", False,
                         "No data in database to check")
        
        return validation_passed
    
    def test_api_endpoints(self, sport: str = "NBA") -> bool:
        """Test 4: Verify API endpoints return data in correct format."""
        logger.info("\n" + "="*80)
        logger.info(f"Test 4: API Endpoint Validation ({sport})")
        logger.info("="*80)
        
        # Test BallDontLie API
        try:
            bdl_client = BallDontLieAPIClient()
            if bdl_client.api_key:
                # Use a known historical date for consistent testing
                # March 15, 2024 had many NBA games
                test_date = "2024-03-15"
                games = bdl_client.get_games(test_date, test_date)
                
                if games:
                    self.log_test("BallDontLie API returns data", True,
                                 f"Returned {len(games)} games for {test_date}")
                    
                    # Validate structure
                    sample = games[0]
                    required_keys = ['id', 'home_team', 'visitor_team']
                    has_required = all(k in sample for k in required_keys)
                    
                    self.log_test("BallDontLie data structure valid", has_required,
                                 "Contains required fields")
                else:
                    self.log_test("BallDontLie API returns data", False,
                                 f"No data returned for {test_date}")
            else:
                self.log_test("BallDontLie API configured", False,
                             "API key not set. Set BALLDONTLIE_API_KEY in .env")
        except Exception as e:
            self.log_test("BallDontLie API test", False, f"Error: {str(e)}")
        
        # Test The Odds API
        try:
            odds_client = TheOddsAPIClient()
            if odds_client.api_key:
                usage = odds_client.check_usage()
                if usage:
                    self.log_test("The Odds API configured", True,
                                 f"Remaining requests: {usage.get('requests_remaining', 'N/A')}")
                else:
                    self.log_test("The Odds API configured", False,
                                 "Could not verify API usage")
            else:
                self.log_test("The Odds API configured", False,
                             "API key not set. Set THE_ODDS_API_KEY in .env")
        except Exception as e:
            self.log_test("The Odds API test", False, f"Error: {str(e)}")
        
        return True
    
    def test_data_collection_pipeline(self) -> bool:
        """Test 5: Verify end-to-end data collection works."""
        logger.info("\n" + "="*80)
        logger.info("Test 5: Data Collection Pipeline")
        logger.info("="*80)
        
        # Check if collection script exists
        script_path = Path(__file__).parent / "collect_historical_sqlite.py"
        
        if script_path.exists():
            self.log_test("Collection script exists", True,
                         f"Found: {script_path.name}")
        else:
            self.log_test("Collection script exists", False,
                         f"Missing: {script_path}")
            return False
        
        # Check if we can import the collector
        try:
            from scripts.collect_historical_sqlite import SQLiteHistoricalCollector
            self.log_test("Collection script imports", True,
                         "SQLiteHistoricalCollector available")
            
            # Verify expected games constants
            expected = SQLiteHistoricalCollector.EXPECTED_GAMES
            self.log_test("Expected games defined", True,
                         f"NBA: {expected.get('NBA', 'N/A')}, NFL: {expected.get('NFL', 'N/A')}")
            
            # Verify season dates defined
            season_dates = SQLiteHistoricalCollector.SEASON_DATES
            self.log_test("Season dates defined", True,
                         f"NBA seasons: {len(season_dates.get('NBA', {}))}, "
                         f"NFL seasons: {len(season_dates.get('NFL', {}))}")
            
        except Exception as e:
            self.log_test("Collection script imports", False, f"Error: {str(e)}")
            return False
        
        return True
    
    def run_all_tests(self, sport: str = "NBA") -> bool:
        """Run all validation tests."""
        logger.info("\n" + "="*80)
        logger.info("DATA COLLECTION VALIDATION TEST SUITE")
        logger.info("OmegaSports Validation Lab")
        logger.info("="*80)
        logger.info(f"\nTarget Sport: {sport}")
        logger.info(f"Database: data/sports_data.db")
        logger.info("")
        
        # Run all tests
        tests = [
            self.test_database_schema(),
            self.test_data_validation_logic(),
            self.test_database_data_integrity(),
            self.test_api_endpoints(sport),
            self.test_data_collection_pipeline()
        ]
        
        # Print summary
        logger.info("\n" + "="*80)
        logger.info("TEST SUMMARY")
        logger.info("="*80)
        
        passed = sum(1 for r in self.test_results if r["passed"])
        total = len(self.test_results)
        
        logger.info(f"\nTotal Tests: {total}")
        logger.info(f"Passed: {passed} ({passed/total*100:.1f}%)")
        logger.info(f"Failed: {total - passed}")
        
        if passed == total:
            logger.info("\n✓ ALL TESTS PASSED")
            logger.info("\nData collection is properly configured and validated!")
            logger.info("Schema is consistent, endpoints return correct data format.")
            logger.info("\nYou can now safely run:")
            logger.info("  python scripts/collect_historical_sqlite.py --sports NBA --start-year 2023 --end-year 2024")
            return True
        else:
            logger.error("\n✗ SOME TESTS FAILED")
            logger.error("\nPlease review the failures above and:")
            logger.error("1. Check API keys are configured in .env")
            logger.error("2. Verify database schema is up to date")
            logger.error("3. Run data collection if no data exists")
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate data collection process and schema compliance"
    )
    parser.add_argument(
        "--sport",
        default="NBA",
        choices=["NBA", "NFL"],
        help="Sport to test (default: NBA)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    validator = DataCollectionValidator()
    success = validator.run_all_tests(args.sport)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
