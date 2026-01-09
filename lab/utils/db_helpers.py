"""
Pandas Query Helpers for SQLite Database

Provides simple DataFrame-based access to sports data for backtesting
and analysis. Maintains API compatibility with legacy JSON-based methods.

Usage:
    from utils.db_helpers import load_games_to_df, load_props_to_df
    
    # Load NBA games for 2020-2024
    games_df = load_games_to_df(sport='NBA', start_date='2020-01-01', end_date='2024-12-31')
    
    # Load player props for specific type
    props_df = load_props_to_df(sport='NBA', prop_type='points', start_date='2023-01-01')
"""

import sqlite3
import pandas as pd
import json
from typing import Optional, List
import os


def get_db_path() -> str:
    """Get the default database path."""
    return os.path.join(os.path.dirname(__file__), '..', 'data', 'sports_data.db')


def load_games_to_df(
    db_path: Optional[str] = None,
    sport: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    season: Optional[int] = None,
    status: Optional[str] = None,
    deserialize_json: bool = True
) -> pd.DataFrame:
    """
    Load games into a Pandas DataFrame.
    
    Args:
        db_path: Path to SQLite database (default: data/sports_data.db)
        sport: Filter by sport (NBA, NFL, etc.)
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        season: Filter by season year
        status: Filter by status (final, scheduled, etc.)
        deserialize_json: If True, parse JSON columns into dicts/lists
        
    Returns:
        pd.DataFrame: Games data
        
    Example:
        >>> df = load_games_to_df(sport='NBA', start_date='2024-01-01', end_date='2024-12-31')
        >>> print(df[['date', 'home_team', 'away_team', 'home_score', 'away_score']])
    """
    if db_path is None:
        db_path = get_db_path()
    
    conn = sqlite3.connect(db_path)
    
    # Build query
    query = "SELECT * FROM games WHERE 1=1"
    params = []
    
    if sport:
        query += " AND sport = ?"
        params.append(sport)
    
    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)
    
    if season:
        query += " AND season = ?"
        params.append(season)
    
    if status:
        query += " AND status = ?"
        params.append(status)
    
    query += " ORDER BY date, game_id"
    
    # Load into DataFrame
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    
    # Deserialize JSON columns if requested
    if deserialize_json and len(df) > 0:
        json_columns = ['home_team_stats', 'away_team_stats', 'player_stats']
        
        for col in json_columns:
            if col in df.columns:
                df[col] = df[col].apply(
                    lambda x: json.loads(x) if pd.notna(x) and x else None
                )
    
    return df


def load_props_to_df(
    db_path: Optional[str] = None,
    sport: Optional[str] = None,
    player_name: Optional[str] = None,
    prop_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> pd.DataFrame:
    """
    Load player props into a Pandas DataFrame.
    
    Args:
        db_path: Path to SQLite database
        sport: Filter by sport
        player_name: Filter by player
        prop_type: Filter by prop type (points, rebounds, assists, etc.)
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        
    Returns:
        pd.DataFrame: Player props data
        
    Example:
        >>> df = load_props_to_df(sport='NBA', prop_type='points', player_name='LeBron James')
        >>> print(df[['date', 'player_name', 'over_line', 'actual_value']])
    """
    if db_path is None:
        db_path = get_db_path()
    
    conn = sqlite3.connect(db_path)
    
    query = "SELECT * FROM player_props WHERE 1=1"
    params = []
    
    if sport:
        query += " AND sport = ?"
        params.append(sport)
    
    if player_name:
        query += " AND player_name = ?"
        params.append(player_name)
    
    if prop_type:
        query += " AND prop_type = ?"
        params.append(prop_type)
    
    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)
    
    query += " ORDER BY date, player_name"
    
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    
    return df


def load_odds_history_to_df(
    db_path: Optional[str] = None,
    game_id: Optional[str] = None,
    bookmaker: Optional[str] = None,
    market_type: Optional[str] = None
) -> pd.DataFrame:
    """
    Load historical odds into a Pandas DataFrame.
    
    Args:
        db_path: Path to SQLite database
        game_id: Filter by game ID
        bookmaker: Filter by bookmaker
        market_type: Filter by market (moneyline, spread, total)
        
    Returns:
        pd.DataFrame: Odds history data
    """
    if db_path is None:
        db_path = get_db_path()
    
    conn = sqlite3.connect(db_path)
    
    query = "SELECT * FROM odds_history WHERE 1=1"
    params = []
    
    if game_id:
        query += " AND game_id = ?"
        params.append(game_id)
    
    if bookmaker:
        query += " AND bookmaker = ?"
        params.append(bookmaker)
    
    if market_type:
        query += " AND market_type = ?"
        params.append(market_type)
    
    query += " ORDER BY game_id, timestamp"
    
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    
    return df


