#!/usr/bin/env python3
"""
Backfill Player Props Actuals

Reads player_stats JSON blobs in the games table and populates the player_props
(table for actual player outcomes) with prop records (points, rebounds, assists,
steals, blocks, turnovers, threes made, FG/3PT/FT percentages).

Usage:
    python scripts/backfill_player_props.py
    python scripts/backfill_player_props.py --limit 5000
    python scripts/backfill_player_props.py --sport NBA --season 2024
"""

import os
import sys
import json
import time
from typing import Dict, Any, List, Optional, Iterable
from datetime import datetime

# Add project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.db_manager import DatabaseManager


def _sanitize_player_name(name: str) -> str:
    return name.strip().lower().replace(' ', '_') if name else 'unknown'


def _to_float(val: Any) -> Optional[float]:
    try:
        if val is None:
            return None
        if isinstance(val, (int, float)):
            return float(val)
        # Handle strings like "12" or "12.5"
        return float(str(val).replace('%', ''))
    except Exception:
        return None


class PlayerPropsBackfill:
    """Backfills player_props from games.player_stats actuals."""

    # Each prop maps to one or more possible stat keys found in player_stats blobs
    STAT_FIELD_ALIASES: Dict[str, List[str]] = {
        'points': ['points', 'pts'],
        'rebounds': ['rebounds', 'reb'],
        'assists': ['assists', 'ast'],
        'steals': ['steals', 'stl'],
        'blocks': ['blocks', 'blk'],
        'turnovers': ['turnovers', 'turnover'],
        'three_pt_made': ['three_pt_made', 'fg3m', 'fg3_made'],
        'fg_pct': ['fg_pct'],
        'three_pt_pct': ['three_pt_pct', 'fg3_pct'],
        'ft_pct': ['ft_pct'],
    }

    def __init__(self, db_path: str = 'data/sports_data.db', limit: Optional[int] = None, sport: Optional[str] = None, season: Optional[int] = None):
        self.db_manager = DatabaseManager(db_path)
        self.limit = limit
        self.sport = sport
        self.season = season
        self.stats = {
            'games_processed': 0,
            'props_inserted': 0,
            'props_updated': 0,
            'games_skipped': 0,
            'errors': 0,
        }

    def _fetch_games(self) -> List[Dict[str, Any]]:
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        query = """
            SELECT game_id, date, sport, season, home_team, away_team, player_stats
            FROM games
            WHERE (player_stats IS NOT NULL AND player_stats != '' AND player_stats != '[]')
            AND status = 'Final'
        """
        params: List[Any] = []

        if self.sport:
            query += " AND sport = ?"
            params.append(self.sport)
        if self.season:
            query += " AND season = ?"
            params.append(self.season)
        query += " ORDER BY date DESC"
        if self.limit:
            query += " LIMIT ?"
            params.append(self.limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        games: List[Dict[str, Any]] = []
        for row in rows:
            games.append({
                'game_id': row[0],
                'date': row[1],
                'sport': row[2],
                'season': row[3],
                'home_team': row[4],
                'away_team': row[5],
                'player_stats': row[6],
            })
        return games

    def _infer_opponent(self, player_team: str, home_team: str, away_team: str) -> str:
        def _norm(name: str) -> str:
            return name.lower().strip() if name else ''

        pt = _norm(player_team)
        ht = _norm(home_team)
        at = _norm(away_team)

        if pt == ht:
            return away_team
        if pt == at:
            return home_team
        return away_team if pt == ht else home_team

    def _resolve_player_name(self, player: Dict[str, Any]) -> str:
        player_obj = player.get('player') or {}
        first = player_obj.get('first_name') or ''
        last = player_obj.get('last_name') or ''
        combined = f"{first} {last}".strip()
        return player.get('player_name') or player.get('name') or combined or 'Unknown'

    def _resolve_player_id(self, player: Dict[str, Any]) -> Optional[str]:
        player_obj = player.get('player') or {}
        return player.get('player_id') or player_obj.get('id')

    def _resolve_player_team(self, player: Dict[str, Any]) -> str:
        team = player.get('team')
        if isinstance(team, str):
            return team
        if isinstance(team, dict):
            return team.get('full_name') or team.get('name') or team.get('abbreviation') or ''
        return player.get('player_team') or ''

    def _get_stat_value(self, player: Dict[str, Any], keys: Iterable[str]) -> Optional[float]:
        for key in keys:
            if key in player:
                return _to_float(player.get(key))
        return None

    def _upsert_prop(self, game: Dict[str, Any], player: Dict[str, Any], prop_type: str, value: Optional[float]):
        if value is None:
            return
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        player_name = self._resolve_player_name(player)
        player_team = self._resolve_player_team(player) or game['home_team']
        opponent_team = self._infer_opponent(player_team, game['home_team'], game['away_team'])
        player_id = self._resolve_player_id(player)

        prop_id = f"{game['game_id']}:{prop_type}:{_sanitize_player_name(player_name)}"
        now = int(time.time())

        cursor.execute(
            """
            INSERT INTO player_props (
                prop_id, game_id, date, sport, player_name, player_id,
                player_team, opponent_team, prop_type,
                over_line, under_line, over_odds, under_odds,
                actual_value, bookmaker, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, NULL, ?, NULL, ?, ?)
            ON CONFLICT(prop_id) DO UPDATE SET
                actual_value = excluded.actual_value,
                player_team = excluded.player_team,
                opponent_team = excluded.opponent_team,
                player_id = COALESCE(excluded.player_id, player_props.player_id),
                updated_at = excluded.updated_at
            """,
            (
                prop_id,
                game['game_id'],
                game['date'],
                game['sport'],
                player_name,
                player_id,
                player_team,
                opponent_team,
                prop_type,
                value,
                now,
                now,
            ),
        )

        if cursor.rowcount == 1:
            self.stats['props_inserted'] += 1
        else:
            self.stats['props_updated'] += 1

    def process_games(self):
        games = self._fetch_games()
        conn = self.db_manager.get_connection()
        total = len(games)
        print(f"Found {total} games with player_stats to backfill props")

        for idx, game in enumerate(games, 1):
            try:
                stats_blob = game['player_stats']
                if isinstance(stats_blob, str):
                    try:
                        stats = json.loads(stats_blob)
                    except json.JSONDecodeError:
                        self.stats['games_skipped'] += 1
                        continue
                else:
                    stats = stats_blob

                if not isinstance(stats, list):
                    self.stats['games_skipped'] += 1
                    continue

                for player in stats:
                    for prop_type, aliases in self.STAT_FIELD_ALIASES.items():
                        value = self._get_stat_value(player, aliases)
                        self._upsert_prop(game, player, prop_type, value)

                conn.commit()
                self.stats['games_processed'] += 1

                if idx % 100 == 0:
                    print(f"Processed {idx}/{total} games | props inserted: {self.stats['props_inserted']:,}")

            except Exception as exc:
                print(f"⚠️  Error processing game {game['game_id']}: {exc}")
                self.stats['errors'] += 1

    def summary(self):
        print("\n📊 PLAYER PROPS BACKFILL SUMMARY")
        print(f"Games processed:  {self.stats['games_processed']:,}")
        print(f"Games skipped:    {self.stats['games_skipped']:,}")
        print(f"Props inserted:   {self.stats['props_inserted']:,}")
        print(f"Props updated:    {self.stats['props_updated']:,}")
        print(f"Errors:           {self.stats['errors']:,}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Backfill player_props from games.player_stats")
    parser.add_argument('--db-path', default='data/sports_data.db', help='Path to database')
    parser.add_argument('--limit', type=int, help='Limit number of games processed')
    parser.add_argument('--sport', help='Filter by sport (e.g., NBA)')
    parser.add_argument('--season', type=int, help='Filter by season year (e.g., 2024)')

    args = parser.parse_args()

    backfill = PlayerPropsBackfill(db_path=args.db_path, limit=args.limit, sport=args.sport, season=args.season)
    backfill.process_games()
    backfill.summary()


if __name__ == '__main__':
    main()
