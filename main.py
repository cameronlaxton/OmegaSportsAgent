#!/usr/bin/env python3
"""
OmegaSports Headless Simulation Engine

A modular sports analytics and simulation engine designed for headless execution
by Perplexity Spaces/Agents. This is the main entry point for all simulation tasks.

Usage:
    python main.py --morning-bets          # Generate daily bet recommendations
    python main.py --analyze TEAM_A TEAM_B # Analyze specific matchup
    python main.py --simulate LEAGUE       # Run simulations for a league
    python main.py --audit                 # Run backtest audit
    python main.py --scrape URL            # Scrape a URL for data

Results are saved to logs/ and outputs/ directories as JSON/Markdown.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from typing import Optional, List

from omega.schema import GameData, BettingLine, PropBet, DailySlate, SimulationInput, BetRecommendation

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/omega_engine.log', mode='a')
    ]
)
logger = logging.getLogger("omega")

os.makedirs("logs", exist_ok=True)
os.makedirs("outputs", exist_ok=True)
os.makedirs("data/logs", exist_ok=True)
os.makedirs("data/outputs", exist_ok=True)


def save_output(data: dict, filename: str, format: str = "json") -> str:
    """Save output data to file and return the path."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    
    if format == "json":
        filepath = f"outputs/{filename}_{timestamp}.json"
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)
    elif format == "markdown":
        filepath = f"outputs/{filename}_{timestamp}.md"
        with open(filepath, "w") as f:
            f.write(data.get("markdown", str(data)))
    else:
        filepath = f"outputs/{filename}_{timestamp}.txt"
        with open(filepath, "w") as f:
            f.write(str(data))
    
    logger.info(f"Output saved to: {filepath}")
    return filepath


def run_morning_bets(leagues: Optional[List[str]] = None, iterations: int = 10000) -> dict:
    """
    Generate morning bet recommendations.
    
    Args:
        leagues: List of leagues to analyze (default: all supported)
        iterations: Number of simulation iterations
    
    Returns:
        Dict with qualified bets and metadata
    """
    logger.info("Starting morning bet generation...")
    
    try:
        from omega.workflows.morning_bets import run_morning_workflow
        
        result = run_morning_workflow(
            leagues=leagues,
            n_iter=iterations,
            sync_to_github=False
        )
        
        output_path = save_output(result, "morning_bets")
        result["output_file"] = output_path
        
        logger.info(f"Morning bets complete: {result.get('qualified_bets_count', 0)} qualified bets")
        return result
        
    except ImportError as e:
        logger.error(f"Module import error: {e}")
        return {"error": str(e), "status": "failed"}
    except Exception as e:
        logger.error(f"Morning bets failed: {e}")
        return {"error": str(e), "status": "failed"}


def run_analyze(team_a: str, team_b: str, league: str = "NBA") -> dict:
    """
    Analyze a specific matchup between two teams.
    
    Args:
        team_a: First team name
        team_b: Second team name  
        league: League identifier (NBA, NFL, MLB, etc.)
    
    Returns:
        Dict with analysis results
    """
    logger.info(f"Analyzing matchup: {team_a} vs {team_b} ({league})")
    
    try:
        from omega.simulation.simulation_engine import run_game_simulation
        from omega.data.stats_scraper import get_team_stats
        
        stats_a = get_team_stats(team_a, league) or {}
        stats_b = get_team_stats(team_b, league) or {}
        
        projection = {
            "off_rating": {
                team_a: stats_a.get("off_rating", 110.0),
                team_b: stats_b.get("off_rating", 108.0)
            },
            "league": league,
            "variance_scalar": 1.0
        }
        
        sim_results = run_game_simulation(projection, n_iter=10000, league=league)
        
        result = {
            "matchup": f"{team_a} vs {team_b}",
            "league": league,
            "team_a": {"name": team_a, "stats": stats_a},
            "team_b": {"name": team_b, "stats": stats_b},
            "simulation": sim_results,
            "analyzed_at": datetime.now().isoformat()
        }
        
        output_path = save_output(result, f"analysis_{team_a}_{team_b}".replace(" ", "_"))
        result["output_file"] = output_path
        
        return result
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        return {"error": str(e), "status": "failed"}


def run_simulate(league: str, iterations: int = 10000) -> dict:
    """
    Run simulations for all games in a league.
    
    Args:
        league: League identifier
        iterations: Number of simulation iterations
    
    Returns:
        Dict with simulation results for all games
    """
    logger.info(f"Running simulations for {league}...")
    
    try:
        from omega.data.schedule_api import get_todays_games
        from omega.simulation.simulation_engine import run_game_simulation
        from omega.data.stats_scraper import get_team_stats
        
        games = get_todays_games(league)
        
        if not games:
            return {
                "league": league,
                "message": "No games found for today",
                "games": [],
                "simulated_at": datetime.now().isoformat()
            }
        
        results = []
        for game in games:
            home = game.get("home_team", {})
            away = game.get("away_team", {})
            home_name = home.get("name", home) if isinstance(home, dict) else str(home)
            away_name = away.get("name", away) if isinstance(away, dict) else str(away)
            
            try:
                home_stats = get_team_stats(home_name, league) or {}
                away_stats = get_team_stats(away_name, league) or {}
                
                projection = {
                    "off_rating": {
                        home_name: home_stats.get("off_rating", 110.0),
                        away_name: away_stats.get("off_rating", 108.0)
                    },
                    "league": league,
                    "variance_scalar": 1.0
                }
                
                sim = run_game_simulation(projection, n_iter=iterations, league=league)
                results.append({
                    "matchup": f"{away_name} @ {home_name}",
                    "simulation": sim
                })
            except Exception as e:
                logger.warning(f"Failed to simulate {away_name} @ {home_name}: {e}")
        
        result = {
            "league": league,
            "games_simulated": len(results),
            "results": results,
            "simulated_at": datetime.now().isoformat()
        }
        
        output_path = save_output(result, f"simulation_{league}")
        result["output_file"] = output_path
        
        return result
        
    except Exception as e:
        logger.error(f"Simulation failed: {e}")
        return {"error": str(e), "status": "failed"}


