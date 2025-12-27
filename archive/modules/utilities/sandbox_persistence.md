# Sandbox Persistence Module

"""
Module Name: Sandbox Persistence & Bet Tracking
Version: 2.0.0
Description: Persistent bet tracking, simulation result logging, and backtesting for OMEGA in Perplexity Spaces sandbox environment.
Class:
    - OmegaCacheLogger: Bet log and audit engine with swappable storage backend
Methods:
    - log_bet_recommendation(bet_data: dict) -> str
    - log_simulation_result(sim_data: dict) -> str
    - update_bet_result(bet_id: str, result: str, final_score: str = None, closing_odds: str = None) -> None
    - get_pending_bets() -> list
    - get_bets_by_date_range(start_date: str, end_date: str) -> list
    - run_backtest_audit(start_date: str = None, end_date: str = None, bets_override: list = None) -> dict
    - export_to_csv(output_file: str = "omega_bets.csv", format: str = "standard") -> str
    - update_pending_bets_and_export(result_updates: list, output_file: str = "BetLog.csv") -> str
    - load_from_thread_fallback(thread_files: list) -> list
Usage Notes:
    - EXECUTION METHOD: Code in this .md file is extracted and executed using get-execute in Perplexity Spaces sandbox
    - STORAGE BACKEND: Swappable via base_path parameter (default: "data/logs" for logs, "data/exports" for CSV)
                      Can use "data/logs/" for repo/Space context or "/tmp/omega_storage/" for session-only
    - FILE OPERATIONS: Use standard Python file I/O (open(), json.dump(), etc.) to read/write files
    - PERSISTENCE: Files persist in Spaces if uploaded/synced. Export as attachments at end of task for long-term storage.
    - DATA RETRIEVAL: Load from previous task attachments in Spaces threads or Space files, not by assuming sandbox copy exists
    - Bet ID format: YYYY-MM-DD_LEAGUE_N (e.g., "2025-11-24_NBA_1")
"""

