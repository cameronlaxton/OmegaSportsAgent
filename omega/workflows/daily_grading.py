"""
Daily Grading & Metrics Update Workflow

OBJECTIVE:
Grade all "pending" bets from the prior day, update the master bet logs, 
and append the day's performance to the cumulative metrics history.

WORKFLOW STEPS:
1. Fetch Game Results
   - Scrape final scores and box scores for yesterday's games
   - Retrieve player stats for prop grading

2. Grade Pending Bets
   - Load data/logs/predictions.json
   - Compare predictions vs actuals for all "pending" items
   - Determine Win/Loss/Push and calculate Profit/Loss

3. Update Cumulative Logs
   - Update Master JSON (data/logs/predictions.json)
   - Update Master CSV (data/exports/BetLog.csv)
   - Update Metrics History (data/logs/cumulative_metrics_report.json)

OUTPUTS:
- Updated predictions.json with graded bets
- Updated BetLog.csv with daily entries
- Updated cumulative_metrics_report.json with daily metrics
- Grading report showing all updates and summary stats
"""

import os
import sys
import json
import csv
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Tuple, Optional
from enum import Enum

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BetResult(Enum):
    """Possible betting outcomes."""
    WIN = "Win"
    LOSS = "Loss"
    PUSH = "Push"
    PENDING = "Pending"
    VOID = "Void"
    PENDING_PLAYER_PROP = "Pending (Player Prop)"


