# Data Logging Module

"""
Module Name: Data Logging
Version: 1.0.0
Description: File-based storage for simulation outputs, model probabilities, and recommended bets.
Functions:
    - log_simulation_output(date: str, game_id: str, sim_results: dict, filepath: str = None) -> str
    - log_bet_recommendation(date: str, bet_data: dict, filepath: str = None) -> str
    - load_past_logs(date: str, log_type: str = "bets") -> list
    - export_bet_log_to_csv(date: str, output_filepath: str = None) -> str
    - get_log_directory() -> str
Usage Notes:
    - All data stored as JSON files in /logs directory
    - Date-based file naming (YYYY-MM-DD format)
    - Helper functions for persistence
"""

```python
from __future__ import annotations
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any

def get_log_directory() -> str:
    """Returns the log directory path. Creates it if it doesn't exist."""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    return log_dir

def log_simulation_output(date: str, game_id: str, sim_results: Dict[str, Any], filepath: Optional[str] = None) -> str:
    """
    Logs simulation output to a JSON file.
    
    Args:
        date: Date string in YYYY-MM-DD format
        game_id: Game identifier
        sim_results: Dict containing simulation results
        filepath: Optional custom filepath (default: logs/simulations_YYYY-MM-DD.json)
    
    Returns:
        Path to the log file
    """
    log_dir = get_log_directory()
    
    if filepath is None:
        filename = f"simulations_{date}.json"
        filepath = os.path.join(log_dir, filename)
    
    # Load existing data if file exists
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            data = []
    else:
        data = []
    
    # Append new simulation result
    entry = {
        "timestamp": datetime.now().isoformat(),
        "date": date,
        "game_id": game_id,
        "sim_results": sim_results
    }
    data.append(entry)
    
    # Write back to file
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    
    return filepath

def log_bet_recommendation(date: str, bet_data: Dict[str, Any], filepath: Optional[str] = None) -> str:
    """
    Logs bet recommendation to a JSON file.
    
    Args:
        date: Date string in YYYY-MM-DD format
        bet_data: Dict containing bet recommendation data
        filepath: Optional custom filepath (default: logs/bets_YYYY-MM-DD.json)
    
    Returns:
        Path to the log file
    """
    log_dir = get_log_directory()
    
    if filepath is None:
        filename = f"bets_{date}.json"
        filepath = os.path.join(log_dir, filename)
    
    # Load existing data if file exists
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            data = []
    else:
        data = []
    
    # Append new bet recommendation
    entry = {
        "timestamp": datetime.now().isoformat(),
        "date": date,
        "bet_data": bet_data
    }
    data.append(entry)
    
    # Write back to file
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    
    return filepath

def load_past_logs(date: str, log_type: str = "bets") -> List[Dict[str, Any]]:
    """
    Loads past log entries for a given date.
    
    Args:
        date: Date string in YYYY-MM-DD format
        log_type: Type of log ("bets", "simulations", "all")
    
    Returns:
        List of log entries
    """
    log_dir = get_log_directory()
    entries = []
    
    if log_type in ("bets", "all"):
        bets_file = os.path.join(log_dir, f"bets_{date}.json")
        if os.path.exists(bets_file):
            try:
                with open(bets_file, 'r') as f:
                    entries.extend(json.load(f))
            except (json.JSONDecodeError, IOError):
                pass
    
    if log_type in ("simulations", "all"):
        sim_file = os.path.join(log_dir, f"simulations_{date}.json")
        if os.path.exists(sim_file):
            try:
                with open(sim_file, 'r') as f:
                    entries.extend(json.load(f))
            except (json.JSONDecodeError, IOError):
                pass
    
    return entries

def export_bet_log_to_csv(date: str, output_filepath: Optional[str] = None) -> str:
    """
    Exports bet log to CSV format for easy analysis.
    
    Args:
        date: Date string in YYYY-MM-DD format
        output_filepath: Optional custom output filepath
    
    Returns:
        Path to the CSV file
    """
    import csv
    
    log_dir = get_log_directory()
    bets_file = os.path.join(log_dir, f"bets_{date}.json")
    
    if output_filepath is None:
        output_filepath = os.path.join(log_dir, f"bets_{date}.csv")
    
    # Load bet data
    bets = load_past_logs(date, log_type="bets")
    
    if not bets:
        # Create empty CSV with headers
        with open(output_filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                "Date", "GameID", "Pick", "Odds", "ImpliedProb", "ModelProb",
                "Edge", "ConfidenceTier", "Result", "PnL"
            ])
        return output_filepath
    
    # Write to CSV
    with open(output_filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            "Date", "GameID", "Pick", "Odds", "ImpliedProb", "ModelProb",
            "Edge", "ConfidenceTier", "Result", "PnL"
        ])
        
        for entry in bets:
            bet_data = entry.get("bet_data", {})
            writer.writerow([
                entry.get("date", ""),
                bet_data.get("game_id", ""),
                bet_data.get("pick", ""),
                bet_data.get("odds_american", ""),
                bet_data.get("implied_prob", ""),
                bet_data.get("model_prob", ""),
                bet_data.get("edge", ""),
                bet_data.get("confidence_tier", ""),
                bet_data.get("result", ""),
                bet_data.get("pnl", "")
            ])
    
    return output_filepath

```