```python
from __future__ import annotations
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any

try:
    from odds_eval import implied_probability, american_to_decimal
except ImportError:
    # Fallback if odds_eval not loaded
    def american_to_decimal(odds: float) -> float:
        odds = float(odds)
        if odds > 0:
            return 1 + odds / 100
        return 1 + 100 / abs(odds)
    
    def implied_probability(odds: float, odds_type: str = "american") -> float:
        if odds_type == "decimal":
            return 1 / float(odds)
        return 1 / american_to_decimal(odds)


class OmegaCacheLogger:
    """
    Bet log and audit engine for OMEGA with swappable storage backend.
    
    This class handles bet tracking, simulation logging, and backtesting.
    Storage backend is configurable via base_path parameter:
    - Use "data/logs" for repo/Space context (persists if uploaded/synced)
    - Use "/tmp/omega_storage" for strict session-only workflows
    
    PERSISTENCE STRATEGY:
    1. Session: Write to base_path during task execution
    2. End of session: Export files as attachments or commit to GitHub
    3. Future sessions: Load from attachments/Space files, not sandbox copy
    """
    
    def __init__(self, base_path: str = "data/logs", exports_path: Optional[str] = None):
        """
        Initialize the logger with swappable storage backend.
        
        Args:
            base_path: Base directory for JSON log files (default: "data/logs")
                       Use "data/logs" for repo/Space context
                       Use "/tmp/omega_storage" for session-only
            exports_path: Directory for CSV export files (default: "data/exports" or base_path)
                          If None, uses "data/exports" if base_path is "data/logs",
                          otherwise uses base_path
        """
        self.base_path = base_path
        
        # Determine exports path
        if exports_path is None:
            if base_path == "data/logs":
                self.exports_path = "data/exports"
            else:
                self.exports_path = base_path
        else:
            self.exports_path = exports_path
        
        # Set file paths
        self.bet_log_file = os.path.join(base_path, "bet_log.json")
        self.sim_log_file = os.path.join(base_path, "simulation_log.json")
        self.audit_log_file = os.path.join(base_path, "audit_log.json")
        
        # Create directories if they don't exist
        os.makedirs(base_path, exist_ok=True)
        os.makedirs(self.exports_path, exist_ok=True)
        
        self._initialize_logs()
    
    def _initialize_logs(self) -> None:
        """Initialize log files if they don't exist."""
        if not os.path.exists(self.bet_log_file):
            with open(self.bet_log_file, 'w') as f:
                json.dump([], f, indent=2)
        
        if not os.path.exists(self.sim_log_file):
            with open(self.sim_log_file, 'w') as f:
                json.dump([], f, indent=2)
        
        if not os.path.exists(self.audit_log_file):
            with open(self.audit_log_file, 'w') as f:
                json.dump([], f, indent=2)
    
    def _load_bet_log(self) -> List[Dict[str, Any]]:
        """Load bet log from file."""
        try:
            if os.path.exists(self.bet_log_file):
                with open(self.bet_log_file, 'r') as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
        return []
    
    def _save_bet_log(self, bets: List[Dict[str, Any]]) -> None:
        """Save bet log to file."""
        with open(self.bet_log_file, 'w') as f:
            json.dump(bets, f, indent=2)
    
    def _load_sim_log(self) -> List[Dict[str, Any]]:
        """Load simulation log from file."""
        try:
            if os.path.exists(self.sim_log_file):
                with open(self.sim_log_file, 'r') as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
        return []
    
    def _save_sim_log(self, sims: List[Dict[str, Any]]) -> None:
        """Save simulation log to file."""
        with open(self.sim_log_file, 'w') as f:
            json.dump(sims, f, indent=2)
    
    def _generate_bet_id(self, date: str, league: str) -> str:
        """
        Generate unique bet ID: YYYY-MM-DD_LEAGUE_N
        
        Args:
            date: Date string in YYYY-MM-DD format
            league: League identifier
        
        Returns:
            Unique bet ID string
        """
        bets = self._load_bet_log()
        # Count existing bets for this date/league
        count = sum(1 for bet in bets if bet.get("date") == date and bet.get("league") == league)
        return f"{date}_{league}_{count + 1}"
    
    def log_bet_recommendation(self, bet_data: Dict[str, Any]) -> str:
        """
        Log a single bet recommendation and return bet_id.
        
        Required fields in bet_data:
            - date: str (YYYY-MM-DD)
            - league: str (e.g., "NBA", "NFL")
            - matchup: str (e.g., "Pistons vs Pacers")
            - pick: str (e.g., "DET -9.5")
            - bet_type: str (e.g., "spread", "total", "moneyline", "prop")
            - odds: str (American format, e.g., "-110")
            - implied_prob: float
            - model_prob: float
            - edge_pct: float
            - confidence: str (e.g., "High", "Medium", "Low")
            - predicted_outcome: str
            - factors: str (explanation)
        
        Optional fields:
            - stake_units: float
            - stake_amount: float
            - game_id: str
        
        Returns:
            bet_id: str (format: YYYY-MM-DD_LEAGUE_N)
        """
        # Validate required fields
        required = ["date", "league", "matchup", "pick", "bet_type", "odds",
                   "implied_prob", "model_prob", "edge_pct", "confidence",
                   "predicted_outcome", "factors"]
        for field in required:
            if field not in bet_data:
                raise ValueError(f"Missing required field: {field}")
        
        # Generate bet ID
        bet_id = self._generate_bet_id(bet_data["date"], bet_data["league"])
        
        # Create bet record
        bet_record = {
            "bet_id": bet_id,
            "date": bet_data["date"],
            "league": bet_data["league"],
            "matchup": bet_data["matchup"],
            "pick": bet_data["pick"],
            "bet_type": bet_data["bet_type"],
            "odds": bet_data["odds"],
            "implied_prob": float(bet_data["implied_prob"]),
            "model_prob": float(bet_data["model_prob"]),
            "edge_pct": float(bet_data["edge_pct"]),
            "confidence": bet_data["confidence"],
            "predicted_outcome": bet_data["predicted_outcome"],
            "factors": bet_data["factors"],
            "stake_units": bet_data.get("stake_units"),
            "stake_amount": bet_data.get("stake_amount"),
            "game_id": bet_data.get("game_id"),
            "result": None,
            "final_score": None,
            "closing_odds": None,
            "clv_pct": None,
            "logged_at": datetime.now().isoformat() + "Z",
            "updated_at": None
        }
        
        # Load existing bets and append
        bets = self._load_bet_log()
        bets.append(bet_record)
        self._save_bet_log(bets)
        
        return bet_id
    
    def log_simulation_result(self, sim_data: Dict[str, Any]) -> str:
        """
        Log a simulation result.
        
        Args:
            sim_data: Dict with keys:
                - date: str (YYYY-MM-DD)
                - game_id: str
                - league: str
                - matchup: str
                - sim_results: dict (from simulation_engine)
                - n_iterations: int
                - model_probabilities: dict
                - predicted_scores: dict
        
        Returns:
            sim_id: str (format: YYYY-MM-DD_GAMEID)
        """
        date = sim_data.get("date", datetime.now().strftime("%Y-%m-%d"))
        game_id = sim_data.get("game_id", "unknown")
        sim_id = f"{date}_{game_id}"
        
        sim_record = {
            "sim_id": sim_id,
            "date": date,
            "game_id": game_id,
            "league": sim_data.get("league"),
            "matchup": sim_data.get("matchup"),
            "sim_results": sim_data.get("sim_results", {}),
            "n_iterations": sim_data.get("n_iterations", 0),
            "model_probabilities": sim_data.get("model_probabilities", {}),
            "predicted_scores": sim_data.get("predicted_scores", {}),
            "logged_at": datetime.now().isoformat() + "Z"
        }
        
        # Load existing sims and append
        sims = self._load_sim_log()
        sims.append(sim_record)
        self._save_sim_log(sims)
        
        return sim_id
    
    def update_bet_result(
        self,
        bet_id: str,
        result: str,
        final_score: Optional[str] = None,
        closing_odds: Optional[str] = None
    ) -> None:
        """
        Update a logged bet with result, final_score, and optionally closing_odds.
        
        Args:
            bet_id: Bet ID to update
            result: "Win", "Loss", or "Push"
            final_score: Final game score (e.g., "DET 125, IND 115")
            closing_odds: Closing odds in American format (e.g., "-112")
        """
        if result not in ("Win", "Loss", "Push"):
            raise ValueError(f"Invalid result: {result}. Must be 'Win', 'Loss', or 'Push'")
        
        bets = self._load_bet_log()
        updated = False
        
        for bet in bets:
            if bet.get("bet_id") == bet_id:
                bet["result"] = result
                bet["final_score"] = final_score
                bet["closing_odds"] = closing_odds
                bet["updated_at"] = datetime.now().isoformat() + "Z"
                
                # Calculate CLV if closing_odds provided
                if closing_odds and bet.get("odds"):
                    bet["clv_pct"] = self._calculate_clv(bet["odds"], closing_odds)
                
                updated = True
                break
        
        if not updated:
            raise ValueError(f"Bet ID not found: {bet_id}")
        
        self._save_bet_log(bets)
    
    def get_pending_bets(self) -> List[Dict[str, Any]]:
        """
        Return all bets with result == None (pending results).
        
        Returns:
            List of bet records without results
        """
        bets = self._load_bet_log()
        return [bet for bet in bets if bet.get("result") is None]
    
    def get_bets_by_date_range(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        Return all bets with date in [start_date, end_date] (inclusive).
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
        
        Returns:
            List of bet records in date range
        """
        bets = self._load_bet_log()
        return [
            bet for bet in bets
            if start_date <= bet.get("date", "") <= end_date
        ]
    
    def _calculate_clv(self, opening_odds: str, closing_odds: str) -> float:
        """
        Calculate Closing Line Value (CLV) percentage.
        
        CLV = (Closing Implied Prob - Opening Implied Prob) * 100
        
        Positive CLV means line moved in our favor.
        
        Args:
            opening_odds: Opening odds in American format
            closing_odds: Closing odds in American format
        
        Returns:
            CLV percentage (positive = favorable)
        """
        try:
            open_imp = implied_probability(float(opening_odds))
            close_imp = implied_probability(float(closing_odds))
            return (close_imp - open_imp) * 100.0
        except (ValueError, TypeError):
            return 0.0
    
    def _calculate_brier(self, outcomes: List[int], probs: List[float]) -> float:
        """
        Calculate Brier score for probability calibration.
        
        Brier = (1/n) * Σ(p_i - o_i)²
        where p_i is predicted probability and o_i is outcome (0 or 1).
        
        Lower is better (0 = perfect, 1 = worst).
        
        Args:
            outcomes: List of outcomes (1 for win, 0 for loss)
            probs: List of predicted probabilities
        
        Returns:
            Brier score (0.0 to 1.0)
        """
        if not outcomes or len(outcomes) != len(probs):
            return 0.0
        return sum((p - o) ** 2 for p, o in zip(probs, outcomes)) / len(outcomes)
    
    def run_backtest_audit(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        bets_override: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Compute backtest metrics and audit results.
        
        Metrics computed:
            - total_bets, wins, losses, pushes
            - win_rate (%), roi_pct (%)
            - avg_edge_pct, avg_clv_pct
            - brier_score
            - by_league, by_confidence, by_bet_type
        
        Args:
            start_date: Start date in YYYY-MM-DD format (optional)
            end_date: End date in YYYY-MM-DD format (optional)
            bets_override: Optional list of bets to use instead of reading from file
        
        Returns:
            Dict with audit metrics
        """
        # Get bets
        if bets_override is not None:
            bets = bets_override
        elif start_date and end_date:
            bets = self.get_bets_by_date_range(start_date, end_date)
        else:
            bets = self._load_bet_log()
        
        # Filter to only settled bets
        settled_bets = [bet for bet in bets if bet.get("result") in ("Win", "Loss", "Push")]
        
        if not settled_bets:
            return {
                "total_bets": 0,
                "settled_bets": 0,
                "message": "No settled bets found for audit period"
            }
        
        # Overall metrics
        total_bets = len(settled_bets)
        wins = sum(1 for bet in settled_bets if bet.get("result") == "Win")
        losses = sum(1 for bet in settled_bets if bet.get("result") == "Loss")
        pushes = sum(1 for bet in settled_bets if bet.get("result") == "Push")
        
        win_rate = (wins / (wins + losses)) * 100.0 if (wins + losses) > 0 else 0.0
        
        # ROI calculation
        total_stake = sum(bet.get("stake_amount", 0.0) or 0.0 for bet in settled_bets)
        total_pnl = 0.0
        for bet in settled_bets:
            if bet.get("result") == "Win":
                odds = bet.get("odds", "-110")
                stake = bet.get("stake_amount", 0.0) or 0.0
                try:
                    dec = american_to_decimal(float(odds))
                    total_pnl += stake * (dec - 1)
                except (ValueError, TypeError):
                    pass
            elif bet.get("result") == "Loss":
                stake = bet.get("stake_amount", 0.0) or 0.0
                total_pnl -= stake
        
        roi_pct = (total_pnl / total_stake * 100.0) if total_stake > 0 else 0.0
        
        # Average edge and CLV
        edges = [bet.get("edge_pct", 0.0) for bet in settled_bets if bet.get("edge_pct") is not None]
        avg_edge_pct = sum(edges) / len(edges) if edges else 0.0
        
        clvs = [bet.get("clv_pct", 0.0) for bet in settled_bets if bet.get("clv_pct") is not None]
        avg_clv_pct = sum(clvs) / len(clvs) if clvs else 0.0
        
        # Brier score
        outcomes = [1 if bet.get("result") == "Win" else 0 for bet in settled_bets if bet.get("result") != "Push"]
        probs = [bet.get("model_prob", 0.0) for bet in settled_bets if bet.get("result") != "Push"]
        brier = self._calculate_brier(outcomes, probs)
        
        # Breakdowns
        by_league = {}
        by_confidence = {}
        by_bet_type = {}
        
        for bet in settled_bets:
            league = bet.get("league", "Unknown")
            confidence = bet.get("confidence", "Unknown")
            bet_type = bet.get("bet_type", "Unknown")
            
            for breakdown, key in [(by_league, league), (by_confidence, confidence), (by_bet_type, bet_type)]:
                if key not in breakdown:
                    breakdown[key] = {"total": 0, "wins": 0, "losses": 0, "pushes": 0}
                breakdown[key]["total"] += 1
                if bet.get("result") == "Win":
                    breakdown[key]["wins"] += 1
                elif bet.get("result") == "Loss":
                    breakdown[key]["losses"] += 1
                elif bet.get("result") == "Push":
                    breakdown[key]["pushes"] += 1
        
        # Calculate win rates for breakdowns
        for breakdown in [by_league, by_confidence, by_bet_type]:
            for key, stats in breakdown.items():
                wins_losses = stats["wins"] + stats["losses"]
                stats["win_rate"] = (stats["wins"] / wins_losses * 100.0) if wins_losses > 0 else 0.0
        
        audit_result = {
            "total_bets": total_bets,
            "settled_bets": len(settled_bets),
            "wins": wins,
            "losses": losses,
            "pushes": pushes,
            "win_rate_pct": round(win_rate, 2),
            "roi_pct": round(roi_pct, 2),
            "total_stake": round(total_stake, 2),
            "total_pnl": round(total_pnl, 2),
            "avg_edge_pct": round(avg_edge_pct, 2),
            "avg_clv_pct": round(avg_clv_pct, 2),
            "brier_score": round(brier, 4),
            "by_league": by_league,
            "by_confidence": by_confidence,
            "by_bet_type": by_bet_type,
            "audit_date": datetime.now().isoformat() + "Z",
            "date_range": {
                "start": start_date,
                "end": end_date
            }
        }
        
        # Log audit result
        try:
            audits = []
            if os.path.exists(self.audit_log_file):
                with open(self.audit_log_file, 'r') as f:
                    audits = json.load(f)
            audits.append(audit_result)
            with open(self.audit_log_file, 'w') as f:
                json.dump(audits, f, indent=2)
        except (json.JSONDecodeError, IOError):
            pass
        
        return audit_result
    
    def export_to_csv(self, output_file: str = "omega_bets.csv", format: str = "standard") -> str:
        """
        Export bet_log.json to CSV in exports_path and return the path.
        
        Args:
            output_file: Output CSV filename (default: "omega_bets.csv")
            format: "standard" (full columns) or "betlog" (matches BetLog.csv format)
        
        Returns:
            Path to the CSV file
        """
        import csv
        
        output_path = os.path.join(self.exports_path, output_file)
        bets = self._load_bet_log()
        
        if format == "betlog":
            # Match BetLog.csv format: Date,League,Game_ID,Pick,Odds_American,Implied_Prob,Model_Prob,Edge_%,Confidence_Tier,Predicted Outcome,Factors,Final Box Score,Result
            headers = [
                "Date", "League", "Game_ID", "Pick", "Odds_American", "Implied_Prob",
                "Model_Prob", "Edge_%", "Confidence_Tier", "Predicted Outcome",
                "Factors", "Final Box Score", "Result"
            ]
        else:
            # Standard format with all columns
            headers = [
                "bet_id", "date", "league", "matchup", "pick", "bet_type",
                "odds", "implied_prob", "model_prob", "edge_pct", "confidence",
                "predicted_outcome", "factors", "stake_units", "stake_amount",
                "result", "final_score", "closing_odds", "clv_pct",
                "logged_at", "updated_at"
            ]
        
        if not bets:
            # Create empty CSV with headers
            with open(output_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
            return output_path
        
        # Write to CSV
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            
            for bet in bets:
                if format == "betlog":
                    # Map to BetLog.csv format
                    confidence_tier = bet.get("confidence", "")
                    # Convert confidence to emoji format if needed
                    if confidence_tier == "High":
                        confidence_tier = "🔵 High"
                    elif confidence_tier == "Medium":
                        confidence_tier = "🟢 Med"
                    elif confidence_tier == "Low":
                        confidence_tier = "🟡 Low"
                    
                    writer.writerow([
                        bet.get("date", ""),
                        bet.get("league", ""),
                        bet.get("game_id", bet.get("matchup", "")),
                        bet.get("pick", ""),
                        bet.get("odds", ""),
                        bet.get("implied_prob", ""),
                        bet.get("model_prob", ""),
                        bet.get("edge_pct", ""),
                        confidence_tier,
                        bet.get("predicted_outcome", ""),
                        bet.get("factors", ""),
                        bet.get("final_score", ""),
                        bet.get("result", "")
                    ])
                else:
                    # Standard format
                    writer.writerow([
                        bet.get("bet_id", ""),
                        bet.get("date", ""),
                        bet.get("league", ""),
                        bet.get("matchup", ""),
                        bet.get("pick", ""),
                        bet.get("bet_type", ""),
                        bet.get("odds", ""),
                        bet.get("implied_prob", ""),
                        bet.get("model_prob", ""),
                        bet.get("edge_pct", ""),
                        bet.get("confidence", ""),
                        bet.get("predicted_outcome", ""),
                        bet.get("factors", ""),
                        bet.get("stake_units", ""),
                        bet.get("stake_amount", ""),
                        bet.get("result", ""),
                        bet.get("final_score", ""),
                        bet.get("closing_odds", ""),
                        bet.get("clv_pct", ""),
                        bet.get("logged_at", ""),
                        bet.get("updated_at", "")
                    ])
        
        return output_path
    
    def load_from_thread_fallback(self, thread_files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Load bet records from thread files (fallback when /tmp not accessible).
        
        This method parses bet records from JSON files that were attached/created
        in previous threads within the Space (last 7 days).
        
        Args:
            thread_files: List of dicts with keys:
                - "filename": str (e.g., "bets_2025-11-24.json")
                - "content": str (JSON content) or dict (parsed JSON)
        
        Returns:
            List of bet records
        """
        bets = []
        
        for file_info in thread_files:
            try:
                # Handle both string content and parsed dict
                if isinstance(file_info.get("content"), str):
                    content = json.loads(file_info["content"])
                else:
                    content = file_info.get("content", {})
                
                # Handle different file structures
                if isinstance(content, list):
                    # Direct list of bets
                    bets.extend(content)
                elif isinstance(content, dict):
                    # Could be wrapped in a structure
                    if "bets" in content:
                        bets.extend(content["bets"])
                    elif "bet_data" in content:
                        bets.append(content["bet_data"])
                    else:
                        # Assume it's a single bet record
                        bets.append(content)
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
        
        return bets
    
    def update_pending_bets_and_export(self, result_updates: List[Dict[str, Any]], output_file: str = "BetLog.csv") -> str:
        """
        Update pending bets with results and export cumulative bet log to CSV in BetLog.csv format.
        
        This method:
        1. Updates pending bets with results, final scores, and closing odds
        2. Exports the entire cumulative bet log to CSV matching BetLog.csv format
        3. Stores the updated bet log back to base_path/bet_log.json
        
        Args:
            result_updates: List of dicts with keys:
                - "bet_id": str (required)
                - "result": str ("Win", "Loss", or "Push")
                - "final_score": str (optional)
                - "closing_odds": str (optional, for CLV calculation)
            output_file: Output CSV filename (default: "BetLog.csv")
        
        Returns:
            Path to the exported CSV file
        """
        bets = self._load_bet_log()
        updated_count = 0
        
        # Update bets with results
        for update in result_updates:
            bet_id = update.get("bet_id")
            if not bet_id:
                continue
            
            for bet in bets:
                if bet.get("bet_id") == bet_id:
                    bet["result"] = update.get("result")
                    bet["final_score"] = update.get("final_score")
                    bet["closing_odds"] = update.get("closing_odds")
                    bet["updated_at"] = datetime.now().isoformat() + "Z"
                    
                    # Calculate CLV if closing odds provided
                    if update.get("closing_odds") and bet.get("odds"):
                        bet["clv_pct"] = self._calculate_clv(bet["odds"], update["closing_odds"])
                    
                    updated_count += 1
                    break
        
        # Save updated bet log back to file
        self._save_bet_log(bets)
        
        # Export to CSV in BetLog.csv format (cumulative, all bets)
        csv_path = self.export_to_csv(output_file=output_file, format="betlog")
        
        return csv_path

```