class DailyGradingWorkflow:
    """Complete daily grading workflow for pending bets."""
    
    def __init__(self, analysis_date: Optional[str] = None):
        """
        Initialize grading workflow.
        
        Args:
            analysis_date: Date to grade (YYYY-MM-DD). Defaults to yesterday.
        """
        self.analysis_date = analysis_date or (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Paths
        self.predictions_file = "data/logs/predictions.json"
        self.bet_log_file = "data/exports/BetLog.csv"
        self.metrics_file = "data/logs/cumulative_metrics_report.json"
        
        # Ensure directories exist
        os.makedirs("data/logs", exist_ok=True)
        os.makedirs("data/exports", exist_ok=True)
        
        # Initialize data
        self.predictions_data = self._load_predictions()
        self.graded_bets = []
        self.daily_stats = {
            "date": self.analysis_date,
            "total_bets_graded": 0,
            "wins": 0,
            "losses": 0,
            "pushes": 0,
            "voids": 0,
            "total_stake": 0.0,
            "total_payout": 0.0,
            "total_profit_loss": 0.0,
            "win_rate": 0.0,
            "roi": 0.0,
            "avg_edge": 0.0
        }
        
        logger.info(f"Initialized daily grading workflow for {self.analysis_date}")
    
    # ===================== STEP 1: FETCH GAME RESULTS =====================
    
    def fetch_game_results(self) -> Dict[str, Any]:
        """
        Fetch final scores and box scores for yesterday's games.
        
        Returns:
            Dict with game results and player stats keyed by game ID
        """
        logger.info(f"Step 1: Fetching game results for {self.analysis_date}...")
        
        results = {
            "date": self.analysis_date,
            "games": {},
            "player_stats": {}
        }
        
        try:
            from omega.data.schedule_api import get_scoreboard
            from omega.data.stats_scraper import get_player_stats_date
            
            # Get games for each league
            for league in ["NBA", "NFL"]:
                try:
                    games = get_scoreboard(league, date=self.analysis_date)
                    
                    for game in games:
                        game_id = f"{league}_{game.get('game_id', 'unknown')}"
                        results["games"][game_id] = {
                            "league": league,
                            "game_id": game.get("game_id"),
                            "home_team": game.get("home_team"),
                            "away_team": game.get("away_team"),
                            "home_score": game.get("home_score"),
                            "away_score": game.get("away_score"),
                            "status": game.get("status"),  # e.g. "Final"
                            "game_date": game.get("date"),
                            "box_score": game.get("box_score", {})
                        }
                    
                    logger.info(f"  ✓ Fetched {len(games)} {league} games")
                    
                except Exception as e:
                    logger.warning(f"  ⚠ Failed to fetch {league} games: {e}")
            
            # Get player stats for the date
            try:
                player_stats = get_player_stats_date(self.analysis_date)
                results["player_stats"] = player_stats
                logger.info(f"  ✓ Fetched player stats ({len(player_stats)} players)")
            except Exception as e:
                logger.warning(f"  ⚠ Failed to fetch player stats: {e}")
            
            logger.info(f"Step 1 complete: {len(results['games'])} games, {len(results['player_stats'])} players")
            return results
            
        except Exception as e:
            logger.error(f"Failed to fetch game results: {e}")
            return results
    
    # ===================== STEP 2: GRADE PENDING BETS =====================
    
    def grade_pending_bets(self, game_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Compare predictions vs actuals and determine Win/Loss/Push.
        
        Args:
            game_results: Game results from Step 1
        
        Returns:
            List of graded bets with results
        """
        logger.info("Step 2: Grading pending bets...")
        
        graded_bets = []
        pending_bets = [
            bet for bet in self.predictions_data
            if bet.get("status") == "pending"
        ]
        
        logger.info(f"  Found {len(pending_bets)} pending bets to grade")
        
        for bet in pending_bets:
            try:
                graded_bet = self._grade_single_bet(bet, game_results)
                
                if graded_bet.get("status") != "pending":
                    graded_bets.append(graded_bet)
                    
                    # Update daily stats
                    if graded_bet.get("result") == BetResult.WIN.value:
                        self.daily_stats["wins"] += 1
                    elif graded_bet.get("result") == BetResult.LOSS.value:
                        self.daily_stats["losses"] += 1
                    elif graded_bet.get("result") == BetResult.PUSH.value:
                        self.daily_stats["pushes"] += 1
                    elif graded_bet.get("result") == BetResult.VOID.value:
                        self.daily_stats["voids"] += 1
                    
                    self.daily_stats["total_stake"] += graded_bet.get("stake", 0)
                    self.daily_stats["total_payout"] += graded_bet.get("payout", 0)
                    self.daily_stats["total_profit_loss"] += graded_bet.get("profit_loss", 0)
                    self.daily_stats["total_bets_graded"] += 1
                    
            except Exception as e:
                logger.error(f"Failed to grade bet {bet.get('bet_id')}: {e}")
        
        # Calculate summary stats
        if self.daily_stats["total_bets_graded"] > 0:
            graded_count = (self.daily_stats["wins"] + self.daily_stats["losses"] 
                           + self.daily_stats["pushes"])
            if graded_count > 0:
                self.daily_stats["win_rate"] = (
                    self.daily_stats["wins"] / graded_count
                )
            
            if self.daily_stats["total_stake"] > 0:
                self.daily_stats["roi"] = (
                    self.daily_stats["total_profit_loss"] / self.daily_stats["total_stake"]
                )
        
        logger.info(f"Step 2 complete: Graded {len(graded_bets)} bets")
        logger.info(f"  Wins: {self.daily_stats['wins']}, "
                   f"Losses: {self.daily_stats['losses']}, "
                   f"Pushes: {self.daily_stats['pushes']}")
        logger.info(f"  Profit/Loss: ${self.daily_stats['total_profit_loss']:.2f}")
        
        self.graded_bets = graded_bets
        return graded_bets
    
    def _grade_single_bet(self, bet: Dict[str, Any], game_results: Dict[str, Any]
                         ) -> Dict[str, Any]:
        """
        Grade a single bet based on game results.
        
        Args:
            bet: Prediction data with status "pending"
            game_results: Game results from Step 1
        
        Returns:
            Updated bet dict with result, actual_value, payout, profit_loss
        """
        graded_bet = bet.copy()
        graded_bet["graded_date"] = datetime.now(timezone.utc).isoformat()
        
        bet_type = bet.get("bet_type", "").lower()
        league = bet.get("league", "").upper()
        matchup = bet.get("matchup", "")
        
        # Find matching game
        matching_game = None
        for game_id, game in game_results.get("games", {}).items():
            if game["league"] == league:
                home = game.get("home_team", "")
                away = game.get("away_team", "")
                if (home in matchup or away in matchup):
                    matching_game = game
                    break
        
        # If game not final, keep as pending
        if not matching_game or matching_game.get("status") != "Final":
            graded_bet["status"] = "pending"
            return graded_bet
        
        # Grade based on bet type
        result = BetResult.PENDING
        actual_value = None
        
        if "moneyline" in bet_type or "ml" in bet_type:
            result, actual_value = self._grade_moneyline(bet, matching_game)
        
        elif "spread" in bet_type:
            result, actual_value = self._grade_spread(bet, matching_game)
        
        elif "total" in bet_type or "over" in bet_type or "under" in bet_type:
            result, actual_value = self._grade_total(bet, matching_game)
        
        elif "prop" in bet_type or "player" in bet_type:
            result, actual_value = self._grade_player_prop(
                bet, matching_game, game_results
            )
        
        # Calculate payout and profit/loss
        graded_bet["result"] = result.value
        graded_bet["actual_value"] = actual_value
        graded_bet["status"] = "graded"
        
        stake = graded_bet.get("stake", 0)
        odds = graded_bet.get("odds", -110)
        
        payout = 0.0
        profit_loss = 0.0
        
        if result == BetResult.WIN:
            if odds > 0:
                payout = stake + stake * (odds / 100)
            else:
                payout = stake + stake * (100 / abs(odds))
            profit_loss = payout - stake
        elif result == BetResult.PUSH:
            payout = stake
            profit_loss = 0.0
        elif result == BetResult.VOID:
            payout = stake
            profit_loss = 0.0
        else:  # LOSS
            payout = 0.0
            profit_loss = -stake
        
        graded_bet["payout"] = payout
        graded_bet["profit_loss"] = profit_loss
        
        return graded_bet
    
    def _grade_moneyline(self, bet: Dict[str, Any], game: Dict[str, Any]
                        ) -> Tuple[BetResult, float]:
        """Grade moneyline bet."""
        pick = bet.get("pick", "").strip()
        home_team = game.get("home_team", "")
        away_team = game.get("away_team", "")
        home_score = game.get("home_score", 0)
        away_score = game.get("away_score", 0)
        
        # Determine which team was picked
        picked_home = home_team in pick
        picked_away = away_team in pick
        
        if not (picked_home or picked_away):
            return BetResult.VOID, None
        
        home_won = home_score > away_score
        
        if picked_home:
            if home_won:
                return BetResult.WIN, 1.0
            else:
                return BetResult.LOSS, 0.0
        else:  # picked_away
            if not home_won:
                return BetResult.WIN, 1.0
            else:
                return BetResult.LOSS, 0.0
    
    def _grade_spread(self, bet: Dict[str, Any], game: Dict[str, Any]
                     ) -> Tuple[BetResult, float]:
        """Grade spread bet."""
        pick = bet.get("pick", "").strip()
        line = bet.get("line", 0)
        
        home_team = game.get("home_team", "")
        away_team = game.get("away_team", "")
        home_score = game.get("home_score", 0)
        away_score = game.get("away_score", 0)
        
        # Determine which side was picked
        picked_home = home_team in pick
        picked_away = away_team in pick
        
        if not (picked_home or picked_away):
            return BetResult.VOID, None
        
        point_diff = home_score - away_score
        
        if picked_home:
            # Home team spread (positive line is home underdog, negative is home favorite)
            spread_diff = point_diff - line
        else:
            # Away team spread
            spread_diff = away_score - home_score - line
        
        if spread_diff > 0:
            return BetResult.WIN, 1.0
        elif spread_diff == 0:
            return BetResult.PUSH, 0.5
        else:
            return BetResult.LOSS, 0.0
    
    def _grade_total(self, bet: Dict[str, Any], game: Dict[str, Any]
                    ) -> Tuple[BetResult, float]:
        """Grade total (over/under) bet."""
        pick = bet.get("pick", "").lower()
        line = bet.get("line", 0)
        
        home_score = game.get("home_score", 0)
        away_score = game.get("away_score", 0)
        total = home_score + away_score
        
        is_over = "over" in pick
        is_under = "under" in pick
        
        if not (is_over or is_under):
            return BetResult.VOID, None
        
        if is_over:
            if total > line:
                return BetResult.WIN, 1.0
            elif total == line:
                return BetResult.PUSH, 0.5
            else:
                return BetResult.LOSS, 0.0
        else:  # is_under
            if total < line:
                return BetResult.WIN, 1.0
            elif total == line:
                return BetResult.PUSH, 0.5
            else:
                return BetResult.LOSS, 0.0
    
    def _grade_player_prop(self, bet: Dict[str, Any], game: Dict[str, Any],
                          game_results: Dict[str, Any]) -> Tuple[BetResult, float]:
        """
        Grade player prop bet.
        
        Requires player stats from Step 1.
        """
        pick = bet.get("pick", "").strip()
        line = bet.get("line", 0)
        
        # Extract player name and prop type from pick
        # Format: "Player Name PROP TYPE OVER/UNDER LINE"
        try:
            parts = pick.split()
            player_name = " ".join(parts[:-3])  # All but last 3 words
            prop_type = parts[-3]  # e.g. "Points", "Rebounds", "Assists"
            is_over = "over" in parts[-2].lower()
            
            # Find player stats
            player_stats = game_results.get("player_stats", {}).get(player_name, {})
            
            if not player_stats:
                logger.warning(f"No stats found for {player_name}")
                return BetResult.PENDING_PLAYER_PROP, None
            
            # Get actual value from stats
            stat_key = prop_type.lower()
            actual_value = float(player_stats.get(stat_key, 0))
            
            if is_over:
                if actual_value > line:
                    return BetResult.WIN, 1.0
                elif actual_value == line:
                    return BetResult.PUSH, 0.5
                else:
                    return BetResult.LOSS, 0.0
            else:  # under
                if actual_value < line:
                    return BetResult.WIN, 1.0
                elif actual_value == line:
                    return BetResult.PUSH, 0.5
                else:
                    return BetResult.LOSS, 0.0
        
        except Exception as e:
            logger.warning(f"Could not grade player prop: {e}")
            return BetResult.PENDING_PLAYER_PROP, None
    
    # ===================== STEP 3: UPDATE CUMULATIVE LOGS =====================
    
    def update_predictions_json(self) -> bool:
        """Update Master JSON (data/logs/predictions.json)."""
        logger.info("Step 3a: Updating predictions.json...")
        
        try:
            # Update predictions that were graded
            for graded_bet in self.graded_bets:
                bet_id = graded_bet.get("bet_id")
                
                for i, pred in enumerate(self.predictions_data):
                    if pred.get("bet_id") == bet_id:
                        self.predictions_data[i] = graded_bet
                        break
            
            # Save updated predictions
            os.makedirs(os.path.dirname(self.predictions_file), exist_ok=True)
            with open(self.predictions_file, 'w') as f:
                json.dump(self.predictions_data, f, indent=2, default=str)
            
            logger.info(f"  ✓ Updated {len(self.graded_bets)} predictions in {self.predictions_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update predictions.json: {e}")
            return False
    
    def update_bet_log_csv(self) -> bool:
        """Update Master CSV (data/exports/BetLog.csv)."""
        logger.info("Step 3b: Updating BetLog.csv...")
        
        try:
            # Prepare CSV rows from graded bets
            fieldnames = [
                "bet_id", "date", "league", "matchup", "bet_type", "pick",
                "line", "odds", "stake", "edge_pct", "confidence",
                "result", "actual_value", "payout", "profit_loss", "graded_date"
            ]
            
            # Check if file exists to determine write mode
            file_exists = os.path.exists(self.bet_log_file)
            
            with open(self.bet_log_file, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                
                # Write header only if file is new
                if not file_exists:
                    writer.writeheader()
                
                # Write graded bets
                for bet in self.graded_bets:
                    row = {field: bet.get(field, "") for field in fieldnames}
                    writer.writerow(row)
            
            logger.info(f"  ✓ Appended {len(self.graded_bets)} rows to {self.bet_log_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update BetLog.csv: {e}")
            return False
    
    def update_cumulative_metrics(self) -> bool:
        """Update Metrics History (data/logs/cumulative_metrics_report.json)."""
        logger.info("Step 3c: Updating cumulative_metrics_report.json...")
        
        try:
            # Load existing metrics
            metrics_data = {"daily_reports": []}
            
            if os.path.exists(self.metrics_file):
                with open(self.metrics_file, 'r') as f:
                    metrics_data = json.load(f)
            
            # Add today's metrics
            metrics_data["daily_reports"].append(self.daily_stats)
            
            # Calculate cumulative stats
            total_bets = sum(r["total_bets_graded"] for r in metrics_data["daily_reports"])
            total_wins = sum(r["wins"] for r in metrics_data["daily_reports"])
            total_losses = sum(r["losses"] for r in metrics_data["daily_reports"])
            total_stake = sum(r["total_stake"] for r in metrics_data["daily_reports"])
            total_profit_loss = sum(r["total_profit_loss"] for r in metrics_data["daily_reports"])
            
            metrics_data["cumulative_summary"] = {
                "report_generated": datetime.now(timezone.utc).isoformat(),
                "total_days_graded": len(metrics_data["daily_reports"]),
                "total_bets_graded": total_bets,
                "total_wins": total_wins,
                "total_losses": total_losses,
                "cumulative_win_rate": total_wins / total_bets if total_bets > 0 else 0,
                "total_stake": total_stake,
                "total_profit_loss": total_profit_loss,
                "cumulative_roi": total_profit_loss / total_stake if total_stake > 0 else 0
            }
            
            # Save metrics
            os.makedirs(os.path.dirname(self.metrics_file), exist_ok=True)
            with open(self.metrics_file, 'w') as f:
                json.dump(metrics_data, f, indent=2, default=str)
            
            logger.info(f"  ✓ Updated {self.metrics_file}")
            logger.info(f"  Cumulative: {total_wins}-{total_losses} record, "
                       f"${total_profit_loss:.2f} profit/loss")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update cumulative_metrics_report.json: {e}")
            return False
    
    # ===================== UTILITY METHODS =====================
    
    def _load_predictions(self) -> List[Dict[str, Any]]:
        """Load predictions from JSON file."""
        if os.path.exists(self.predictions_file):
            try:
                with open(self.predictions_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load predictions file: {e}")
                return []
        return []
    
    def get_grading_report(self) -> Dict[str, Any]:
        """Generate comprehensive grading report."""
        return {
            "workflow_date": datetime.now(timezone.utc).isoformat(),
            "analysis_date": self.analysis_date,
            "bets_graded": len(self.graded_bets),
            "daily_stats": self.daily_stats,
            "graded_bets": self.graded_bets,
            "summary": {
                "win_loss_record": f"{self.daily_stats['wins']}-{self.daily_stats['losses']}",
                "total_stake": f"${self.daily_stats['total_stake']:.2f}",
                "total_profit_loss": f"${self.daily_stats['total_profit_loss']:.2f}",
                "roi": f"{self.daily_stats['roi']:.2%}",
                "win_rate": f"{self.daily_stats['win_rate']:.2%}"
            }
        }
    
    def run_complete_workflow(self) -> Dict[str, Any]:
        """
        Execute the complete daily grading workflow.
        
        Returns:
            Complete workflow report with all results
        """
        logger.info("=" * 80)
        logger.info("DAILY GRADING & METRICS UPDATE WORKFLOW")
        logger.info("=" * 80)
        
        start_time = datetime.now()
        
        try:
            # Step 1: Fetch game results
            game_results = self.fetch_game_results()
            
            # Step 2: Grade pending bets
            self.grade_pending_bets(game_results)
            
            # Step 3: Update logs
            step_3a = self.update_predictions_json()
            step_3b = self.update_bet_log_csv()
            step_3c = self.update_cumulative_metrics()
            
            duration = (datetime.now() - start_time).total_seconds()
            
            report = self.get_grading_report()
            report["workflow_status"] = "COMPLETE" if (step_3a and step_3b and step_3c) else "PARTIAL"
            report["duration_seconds"] = duration
            
            logger.info("=" * 80)
            logger.info("WORKFLOW COMPLETE")
            logger.info(f"  Status: {report['workflow_status']}")
            logger.info(f"  Bets Graded: {len(self.graded_bets)}")
            logger.info(f"  Duration: {duration:.1f}s")
            logger.info("=" * 80)
            
            return report
            
        except Exception as e:
            logger.error(f"Workflow failed: {e}")
            return {
                "workflow_status": "FAILED",
                "error": str(e),
                "duration_seconds": (datetime.now() - start_time).total_seconds()
            }


def main():
    """CLI entry point for daily grading workflow."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Daily Bet Grading Workflow")
    parser.add_argument("--date", help="Analysis date (YYYY-MM-DD), defaults to yesterday")
    parser.add_argument("--output", help="Output report file (JSON)")
    
    args = parser.parse_args()
    
    # Run workflow
    workflow = DailyGradingWorkflow(analysis_date=args.date)
    report = workflow.run_complete_workflow()
    
    # Save report
    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        logger.info(f"Report saved to {args.output}")
    
    # Print summary
    print("\n" + "=" * 80)
    print("GRADING WORKFLOW SUMMARY")
    print("=" * 80)
    print(json.dumps(report.get("summary", {}), indent=2))
    print("=" * 80)
    
    return report


if __name__ == "__main__":
    main()
