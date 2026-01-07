#!/usr/bin/env python3
"""
Daily Grading Workflow Example

Demonstrates how to use the Daily Grading Workflow to:
1. Fetch game results from ESPN
2. Grade pending bets against actual outcomes
3. Update cumulative logs and metrics

Usage:
    python examples/daily_grading_example.py
    python examples/daily_grading_example.py --date 2026-01-06
    python examples/daily_grading_example.py --date 2026-01-06 --save-report
"""

import os
import sys
import json
import argparse
from datetime import datetime, timezone, timedelta

# Add repo to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from omega.workflows.daily_grading import DailyGradingWorkflow, BetResult


def print_header(title: str):
    """Print formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_game_results(results: dict):
    """Display game results in readable format."""
    print_header("Game Results Fetched")
    
    games = results.get("games", {})
    print(f"\n  Total games: {len(games)}")
    
    # Show first few games
    for i, (game_id, game) in enumerate(list(games.items())[:5]):
        home = game.get("home_team", "?")
        away = game.get("away_team", "?")
        home_score = game.get("home_score", 0)
        away_score = game.get("away_score", 0)
        status = game.get("status", "?")
        
        print(f"\n    {i+1}. {away} @ {home}")
        print(f"       Score: {away_score} - {home_score}")
        print(f"       Status: {status}")
    
    if len(games) > 5:
        print(f"\n    ... and {len(games) - 5} more games")
    
    player_stats = results.get("player_stats", {})
    print(f"\n  Player stats collected: {len(player_stats)} players")


def print_pending_bets_summary(workflow: DailyGradingWorkflow):
    """Display pending bets before grading."""
    print_header("Pending Bets (Before Grading)")
    
    pending = [
        bet for bet in workflow.predictions_data
        if bet.get("status") == "pending"
    ]
    
    print(f"\n  Total pending bets: {len(pending)}")
    
    # Group by bet type
    by_type = {}
    for bet in pending:
        bet_type = bet.get("bet_type", "unknown")
        by_type[bet_type] = by_type.get(bet_type, 0) + 1
    
    print("\n  Breakdown by type:")
    for bet_type, count in sorted(by_type.items()):
        print(f"    - {bet_type}: {count}")
    
    # Show first few
    print("\n  Sample pending bets:")
    for i, bet in enumerate(pending[:3]):
        print(f"\n    {i+1}. {bet.get('pick')} ({bet.get('bet_type')})")
        print(f"       Odds: {bet.get('odds')}, Stake: ${bet.get('stake', 0):.2f}")
        print(f"       Edge: {bet.get('edge_pct', 0):.1f}%, Confidence: {bet.get('confidence', '?')}")
    
    if len(pending) > 3:
        print(f"\n    ... and {len(pending) - 3} more")


def print_grading_results(workflow: DailyGradingWorkflow):
    """Display grading results in detailed format."""
    print_header("Grading Results (After)")
    
    stats = workflow.daily_stats
    graded = workflow.graded_bets
    
    print(f"\n  Total graded: {len(graded)} bets")
    print(f"  Record: {stats['wins']}-{stats['losses']}-{stats['pushes']}")
    print(f"  Win rate: {stats['win_rate']:.1%}")
    print(f"  ROI: {stats['roi']:.2%}")
    
    print(f"\n  Financial Summary:")
    print(f"    Total stake:   ${stats['total_stake']:>10.2f}")
    print(f"    Total payout:  ${stats['total_payout']:>10.2f}")
    print(f"    Profit/Loss:   ${stats['total_profit_loss']:>10.2f}")
    
    # Show sample graded bets
    print(f"\n  Sample graded bets:")
    for i, bet in enumerate(graded[:3]):
        result = bet.get("result", "?")
        pick = bet.get("pick", "?")
        payout = bet.get("payout", 0)
        pl = bet.get("profit_loss", 0)
        
        symbol = "✓" if result == "Win" else "x" if result == "Loss" else "="
        print(f"\n    {i+1}. [{symbol}] {pick}")
        print(f"       Result: {result} | Payout: ${payout:.2f} | P&L: ${pl:+.2f}")
    
    if len(graded) > 3:
        print(f"\n    ... and {len(graded) - 3} more")


def print_logs_updated(workflow: DailyGradingWorkflow):
    """Display summary of log files updated."""
    print_header("Cumulative Logs Updated")
    
    print(f"\n  1. predictions.json")
    print(f"     - Status updated: pending → graded")
    print(f"     - Bets updated: {len(workflow.graded_bets)}")
    print(f"     - Location: {workflow.predictions_file}")
    
    print(f"\n  2. BetLog.csv")
    print(f"     - Rows appended: {len(workflow.graded_bets)}")
    print(f"     - Columns: 15 (date, league, pick, odds, result, etc.)")
    print(f"     - Location: {workflow.bet_log_file}")
    
    print(f"\n  3. cumulative_metrics_report.json")
    # Load and display cumulative stats
    try:
        with open(workflow.metrics_file, 'r') as f:
            metrics = json.load(f)
            cum = metrics.get("cumulative_summary", {})
            print(f"     - Daily reports: {cum.get('total_days_graded', 0)}")
            print(f"     - Cumulative record: {cum.get('total_wins', 0)}-{cum.get('total_losses', 0)}")
            print(f"     - Cumulative ROI: {cum.get('cumulative_roi', 0):.2%}")
            print(f"     - Total P&L: ${cum.get('total_profit_loss', 0):.2f}")
    except Exception as e:
        print(f"     - (Metrics file will be created on first run)")
    
    print(f"     - Location: {workflow.metrics_file}")


def print_workflow_summary(report: dict):
    """Display final workflow summary."""
    print_header("Workflow Summary")
    
    print(f"\n  Status: {report.get('workflow_status', 'UNKNOWN')}")
    print(f"  Duration: {report.get('duration_seconds', 0):.1f} seconds")
    print(f"  Date analyzed: {report.get('analysis_date', '?')}")
    print(f"  Bets graded: {report.get('bets_graded', 0)}")
    
    summary = report.get("summary", {})
    print(f"\n  Final Results:")
    print(f"    Record: {summary.get('win_loss_record', '0-0')}")
    print(f"    Stake: {summary.get('total_stake', '$0.00')}")
    print(f"    P&L: {summary.get('total_profit_loss', '$0.00')}")
    print(f"    ROI: {summary.get('roi', '0.00%')}")
    print(f"    Win Rate: {summary.get('win_rate', '0.00%')}")


def main():
    """Run complete daily grading workflow example."""
    parser = argparse.ArgumentParser(description="Daily Grading Workflow Example")
    parser.add_argument(
        "--date",
        help="Analysis date (YYYY-MM-DD), defaults to yesterday"
    )
    parser.add_argument(
        "--save-report",
        action="store_true",
        help="Save detailed report as JSON"
    )
    
    args = parser.parse_args()
    
    # Initialize workflow
    print("\n" + "=" * 80)
    print("  DAILY GRADING WORKFLOW EXAMPLE")
    print("=" * 80)
    
    analysis_date = args.date or (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    print(f"\n  Initializing workflow for {analysis_date}...")
    
    workflow = DailyGradingWorkflow(analysis_date=analysis_date)
    
    # Step 1: Fetch results
    print("\n  Executing Step 1: Fetch game results...")
    game_results = workflow.fetch_game_results()
    print_game_results(game_results)
    
    # Display pending bets
    print_pending_bets_summary(workflow)
    
    # Step 2: Grade bets
    print("\n  Executing Step 2: Grade pending bets...")
    graded = workflow.grade_pending_bets(game_results)
    print_grading_results(workflow)
    
    # Step 3: Update logs
    print("\n  Executing Step 3: Update cumulative logs...")
    workflow.update_predictions_json()
    workflow.update_bet_log_csv()
    workflow.update_cumulative_metrics()
    print_logs_updated(workflow)
    
    # Get final report
    report = workflow.get_grading_report()
    print_workflow_summary(report)
    
    # Optionally save report
    if args.save_report:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"outputs/grading_report_{timestamp}.json"
        os.makedirs("outputs", exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n  Report saved: {report_file}")
    
    print("\n" + "=" * 80)
    print("  WORKFLOW COMPLETE")
    print("=" * 80 + "\n")
    
    return report


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nWorkflow interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
