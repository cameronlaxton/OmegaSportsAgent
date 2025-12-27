"""
Scheduled Automation for OMEGA Sports Betting System

Handles:
1. Morning bet generation (6am ET)
2. Result updates (3am ET)
3. System health checks
"""

import os
import sys
import json
import requests
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

API_BASE_URL = os.environ.get("OMEGA_API_URL", "http://localhost:5000")

def get_api_key() -> Optional[str]:
    return os.environ.get("OMEGA_API_KEY")

def make_request(endpoint: str, method: str = "GET", data: Optional[Dict] = None) -> Dict[str, Any]:
    url = f"{API_BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    
    api_key = get_api_key()
    if api_key:
        headers["X-API-Key"] = api_key
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=300)
        else:
            response = requests.post(url, json=data, headers=headers, timeout=300)
        
        return {
            "success": response.status_code in [200, 201],
            "status_code": response.status_code,
            "data": response.json() if response.status_code == 200 else None,
            "error": None if response.status_code == 200 else response.text
        }
    except Exception as e:
        return {
            "success": False,
            "status_code": None,
            "data": None,
            "error": str(e)
        }


def run_morning_bets():
    """
    Run morning bet generation workflow.
    Fetches today's games, runs simulations, identifies qualified bets.
    """
    logger.info("Starting morning bet generation...")
    
    from omega.workflows.morning_bets import run_morning_workflow
    
    try:
        result = run_morning_workflow(
            leagues=["NBA", "NFL"],
            n_iter=10000,
            sync_to_github=True
        )
        
        logger.info(f"Morning workflow completed:")
        logger.info(f"  Games evaluated: {result.get('games_evaluated', 0)}")
        logger.info(f"  Qualified bets: {result.get('qualified_bets_count', 0)}")
        logger.info(f"  Duration: {result.get('duration_seconds', 0):.1f}s")
        
        return result
        
    except Exception as e:
        logger.error(f"Morning workflow failed: {e}")
        return {"success": False, "error": str(e)}


def run_result_updates():
    """
    Run result update workflow.
    Fetches completed games and updates bet results via API.
    """
    logger.info("Starting result update workflow...")
    
    from omega.utilities.sandbox_persistence import OmegaCacheLogger
    from omega.data.schedule_api import get_scoreboard
    
    try:
        cache_logger = OmegaCacheLogger()
        pending_bets = cache_logger.get_pending_bets()
        
        if not pending_bets:
            logger.info("No pending bets to update")
            return {"success": True, "updated": 0, "message": "No pending bets"}
        
        logger.info(f"Found {len(pending_bets)} pending bets to check")
        
        updates = []
        for bet in pending_bets:
            try:
                league = bet.get("league", "NBA")
                matchup = bet.get("matchup", "")
                
                scores = get_scoreboard(league)
                
                for game in scores:
                    home_team = game.get("home_team", "")
                    away_team = game.get("away_team", "")
                    
                    if matchup and (home_team in matchup or away_team in matchup):
                        if game.get("status") == "Final":
                            pick = bet.get("pick", "")
                            home_score = game.get("home_score", 0)
                            away_score = game.get("away_score", 0)
                            
                            if "ML" in pick:
                                team_picked = pick.replace(" ML", "").strip()
                                if team_picked in home_team:
                                    result = "Win" if home_score > away_score else "Loss"
                                elif team_picked in away_team:
                                    result = "Win" if away_score > home_score else "Loss"
                                else:
                                    result = "Pending"
                            else:
                                result = "Pending"
                            
                            if result != "Pending":
                                updates.append({
                                    "bet_id": bet.get("bet_id"),
                                    "result": result,
                                    "final_score": f"{home_team} {home_score}, {away_team} {away_score}"
                                })
                                break
            except Exception as e:
                logger.error(f"Error checking bet {bet.get('bet_id')}: {e}")
        
        if updates:
            logger.info(f"Updating {len(updates)} bet results...")
            response = make_request("/api/update-results", "POST", {
                "updates": updates,
                "sync_to_github": True
            })
            
            if response["success"]:
                logger.info(f"Results updated successfully")
            else:
                logger.error(f"Failed to update results: {response.get('error')}")
            
            return response
        else:
            logger.info("No completed games found for pending bets")
            return {"success": True, "updated": 0, "message": "No completed games"}
            
    except Exception as e:
        logger.error(f"Result update failed: {e}")
        return {"success": False, "error": str(e)}


def run_health_check():
    """
    Run system health check.
    Verifies API endpoints, data sources, and GitHub connectivity.
    """
    logger.info("Running health check...")
    
    checks = {
        "api_status": False,
        "github_status": False,
        "data_sources": {
            "espn": False,
            "odds_api": False
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    status = make_request("/api/status")
    checks["api_status"] = status["success"]
    
    github = make_request("/api/github-status")
    checks["github_status"] = github["success"] and github.get("data", {}).get("connected", False)
    
    try:
        from omega.data.schedule_api import get_todays_games
        games = get_todays_games("NBA")
        checks["data_sources"]["espn"] = True
    except:
        pass
    
    try:
        from omega.data.odds_scraper import check_api_status
        checks["data_sources"]["odds_api"] = check_api_status()
    except:
        pass
    
    all_good = checks["api_status"] and checks["github_status"]
    logger.info(f"Health check completed: {'PASS' if all_good else 'ISSUES DETECTED'}")
    
    return checks


def main():
    """
    Main entry point for scheduled tasks.
    Called by scheduler with task type argument.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="OMEGA Scheduled Tasks")
    parser.add_argument("task", choices=["morning", "results", "health"], 
                       help="Task to run")
    args = parser.parse_args()
    
    if args.task == "morning":
        result = run_morning_bets()
    elif args.task == "results":
        result = run_result_updates()
    elif args.task == "health":
        result = run_health_check()
    else:
        result = {"error": f"Unknown task: {args.task}"}
    
    print(json.dumps(result, indent=2, default=str))
    return result


if __name__ == "__main__":
    main()
