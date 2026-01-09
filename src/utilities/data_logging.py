"""
Data Logging Module

File-based storage for simulation outputs, model probabilities, and recommended bets.

Functions:
    - get_log_directory: Returns the log directory path
    - log_simulation_output: Logs simulation output to a JSON file
    - log_bet_recommendation: Logs bet recommendation to a JSON file
    - load_past_logs: Loads past log entries for a given date
    - export_bet_log_to_csv: Exports bet log to CSV format
"""

from __future__ import annotations
import csv
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any

try:
    from src.utils.schema_validator import get_schema_validator, SchemaViolationException
except Exception:
    # Fallback if validator cannot be imported; logging proceeds without schema checks
    get_schema_validator = None
    SchemaViolationException = Exception  # type: ignore

def get_log_directory() -> str:
    """
    Returns the log directory path. Creates it if it doesn't exist.
    
    Returns:
        Path to the log directory
    """
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    return log_dir


def log_simulation_output(
    date: str,
    game_id: str,
    sim_results: Dict[str, Any],
    filepath: Optional[str] = None
) -> str:
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
    
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            data = []
    else:
        data = []
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "date": date,
        "game_id": game_id,
        "sim_results": sim_results
    }
    data.append(entry)
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    
    return filepath


def log_bet_recommendation(
    date: str,
    bet_data: Dict[str, Any],
    filepath: Optional[str] = None
) -> str:
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
    
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            data = []
    else:
        data = []
    
    # Validate bet_data against schema (LAX mode will log violations, STRICT will raise)
    if get_schema_validator:
        try:
            validator = get_schema_validator()
            validator.validate_betlog_row(bet_data)
        except SchemaViolationException as e:
            # In STRICT mode this will raise; allow caller to handle
            raise e
        except Exception:
            # If validator fails unexpectedly, proceed without blocking logging
            pass

    entry = {
        "timestamp": datetime.now().isoformat(),
        "date": date,
        "bet_data": bet_data
    }
    data.append(entry)
    
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
    entries: List[Dict[str, Any]] = []
    
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
    log_dir = get_log_directory()
    
    if output_filepath is None:
        output_filepath = os.path.join(log_dir, f"bets_{date}.csv")
    
    bets = load_past_logs(date, log_type="bets")
    
    headers = [
        "Date", "GameID", "Pick", "Odds", "ImpliedProb", "ModelProb",
        "Edge", "ConfidenceTier", "Result", "PnL"
    ]
    
    with open(output_filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        
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