## Storage Backend & Persistence

### Swappable Storage Backend

The `OmegaCacheLogger` class uses a swappable storage backend via the `base_path` parameter:

**Default (Recommended for Spaces/Repo):**
```python
logger = OmegaCacheLogger(base_path="data/logs")
# Logs go to: data/logs/bet_log.json, data/logs/simulation_log.json
# Exports go to: data/exports/BetLog.csv
```

**Session-Only (Alternative):**
```python
logger = OmegaCacheLogger(base_path="/tmp/omega_storage")
# All files go to: /tmp/omega_storage/
```

**Custom Paths:**
```python
logger = OmegaCacheLogger(base_path="data/logs", exports_path="data/exports")
# Explicitly set both paths
```

### Persistence Strategy

**Three-Layer Approach:**

1. **Session Storage**: Write to `base_path` during task execution
   - Files persist in Spaces if uploaded/synced to the Space
   - Files written only to sandbox filesystem may not persist

2. **End of Session**: Export files for long-term storage
   - Read files from `base_path` and `exports_path`
   - Deliver as attachments in task answer
   - Optionally upload as Space files for explicit persistence
   - Optionally commit to GitHub (structure committed, daily data git-ignored)

3. **Future Sessions**: Load from persistent sources
   - Load from previous task attachments
   - Load from explicitly uploaded Space files
   - **Do NOT** assume sandbox copy still exists