def export_to_json(
    output_path: str,
    sport: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    include_props: bool = True
):
    """
    Export games and props to JSON file (legacy format compatibility).
    
    Args:
        output_path: Path to output JSON file
        sport: Filter by sport
        start_date: Start date filter
        end_date: End date filter
        include_props: If True, also export props to separate file
        
    Example:
        >>> export_to_json('nba_2024.json', sport='NBA', start_date='2024-01-01')
        # Creates: nba_2024.json and nba_2024_props.json
    """
    # Load games
    df = load_games_to_df(
        sport=sport,
        start_date=start_date,
        end_date=end_date,
        deserialize_json=True
    )
    
    # Convert to records (list of dicts)
    games = df.to_dict('records')
    
    # Write to JSON
    with open(output_path, 'w') as f:
        json.dump(games, f, indent=2, default=str)
    
    print(f"✅ Exported {len(games)} games to {output_path}")
    
    # Export props if requested
    if include_props:
        props_df = load_props_to_df(
            sport=sport,
            start_date=start_date,
            end_date=end_date
        )
        
        if len(props_df) > 0:
            props_path = output_path.replace('.json', '_props.json')
            props = props_df.to_dict('records')
            
            with open(props_path, 'w') as f:
                json.dump(props, f, indent=2, default=str)
            
            print(f"✅ Exported {len(props)} props to {props_path}")


def get_database_stats(db_path: Optional[str] = None) -> dict:
    """
    Get database statistics.
    
    Args:
        db_path: Path to SQLite database
        
    Returns:
        dict: Statistics for each table
    """
    if db_path is None:
        db_path = get_db_path()
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    stats = {}
    
    tables = ['games', 'player_props', 'odds_history', 'player_props_odds', 'perplexity_cache']
    
    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            stats[table] = count
        except sqlite3.OperationalError:
            stats[table] = 0
    
    conn.close()
    
    return stats


def query_games_for_backtesting(
    sport: str,
    start_date: str,
    end_date: str,
    min_edge: Optional[float] = None
) -> pd.DataFrame:
    """
    Optimized query for backtesting experiments.
    
    Loads only essential fields for performance.
    
    Args:
        sport: Sport type
        start_date: Start date
        end_date: End date
        min_edge: Minimum edge threshold (optional filter)
        
    Returns:
        pd.DataFrame: Games with essential fields only
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    
    # Only load fields needed for backtesting
    query = """
        SELECT 
            game_id,
            date,
            sport,
            home_team,
            away_team,
            home_score,
            away_score,
            moneyline_home,
            moneyline_away,
            spread_line,
            spread_home_odds,
            spread_away_odds,
            total_line,
            total_over_odds,
            total_under_odds,
            status
        FROM games
        WHERE sport = ? AND date >= ? AND date <= ?
        ORDER BY date
    """
    
    df = pd.read_sql(query, conn, params=(sport, start_date, end_date))
    conn.close()
    
    return df


if __name__ == '__main__':
    """Test the helpers."""
    print("Testing database helpers...")
    
    # Test stats
    stats = get_database_stats()
    print("\nDatabase Stats:")
    for table, count in stats.items():
        print(f"  {table}: {count:,}")
    
    # Test games query
    print("\nTesting games query...")
    games_df = load_games_to_df(sport='NBA', start_date='2024-01-01')
    print(f"  Loaded {len(games_df)} NBA games from 2024")
    
    if len(games_df) > 0:
        print(f"  Columns: {list(games_df.columns)}")
        print(f"  Sample:\n{games_df[['date', 'home_team', 'away_team']].head()}")
    
    # Test props query
    print("\nTesting props query...")
    props_df = load_props_to_df(sport='NBA', prop_type='points')
    print(f"  Loaded {len(props_df)} point props")
    
    print("\n✅ All tests complete")