def run_audit(start_date: Optional[str] = None, end_date: Optional[str] = None) -> dict:
    """
    Run backtest audit on historical bets.
    
    Args:
        start_date: Start date for audit (YYYY-MM-DD)
        end_date: End date for audit (YYYY-MM-DD)
    
    Returns:
        Dict with audit metrics
    """
    logger.info("Running backtest audit...")
    
    try:
        from omega.utilities.sandbox_persistence import OmegaCacheLogger
        
        cache_logger = OmegaCacheLogger()
        
        audit_result = cache_logger.run_backtest_audit(
            start_date=start_date,
            end_date=end_date
        )
        
        output_path = save_output(audit_result, "audit_report")
        audit_result["output_file"] = output_path
        
        return audit_result
        
    except Exception as e:
        logger.error(f"Audit failed: {e}")
        return {"error": str(e), "status": "failed"}


def run_scrape(url: str) -> dict:
    """
    Scrape a URL and return as Markdown.
    
    Args:
        url: URL to scrape
    
    Returns:
        Dict with markdown content and schema template
    """
    logger.info(f"Scraping URL: {url}")
    
    try:
        from scraper_engine import fetch_sports_markdown, parse_to_game_data
        
        result = fetch_sports_markdown(url)
        
        if result["success"]:
            game_template = parse_to_game_data(
                markdown=result.get("markdown", ""),
                source_url=url
            )
            result["schema_template"] = game_template
            result["schema_note"] = "Fill in the betting data fields to match omega.schema.GameData before simulation"
            
            output_path = save_output(result, "scrape_result", format="json")
            result["output_file"] = output_path
        
        return result
        
    except Exception as e:
        logger.error(f"Scrape failed: {e}")
        return {"error": str(e), "status": "failed"}


def main():
    """Main entry point for the OmegaSports simulation engine."""
    parser = argparse.ArgumentParser(
        description="OmegaSports Headless Simulation Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --morning-bets
  python main.py --morning-bets --leagues NBA NFL
  python main.py --analyze "Boston Celtics" "Indiana Pacers" --league NBA
  python main.py --simulate NBA --iterations 5000
  python main.py --audit --start-date 2025-01-01 --end-date 2025-01-15
  python main.py --scrape "https://www.espn.com/nba/schedule"
        """
    )
    
    parser.add_argument("--morning-bets", action="store_true",
                        help="Generate daily bet recommendations")
    parser.add_argument("--analyze", nargs=2, metavar=("TEAM_A", "TEAM_B"),
                        help="Analyze matchup between two teams")
    parser.add_argument("--simulate", metavar="LEAGUE",
                        help="Run simulations for a league")
    parser.add_argument("--audit", action="store_true",
                        help="Run backtest audit")
    parser.add_argument("--scrape", metavar="URL",
                        help="Scrape a URL for sports data")
    
    parser.add_argument("--leagues", nargs="+", default=None,
                        help="Leagues to analyze (for --morning-bets)")
    parser.add_argument("--league", default="NBA",
                        help="League for analysis (default: NBA)")
    parser.add_argument("--iterations", type=int, default=10000,
                        help="Simulation iterations (default: 10000)")
    parser.add_argument("--start-date", help="Start date for audit (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="End date for audit (YYYY-MM-DD)")
    parser.add_argument("--verbose", action="store_true",
                        help="Enable verbose output")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    print("=" * 60)
    print("OmegaSports Headless Simulation Engine")
    print(f"Started at: {datetime.now().isoformat()}")
    print("=" * 60)
    
    result = None
    
    if args.morning_bets:
        result = run_morning_bets(leagues=args.leagues, iterations=args.iterations)
        
    elif args.analyze:
        result = run_analyze(args.analyze[0], args.analyze[1], league=args.league)
        
    elif args.simulate:
        result = run_simulate(args.simulate, iterations=args.iterations)
        
    elif args.audit:
        result = run_audit(start_date=args.start_date, end_date=args.end_date)
        
    elif args.scrape:
        result = run_scrape(args.scrape)
        
    else:
        parser.print_help()
        print("\n[INFO] No command specified. Use one of the options above.")
        return
    
    print("\n" + "-" * 60)
    print("Result Summary:")
    print("-" * 60)
    
    if result:
        if result.get("error"):
            print(f"[ERROR] {result['error']}")
        else:
            print(json.dumps(result, indent=2, default=str)[:2000])
            if result.get("output_file"):
                print(f"\n[OUTPUT] Full results saved to: {result['output_file']}")
    
    print("=" * 60)


if __name__ == "__main__":
    main()