### File Locations

**JSON Logs** (in `base_path`, default: `data/logs/`):
- `bet_log.json` - All bet recommendations and results
- `simulation_log.json` - All simulation results
- `audit_log.json` - Audit history

**CSV Exports** (in `exports_path`, default: `data/exports/`):
- `BetLog.csv` - Cumulative bet log (BetLog.csv format)
- `omega_bets_YYYY-MM-DD.csv` - Daily bet summaries
- `daily_suggested_bets-MM-DD.csv` - Daily suggested bets

### Data Retrieval

To retrieve data in subsequent tasks:

1. **Review threads within the Space** from previous task sessions
2. **Locate file attachments** (BetLog.csv, bet_log.json, simulation_log.json) from previous tasks
3. **Extract JSON/CSV content** from those attached files
4. **Use `load_from_thread_fallback()`** method to parse bet records from those files
5. **Pass parsed bets to `run_backtest_audit(bets_override=...)`** for analysis

### Bet Record Schema

Each bet record in JSON files should follow this schema:

```json
{
  "bet_id": "2025-11-24_NBA_1",
  "date": "2025-11-24",
  "league": "NBA",
  "matchup": "Pistons vs Pacers",
  "pick": "DET -9.5",
  "bet_type": "spread",
  "odds": "-110",
  "implied_prob": 0.485,
  "model_prob": 0.54,
  "edge_pct": 5.5,
  "confidence": "High",
  "predicted_outcome": "DET 123, IND 110",
  "factors": "Pistons home court advantage; Pacers on back-to-back",
  "stake_units": 2.5,
  "stake_amount": 12.5,
  "result": "Win",
  "final_score": "DET 125, IND 115",
  "closing_odds": "-112",
  "clv_pct": 0.45,
  "logged_at": "2025-11-24T13:00:00Z",
  "updated_at": "2025-11-24T23:30:00Z"
}
```

