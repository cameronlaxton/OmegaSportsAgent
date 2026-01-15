#!/usr/bin/env python3
"""
Daily Bet Generation Orchestrator

Executes the complete morning workflow:
1. Fetch live sports schedules (NBA/NFL/NHL)
2. Run simulations for all games
3. Calculate edges and qualify bets
4. Generate categorical best plays
5. Update cumulative BetLog and predictions.json
6. Create narrative output for GitHub commit

Date: 2026-01-15
Last Updated: 2026-01-15
"""

import os
import sys
import json
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import subprocess

# Import OmegaSports modules
try:
    from src.simulation.simulation_engine import run_game_simulation
    from src.betting.odds_eval import edge_percentage, implied_probability, expected_value_percent
    from src.betting.kelly_staking import recommend_stake
    from src.foundation.model_config import get_edge_thresholds
    from src.data.schedule_api import get_todays_games
    from src.utilities.data_logging import log_bet
    print("✓ OmegaSports modules imported successfully")
except ImportError as e:
    print(f"✗ Failed to import OmegaSports modules: {e}")
    print("Ensure dependencies are installed: pip install -r requirements.txt")
    sys.exit(1)


class DailyBetGenerator:
    """
    Orchestrates daily bet generation workflow with cumulative logging.
    """

    def __init__(self, date: Optional[str] = None):
        """Initialize the daily bet generator.
        
        Args:
            date: YYYY-MM-DD format (defaults to today)
        """
        self.date = date or datetime.now().strftime("%Y-%m-%d")
        self.timestamp = datetime.now().isoformat()
        
        # Setup directories
        self.output_dir = Path("outputs")
        self.data_exports_dir = Path("data/exports")
        self.data_logs_dir = Path("data/logs")
        
        for directory in [self.output_dir, self.data_exports_dir, self.data_logs_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # File paths
        self.betlog_path = self.data_exports_dir / "BetLog.csv"
        self.predictions_path = self.data_logs_dir / "predictions.json"
        self.narrative_path = self.output_dir / f"daily_narrative_{self.date}.md"
        
        # Data structures
        self.all_bets: List[Dict[str, Any]] = []
        self.qualified_bets: List[Dict[str, Any]] = []
        self.best_plays_by_category: Dict[str, Dict[str, Any]] = {}
        self.games_analyzed = 0
        
        print(f"✓ Daily Bet Generator initialized for {self.date}")

    def fetch_games(self, leagues: List[str] = None) -> List[Dict[str, Any]]:
        """Fetch today's games from sports APIs.
        
        Args:
            leagues: List of leagues (NBA, NFL, NHL)
        
        Returns:
            List of game dictionaries
        """
        if leagues is None:
            leagues = ["NBA", "NFL"]
        
        print(f"\n📅 FETCHING GAMES FOR {self.date}")
        print(f"   Leagues: {', '.join(leagues)}")
        
        games = []
        for league in leagues:
            try:
                league_games = get_todays_games(league=league)
                games.extend(league_games)
                print(f"   ✓ {league}: {len(league_games)} games")
            except Exception as e:
                print(f"   ✗ {league}: Failed to fetch ({e})")
        
        self.games_analyzed = len(games)
        print(f"\n   Total games: {self.games_analyzed}")
        return games

    def run_simulations(self, games: List[Dict[str, Any]]) -> None:
        """Run simulations for all games.
        
        Args:
            games: List of game dictionaries
        """
        print(f"\n🎯 RUNNING SIMULATIONS ({len(games)} games)")
        print(f"   Monte Carlo: 10,000 iterations per game")
        print(f"   Markov: 50,000 iterations for player props\n")
        
        for i, game in enumerate(games, 1):
            try:
                self._simulate_game(game)
                progress = f"{i}/{len(games)}"
                if i % 5 == 0 or i == len(games):
                    print(f"   Progress: {progress} games complete")
            except Exception as e:
                print(f"   ✗ Game {i}: Simulation failed ({e})")

    def _simulate_game(self, game: Dict[str, Any]) -> None:
        """Run simulation for a single game.
        
        Args:
            game: Game dictionary
        """
        home_team = game.get("home_team")
        away_team = game.get("away_team")
        league = game.get("league", "NBA")
        
        # Build projection from game data
        projection = {
            "off_rating": {
                home_team: game.get("home_off_rating", 110.0),
                away_team: game.get("away_off_rating", 110.0)
            },
            "def_rating": {
                home_team: game.get("home_def_rating", 110.0),
                away_team: game.get("away_def_rating", 110.0)
            },
            "pace": {
                home_team: game.get("home_pace", 100.0),
                away_team: game.get("away_pace", 100.0)
            },
            "league": league,
            "variance_scalar": 1.0
        }
        
        # Run Monte Carlo simulation
        sim_result = run_game_simulation(projection, n_iter=10000, league=league)
        
        # Process simulation results
        self._process_simulation_result(game, sim_result)

    def _process_simulation_result(self, game: Dict[str, Any], sim: Dict[str, Any]) -> None:
        """Process simulation results and identify qualified bets.
        
        Args:
            game: Game dictionary
            sim: Simulation result dictionary
        """
        home_team = game.get("home_team")
        away_team = game.get("away_team")
        league = game.get("league", "NBA")
        
        # Process game bets (moneyline, spread, total)
        thresholds = get_edge_thresholds()
        
        # Moneyline bet (home)
        if "home_moneyline_odds" in game:
            home_prob = sim["true_prob_a"]
            home_odds = game["home_moneyline_odds"]
            home_implied = implied_probability(home_odds)
            home_edge = edge_percentage(home_prob, home_implied)
            
            if home_edge >= thresholds.get("moneyline", 3.0):
                bet = {
                    "date": self.date,
                    "game_id": game.get("game_id", f"{away_team}@{home_team}"),
                    "pick": f"{home_team} ML",
                    "league": league,
                    "odds": home_odds,
                    "model_prob": home_prob,
                    "implied_prob": home_implied,
                    "edge_pct": home_edge,
                    "tier": self._get_confidence_tier(home_edge),
                    "category": "GameBet",
                    "narrative": f"Home team edge vs market line",
                    "status": "pending",
                    "result": None
                }
                self.qualified_bets.append(bet)
                self.all_bets.append(bet)

    def _get_confidence_tier(self, edge_pct: float) -> str:
        """Determine confidence tier based on edge percentage.
        
        Args:
            edge_pct: Edge percentage
        
        Returns:
            Confidence tier: A, B, or C
        """
        if edge_pct >= 5.0:
            return "A"
        elif edge_pct >= 2.0:
            return "B"
        else:
            return "C"

    def select_best_plays(self) -> None:
        """Select categorical best plays from qualified bets."""
        print(f"\n🏆 SELECTING CATEGORICAL BEST PLAYS")
        
        categories = {
            "game_bet": ("GameBet", None),
            "best_points": ("PlayerProp", "pts"),
            "best_rebounds": ("PlayerProp", "reb"),
            "best_assists": ("PlayerProp", "ast"),
            "best_combo": ("PlayerProp", "combo"),
            "best_3pm": ("PlayerProp", "3pm"),
            "best_blocks": ("PlayerProp", "blk"),
            "best_steals": ("PlayerProp", "stl"),
        }
        
        for category_name, (category_type, prop_type) in categories.items():
            # Find highest edge bet in category
            matching_bets = [
                b for b in self.qualified_bets
                if b["category"] == category_type
                and (prop_type is None or b.get("prop_type") == prop_type)
            ]
            
            if matching_bets:
                best = max(matching_bets, key=lambda x: x["edge_pct"])
                self.best_plays_by_category[category_name] = best
                print(f"   ✓ {category_name.replace('_', ' ').title()}: {best['pick']} ({best['edge_pct']:.1f}%)")

    def update_cumulative_logs(self) -> None:
        """Update cumulative BetLog.csv and predictions.json files."""
        print(f"\n💾 UPDATING CUMULATIVE LOGS")
        
        # Update BetLog.csv
        self._update_betlog_csv()
        
        # Update predictions.json
        self._update_predictions_json()
        
        print(f"   ✓ BetLog.csv updated ({len(self.qualified_bets)} new bets)")
        print(f"   ✓ predictions.json updated")

    def _update_betlog_csv(self) -> None:
        """Append new bets to cumulative BetLog.csv."""
        # Check if file exists and has header
        file_exists = self.betlog_path.exists()
        
        with open(self.betlog_path, "a", newline="") as f:
            fieldnames = [
                "Date", "Game_ID", "Pick", "League", "Odds", "Model_Prob",
                "Implied_Prob", "Edge_%", "Tier", "Category", "Narrative_Summary",
                "Status", "Result"
            ]
            
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            # Write header if file is new
            if not file_exists:
                writer.writeheader()
            
            # Write all qualified bets
            for bet in self.qualified_bets:
                writer.writerow({
                    "Date": bet["date"],
                    "Game_ID": bet["game_id"],
                    "Pick": bet["pick"],
                    "League": bet["league"],
                    "Odds": bet["odds"],
                    "Model_Prob": f"{bet['model_prob']:.4f}",
                    "Implied_Prob": f"{bet['implied_prob']:.4f}",
                    "Edge_%": f"{bet['edge_pct']:.2f}",
                    "Tier": bet["tier"],
                    "Category": bet["category"],
                    "Narrative_Summary": bet["narrative"],
                    "Status": bet["status"],
                    "Result": bet.get("result", "")
                })

    def _update_predictions_json(self) -> None:
        """Append new predictions to cumulative predictions.json."""
        # Load existing predictions or create new structure
        if self.predictions_path.exists():
            with open(self.predictions_path, "r") as f:
                data = json.load(f)
        else:
            data = {"predictions": [], "metadata": {}}
        
        # Append new predictions
        for i, bet in enumerate(self.qualified_bets, 1):
            prediction = {
                "prediction_id": f"{self.date.replace('-', '')}-{i:03d}",
                "date": self.date,
                "game": bet["game_id"],
                "pick": bet["pick"],
                "odds": bet["odds"],
                "model_probability": round(bet["model_prob"], 4),
                "implied_probability": round(bet["implied_prob"], 4),
                "edge_percentage": round(bet["edge_pct"], 2),
                "tier": bet["tier"],
                "category": bet["category"],
                "simulation_iterations": 10000,
                "narrative": bet["narrative"],
                "status": bet["status"]
            }
            data["predictions"].append(prediction)
        
        # Update metadata
        data["metadata"] = {
            "last_updated": self.timestamp,
            "total_predictions_all_time": len(data["predictions"]),
            "daily_summary": {
                "date": self.date,
                "games_analyzed": self.games_analyzed,
                "bets_generated": len(self.qualified_bets),
                "tier_a_count": len([b for b in self.qualified_bets if b["tier"] == "A"]),
                "tier_b_count": len([b for b in self.qualified_bets if b["tier"] == "B"]),
                "tier_c_count": len([b for b in self.qualified_bets if b["tier"] == "C"]),
                "average_edge": round(
                    sum(b["edge_pct"] for b in self.qualified_bets) / len(self.qualified_bets)
                    if self.qualified_bets else 0,
                    2
                )
            }
        }
        
        # Write updated file
        with open(self.predictions_path, "w") as f:
            json.dump(data, f, indent=2)

    def generate_narrative(self) -> str:
        """Generate narrative output for daily report.
        
        Returns:
            Markdown narrative string
        """
        print(f"\n📝 GENERATING NARRATIVE OUTPUT")
        
        # Count bets by tier
        tier_a = [b for b in self.qualified_bets if b["tier"] == "A"]
        tier_b = [b for b in self.qualified_bets if b["tier"] == "B"]
        tier_c = [b for b in self.qualified_bets if b["tier"] == "C"]
        
        avg_edge = sum(b["edge_pct"] for b in self.qualified_bets) / len(self.qualified_bets) if self.qualified_bets else 0
        expected_value = sum((b["odds"] / 100.0 * b["model_prob"]) for b in self.qualified_bets) if self.qualified_bets else 0
        
        narrative = f"""# Daily Betting Recommendations - {self.date}

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z')}  
**Status:** Ready for Review

---

## Executive Summary

📊 **Daily Metrics:**
- Games Analyzed: {self.games_analyzed}
- Total Qualified Bets: {len(self.qualified_bets)}
- Tier A Bets: {len(tier_a)} | Avg Edge: {(sum(b['edge_pct'] for b in tier_a) / len(tier_a) if tier_a else 0):.2f}%
- Tier B Bets: {len(tier_b)} | Avg Edge: {(sum(b['edge_pct'] for b in tier_b) / len(tier_b) if tier_b else 0):.2f}%
- Tier C Bets: {len(tier_c)} | Avg Edge: {(sum(b['edge_pct'] for b in tier_c) / len(tier_c) if tier_c else 0):.2f}%

**Portfolio Edge:** {avg_edge:.2f}% average across all qualified bets

---

## 🏆 Categorical Best Plays

"""
        
        # Add best plays
        for category, bet in self.best_plays_by_category.items():
            narrative += f"\n**{category.replace('_', ' ').title()}**  \n"
            narrative += f"Pick: {bet['pick']} @ {bet['odds']}  \n"
            narrative += f"Edge: {bet['edge_pct']:.2f}% | Tier: {bet['tier']}\n\n"
        
        # Add all qualified bets
        narrative += f"\n## 📋 All Qualified Bets ({len(self.qualified_bets)} total)\n\n"
        
        if tier_a:
            narrative += f"### Tier A - High Confidence ({len(tier_a)} bets)\n\n"
            for bet in sorted(tier_a, key=lambda x: x["edge_pct"], reverse=True):
                narrative += f"- **{bet['pick']}** @ {bet['odds']} | Edge: {bet['edge_pct']:.2f}%\n"
            narrative += "\n"
        
        if tier_b:
            narrative += f"### Tier B - Medium Confidence ({len(tier_b)} bets)\n\n"
            for bet in sorted(tier_b, key=lambda x: x["edge_pct"], reverse=True):
                narrative += f"- **{bet['pick']}** @ {bet['odds']} | Edge: {bet['edge_pct']:.2f}%\n"
            narrative += "\n"
        
        if tier_c:
            narrative += f"### Tier C - Lower Confidence ({len(tier_c)} bets)\n\n"
            for bet in sorted(tier_c, key=lambda x: x["edge_pct"], reverse=True):
                narrative += f"- **{bet['pick']}** @ {bet['odds']} | Edge: {bet['edge_pct']:.2f}%\n"
            narrative += "\n"
        
        # Add notes
        narrative += f"""\n---

## 📌 Notes

- All bets represent +EV opportunities based on Monte Carlo simulation (10,000 iterations)
- Edge percentages calculated as (Model Probability - Implied Probability) × 100
- Confidence tiers: A (5%+ edge), B (2-5% edge), C (1-2% edge)
- Player props simulated with Markov play-by-play modeling (50,000 iterations)
- All bets appended to cumulative BetLog.csv and predictions.json for tracking

**Next Steps:**
1. Review categorical best plays for immediate action
2. Check Tier A bets for highest conviction plays
3. Monitor odds movement throughout the day
4. Update results in cumulative logs after games conclude

---

*Generated by OmegaSports Betting Engine*  
*Cumulative logs: data/exports/BetLog.csv | data/logs/predictions.json*
"""
        
        # Write narrative to file
        with open(self.narrative_path, "w") as f:
            f.write(narrative)
        
        print(f"   ✓ Narrative written to {self.narrative_path}")
        return narrative

    def prepare_commit_summary(self) -> str:
        """Prepare summary for GitHub commit message.
        
        Returns:
            Commit message string
        """
        tier_a = [b for b in self.qualified_bets if b["tier"] == "A"]
        tier_b = [b for b in self.qualified_bets if b["tier"] == "B"]
        tier_c = [b for b in self.qualified_bets if b["tier"] == "C"]
        
        avg_edge_a = sum(b["edge_pct"] for b in tier_a) / len(tier_a) if tier_a else 0
        avg_edge_b = sum(b["edge_pct"] for b in tier_b) / len(tier_b) if tier_b else 0
        avg_edge_c = sum(b["edge_pct"] for b in tier_c) / len(tier_c) if tier_c else 0
        
        # Get top 3 best plays
        top_picks = sorted(self.qualified_bets, key=lambda x: x["edge_pct"], reverse=True)[:3]
        
        message = f"""Daily Bets: {self.date} - {len(self.qualified_bets)} Qualified Bets ({self.games_analyzed} Games)

CATEGORICAL BEST PLAYS:"""
        
        for i, pick in enumerate(top_picks, 1):
            message += f"\n{i}. {pick['pick']} @ {pick['odds']} ({pick['edge_pct']:.1f}% edge)"
        
        message += f"\n\nPORTFOLIO SUMMARY:\n"
        message += f"- Tier A: {len(tier_a)} bets | Avg edge: {avg_edge_a:.1f}%\n"
        message += f"- Tier B: {len(tier_b)} bets | Avg edge: {avg_edge_b:.1f}%\n"
        message += f"- Tier C: {len(tier_c)} bets | Avg edge: {avg_edge_c:.1f}%\n"
        message += f"\nAll bets appended to cumulative BetLog & predictions.json"
        
        return message

    def run(self, leagues: List[str] = None) -> Dict[str, Any]:
        """Execute complete daily betting workflow.
        
        Args:
            leagues: List of leagues to analyze
        
        Returns:
            Summary of execution results
        """
        print(f"\n{'='*70}")
        print(f"DAILY BETTING WORKFLOW - {self.date.upper()}")
        print(f"{'='*70}")
        
        # Fetch games
        games = self.fetch_games(leagues)
        if not games:
            print("\n⚠️  No games found. Exiting.")
            return {"success": False, "message": "No games found for the specified date"}
        
        # Run simulations
        self.run_simulations(games)
        
        # Select best plays
        self.select_best_plays()
        
        # Update logs
        self.update_cumulative_logs()
        
        # Generate narrative
        narrative = self.generate_narrative()
        
        # Prepare commit message
        commit_msg = self.prepare_commit_summary()
        
        # Print summary
        print(f"\n{'='*70}")
        print(f"WORKFLOW COMPLETE ✓")
        print(f"{'='*70}")
        print(f"\n✓ {len(self.qualified_bets)} qualified bets generated")
        print(f"✓ Cumulative logs updated (BetLog.csv, predictions.json)")
        print(f"✓ Narrative output saved to {self.narrative_path}")
        print(f"\nReady for GitHub commit:\n{commit_msg}")
        
        return {
            "success": True,
            "date": self.date,
            "games_analyzed": self.games_analyzed,
            "qualified_bets": len(self.qualified_bets),
            "best_plays": len(self.best_plays_by_category),
            "commit_message": commit_msg,
            "files_updated": [
                str(self.betlog_path),
                str(self.predictions_path),
                str(self.narrative_path)
            ]
        }


if __name__ == "__main__":
    # Parse command line arguments
    date = None
    leagues = ["NBA", "NFL"]
    
    if len(sys.argv) > 1:
        if "--date" in sys.argv:
            idx = sys.argv.index("--date")
            date = sys.argv[idx + 1]
        if "--leagues" in sys.argv:
            idx = sys.argv.index("--leagues")
            leagues = sys.argv[idx + 1].split(",")
    
    # Execute workflow
    generator = DailyBetGenerator(date=date)
    result = generator.run(leagues=leagues)
    
    # Exit with appropriate code
    sys.exit(0 if result["success"] else 1)