### Simulation Result Schema

Simulation results can be stored in the same `simulation_log.json` file or separate files:

```json
{
  "sim_id": "2025-11-24_NBA_DET_IND",
  "date": "2025-11-24",
  "game_id": "NBA_DET_IND",
  "league": "NBA",
  "matchup": "Pistons vs Pacers",
  "sim_results": {
    "team_a_wins": 6500,
    "team_b_wins": 3500,
    "true_prob_a": 0.65,
    "true_prob_b": 0.35
  },
  "n_iterations": 10000,
  "model_probabilities": {
    "home_win": 0.65,
    "away_win": 0.35
  },
  "predicted_scores": {
    "home": 123.5,
    "away": 110.2
  },
  "logged_at": "2025-11-24T13:00:00Z"
}
```

### Result Files at End of Session

**Result files MUST be delivered at the end of every session** for long-term persistence. The agent should:

1. After logging bets/simulations to `base_path` (for session use), read the files
2. **Always deliver these files as attachments** at the end of the task answer:
   - `bet_log.json` - All bets logged in this session (from `base_path/bet_log.json`)
   - `simulation_log.json` - All simulations logged in this session (from `base_path/simulation_log.json`)
   - `BetLog.csv` or `omega_bets_YYYY-MM-DD.csv` - CSV export (from `exports_path/`)
3. File naming: Use consistent names (`bet_log.json`, `simulation_log.json`, `BetLog.csv`)
4. Future tasks load data from these attached files using `load_from_thread_fallback()` by reviewing previous thread attachments
5. Optionally: Upload files as Space files for explicit persistence in the Space

