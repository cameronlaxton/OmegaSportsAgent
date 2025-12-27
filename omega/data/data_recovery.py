"""
Data Recovery Service

Orchestrates data fetching with a "NEVER GIVE UP" fallback chain.
Fallback order: ESPN -> BBRef -> NBA.com Stats API -> Perplexity -> Last Known Good

CRITICAL POLICY: 
- ALWAYS prefer stale real data over no data
- NEVER return None unless entity has never been seen before
- Log data source for every stat returned
"""

from __future__ import annotations
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

from omega.data.stats_ingestion import (
    TeamContext, PlayerContext,
    _get_espn_team_stats_direct,
    get_team_ratings_from_perplexity,
    get_player_stats_from_perplexity,
    LEAGUE_BASELINES
)
from omega.data import stats_scraper
from omega.data import nba_stats_api
from omega.data import last_known_good

logger = logging.getLogger(__name__)

DATA_INTEGRITY_LOG_PATH = "data/logs/data_integrity_log.json"


def _ensure_log_dir() -> None:
    """Ensure log directory exists."""
    os.makedirs(os.path.dirname(DATA_INTEGRITY_LOG_PATH), exist_ok=True)


def _log_to_integrity_file(entry: Dict[str, Any]) -> None:
    """Append an entry to the data integrity log file."""
    try:
        _ensure_log_dir()
        
        entries = []
        if os.path.exists(DATA_INTEGRITY_LOG_PATH):
            try:
                with open(DATA_INTEGRITY_LOG_PATH, 'r') as f:
                    entries = json.load(f)
            except (json.JSONDecodeError, IOError):
                entries = []
        
        entries.append(entry)
        
        if len(entries) > 1000:
            entries = entries[-1000:]
        
        with open(DATA_INTEGRITY_LOG_PATH, 'w') as f:
            json.dump(entries, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to write to data integrity log: {e}")


class DataRecoveryService:
    """
    NEVER GIVE UP Data Recovery Service
    
    Orchestrates data fetching with fallback chain:
    ESPN -> BBRef -> NBA.com Stats API -> Perplexity -> Last Known Good
    
    This service ensures data integrity by:
    1. Trying multiple sources in priority order
    2. Using Last Known Good (stale) data when all live sources fail
    3. ONLY returning None if entity has NEVER been seen before
    4. Logging all recovery attempts for audit trail
    5. Tracking data provenance (which source provided each stat)
    """
    
    def __init__(self):
        self._recovery_stats = {
            "espn_success": 0,
            "bbref_success": 0,
            "nba_stats_success": 0,
            "perplexity_success": 0,
            "last_known_good_success": 0,
            "total_failures": 0
        }
    
    def log_recovery_attempt(
        self, 
        source: str, 
        success: bool, 
        entity: str, 
        entity_type: str,
        reason: str,
        data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log a data recovery attempt for audit trail.
        
        Args:
            source: Data source tried (espn, bbref, perplexity)
            success: Whether the attempt succeeded
            entity: Entity name (team or player name)
            entity_type: 'team' or 'player'
            reason: Reason for success/failure
            data: Optional data retrieved (for successful attempts)
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "success": success,
            "entity": entity,
            "entity_type": entity_type,
            "reason": reason,
            "data_retrieved": data is not None
        }
        
        logger.info(f"Recovery attempt: {source} for {entity_type} '{entity}' - {'SUCCESS' if success else 'FAILED'}: {reason}")
        _log_to_integrity_file(entry)
        
        if success:
            if source == "espn":
                self._recovery_stats["espn_success"] += 1
            elif source == "bbref":
                self._recovery_stats["bbref_success"] += 1
            elif source == "nba_stats_api":
                self._recovery_stats["nba_stats_success"] += 1
            elif source == "perplexity":
                self._recovery_stats["perplexity_success"] += 1
            elif source == "last_known_good":
                self._recovery_stats["last_known_good_success"] += 1
    
    def log_skipped_bet(
        self,
        entity: str,
        entity_type: str,
        reason: str,
        sources_tried: List[str]
    ) -> None:
        """
        Log when a bet is skipped due to incomplete data.
        
        Args:
            entity: Entity name
            entity_type: 'team' or 'player'
            reason: Reason for skipping
            sources_tried: List of sources that were attempted
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "skipped_bet",
            "entity": entity,
            "entity_type": entity_type,
            "reason": reason,
            "sources_tried": sources_tried
        }
        
        logger.warning(f"SKIPPED BET: {entity_type} '{entity}' - {reason} (tried: {', '.join(sources_tried)})")
        _log_to_integrity_file(entry)
        self._recovery_stats["total_failures"] += 1
    
    def log_validation_failure(
        self,
        entity: str,
        entity_type: str,
        issues: List[str]
    ) -> None:
        """
        Log when data validation fails.
        
        Args:
            entity: Entity name
            entity_type: 'team' or 'player'
            issues: List of validation issues
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "validation_failure",
            "entity": entity,
            "entity_type": entity_type,
            "issues": issues
        }
        
        logger.warning(f"VALIDATION FAILURE: {entity_type} '{entity}' - Issues: {', '.join(issues)}")
        _log_to_integrity_file(entry)
    
    def get_team_stats(self, team_name: str, league: str) -> Optional[TeamContext]:
        """
        NEVER GIVE UP: Try each data source in order.
        
        Fallback chain: ESPN -> BBRef -> NBA.com Stats API -> Perplexity -> Last Known Good
        
        ONLY returns None if team has NEVER been seen before.
        
        Args:
            team_name: Team name to look up
            league: League code (NBA, NFL, etc.)
        
        Returns:
            TeamContext with real data (may be stale), or None only if never seen
        """
        sources_tried = []
        
        espn_data = self._try_espn_team(team_name, league)
        sources_tried.append("espn")
        if espn_data:
            last_known_good.save_team_data(team_name, league, espn_data.to_dict(), "espn")
            return espn_data
        
        bbref_data = self._try_bbref_team(team_name, league)
        sources_tried.append("bbref")
        if bbref_data:
            last_known_good.save_team_data(team_name, league, bbref_data.to_dict(), "bbref")
            return bbref_data
        
        if league.upper() == "NBA":
            nba_stats_data = self._try_nba_stats_team(team_name)
            sources_tried.append("nba_stats_api")
            if nba_stats_data:
                last_known_good.save_team_data(team_name, league, nba_stats_data.to_dict(), "nba_stats_api")
                return nba_stats_data
        
        perplexity_data = self._try_perplexity_team(team_name, league)
        sources_tried.append("perplexity")
        if perplexity_data:
            last_known_good.save_team_data(team_name, league, perplexity_data.to_dict(), "perplexity")
            return perplexity_data
        
        lkg_data = self._try_last_known_good_team(team_name, league)
        sources_tried.append("last_known_good")
        if lkg_data:
            return lkg_data
        
        self.log_skipped_bet(
            entity=team_name,
            entity_type="team",
            reason="NEVER GIVE UP FAILED: Team has never been seen before",
            sources_tried=sources_tried
        )
        
        return None
    
    def get_player_stats(self, player_name: str, team: str, league: str) -> Optional[PlayerContext]:
        """
        NEVER GIVE UP: Try each data source in order.
        
        Fallback chain: ESPN -> BBRef -> Perplexity -> Last Known Good
        
        ONLY returns None if player has NEVER been seen before.
        
        Args:
            player_name: Player name to look up
            team: Team name
            league: League code
        
        Returns:
            PlayerContext with real data (may be stale), or None only if never seen
        """
        sources_tried = []
        
        espn_data = self._try_espn_player(player_name, team, league)
        sources_tried.append("espn")
        if espn_data:
            last_known_good.save_player_data(player_name, league, espn_data.to_dict(), "espn")
            return espn_data
        
        bbref_data = self._try_bbref_player(player_name, league)
        sources_tried.append("bbref")
        if bbref_data:
            last_known_good.save_player_data(player_name, league, bbref_data.to_dict(), "bbref")
            return bbref_data
        
        perplexity_data = self._try_perplexity_player(player_name, league)
        sources_tried.append("perplexity")
        if perplexity_data:
            last_known_good.save_player_data(player_name, league, perplexity_data.to_dict(), "perplexity")
            return perplexity_data
        
        lkg_data = self._try_last_known_good_player(player_name, league)
        sources_tried.append("last_known_good")
        if lkg_data:
            return lkg_data
        
        self.log_skipped_bet(
            entity=player_name,
            entity_type="player",
            reason="NEVER GIVE UP FAILED: Player has never been seen before",
            sources_tried=sources_tried
        )
        
        return None
    
    def _try_espn_team(self, team_name: str, league: str) -> Optional[TeamContext]:
        """Try to get team stats from ESPN."""
        try:
            data = _get_espn_team_stats_direct(team_name, league)
            
            if not data:
                self.log_recovery_attempt(
                    source="espn",
                    success=False,
                    entity=team_name,
                    entity_type="team",
                    reason="No data returned from ESPN API"
                )
                return None
            
            stats = data.get("stats", {})
            off_rating = stats.get("off_rating") or stats.get("offensive_rating")
            def_rating = stats.get("def_rating") or stats.get("defensive_rating")
            pace = stats.get("pace")
            
            if not self._validate_team_values(off_rating, def_rating, pace, league):
                self.log_recovery_attempt(
                    source="espn",
                    success=False,
                    entity=team_name,
                    entity_type="team",
                    reason=f"ESPN data incomplete: off={off_rating}, def={def_rating}, pace={pace}"
                )
                return None
            
            context = TeamContext(
                name=data.get("name", team_name),
                league=league.upper(),
                off_rating=float(off_rating),
                def_rating=float(def_rating),
                pace=float(pace),
                pts_per_game=float(stats.get("pts_per_game", 0) or 0),
                fg_pct=float(stats.get("fg_pct", 0) or 0),
                three_pt_pct=float(stats.get("three_pt_pct", 0) or 0)
            )
            
            self.log_recovery_attempt(
                source="espn",
                success=True,
                entity=team_name,
                entity_type="team",
                reason="Successfully retrieved team stats",
                data=context.to_dict()
            )
            
            return context
            
        except Exception as e:
            self.log_recovery_attempt(
                source="espn",
                success=False,
                entity=team_name,
                entity_type="team",
                reason=f"ESPN error: {str(e)}"
            )
            return None
    
    def _try_bbref_team(self, team_name: str, league: str) -> Optional[TeamContext]:
        """Try to get team stats from Basketball Reference."""
        try:
            data = stats_scraper.get_team_stats(team_name, league)
            
            if not data:
                self.log_recovery_attempt(
                    source="bbref",
                    success=False,
                    entity=team_name,
                    entity_type="team",
                    reason="No data returned from BBRef scraper"
                )
                return None
            
            off_rating = data.get("off_rating") or data.get("offensive_rating")
            def_rating = data.get("def_rating") or data.get("defensive_rating")
            pace = data.get("pace")
            
            if not self._validate_team_values(off_rating, def_rating, pace, league):
                self.log_recovery_attempt(
                    source="bbref",
                    success=False,
                    entity=team_name,
                    entity_type="team",
                    reason=f"BBRef data incomplete: off={off_rating}, def={def_rating}, pace={pace}"
                )
                return None
            
            assert off_rating is not None and def_rating is not None and pace is not None
            
            context = TeamContext(
                name=team_name,
                league=league.upper(),
                off_rating=float(off_rating),
                def_rating=float(def_rating),
                pace=float(pace),
                pts_per_game=float(data.get("pts_per_game", 0) or 0),
                fg_pct=float(data.get("fg_pct", 0) or 0),
                three_pt_pct=float(data.get("three_pt_pct", 0) or 0)
            )
            
            self.log_recovery_attempt(
                source="bbref",
                success=True,
                entity=team_name,
                entity_type="team",
                reason="Successfully retrieved team stats from BBRef",
                data=context.to_dict()
            )
            
            return context
            
        except Exception as e:
            self.log_recovery_attempt(
                source="bbref",
                success=False,
                entity=team_name,
                entity_type="team",
                reason=f"BBRef error: {str(e)}"
            )
            return None
    
    def _try_perplexity_team(self, team_name: str, league: str) -> Optional[TeamContext]:
        """Try to get team stats from Perplexity AI."""
        try:
            data = get_team_ratings_from_perplexity(team_name, league)
            
            if not data:
                self.log_recovery_attempt(
                    source="perplexity",
                    success=False,
                    entity=team_name,
                    entity_type="team",
                    reason="No data returned from Perplexity"
                )
                return None
            
            if data.get("source") == "league_baseline":
                self.log_recovery_attempt(
                    source="perplexity",
                    success=False,
                    entity=team_name,
                    entity_type="team",
                    reason="Perplexity returned league baseline (not real data)"
                )
                return None
            
            off_rating = data.get("off_rating")
            def_rating = data.get("def_rating")
            pace = data.get("pace")
            
            if not self._validate_team_values(off_rating, def_rating, pace, league):
                self.log_recovery_attempt(
                    source="perplexity",
                    success=False,
                    entity=team_name,
                    entity_type="team",
                    reason=f"Perplexity data incomplete: off={off_rating}, def={def_rating}, pace={pace}"
                )
                return None
            
            assert off_rating is not None and def_rating is not None and pace is not None
            
            context = TeamContext(
                name=team_name,
                league=league.upper(),
                off_rating=float(off_rating),
                def_rating=float(def_rating),
                pace=float(pace),
                pts_per_game=0.0,
                fg_pct=0.0,
                three_pt_pct=0.0
            )
            
            self.log_recovery_attempt(
                source="perplexity",
                success=True,
                entity=team_name,
                entity_type="team",
                reason="Successfully retrieved team stats from Perplexity",
                data=context.to_dict()
            )
            
            return context
            
        except Exception as e:
            self.log_recovery_attempt(
                source="perplexity",
                success=False,
                entity=team_name,
                entity_type="team",
                reason=f"Perplexity error: {str(e)}"
            )
            return None
    
    def _try_espn_player(self, player_name: str, team: str, league: str) -> Optional[PlayerContext]:
        """Try to get player stats from ESPN."""
        try:
            data = stats_scraper.get_player_stats(player_name, league)
            
            if not data:
                self.log_recovery_attempt(
                    source="espn",
                    success=False,
                    entity=player_name,
                    entity_type="player",
                    reason="No data returned from ESPN"
                )
                return None
            
            pts_mean = data.get("pts_mean") or data.get("points")
            reb_mean = data.get("reb_mean") or data.get("rebounds")
            ast_mean = data.get("ast_mean") or data.get("assists")
            
            if not self._validate_player_values(pts_mean, reb_mean, ast_mean):
                self.log_recovery_attempt(
                    source="espn",
                    success=False,
                    entity=player_name,
                    entity_type="player",
                    reason=f"ESPN data incomplete: pts={pts_mean}, reb={reb_mean}, ast={ast_mean}"
                )
                return None
            
            assert pts_mean is not None and reb_mean is not None and ast_mean is not None
            
            context = PlayerContext(
                name=player_name,
                team=team,
                position=data.get("position", ""),
                usage_rate=float(data.get("usage_rate", 0.15) or 0.15),
                pts_mean=float(pts_mean),
                pts_std=float(pts_mean) * 0.25,
                reb_mean=float(reb_mean),
                reb_std=float(reb_mean) * 0.25,
                ast_mean=float(ast_mean),
                ast_std=float(ast_mean) * 0.25
            )
            
            self.log_recovery_attempt(
                source="espn",
                success=True,
                entity=player_name,
                entity_type="player",
                reason="Successfully retrieved player stats",
                data=context.to_dict()
            )
            
            return context
            
        except Exception as e:
            self.log_recovery_attempt(
                source="espn",
                success=False,
                entity=player_name,
                entity_type="player",
                reason=f"ESPN error: {str(e)}"
            )
            return None
    
    def _try_bbref_player(self, player_name: str, league: str) -> Optional[PlayerContext]:
        """Try to get player stats from Basketball Reference."""
        try:
            data = stats_scraper.get_player_stats(player_name, league)
            
            if not data:
                self.log_recovery_attempt(
                    source="bbref",
                    success=False,
                    entity=player_name,
                    entity_type="player",
                    reason="No data returned from BBRef scraper"
                )
                return None
            
            pts_mean = data.get("pts_mean") or data.get("points") or data.get("ppg")
            reb_mean = data.get("reb_mean") or data.get("rebounds") or data.get("rpg")
            ast_mean = data.get("ast_mean") or data.get("assists") or data.get("apg")
            
            if not self._validate_player_values(pts_mean, reb_mean, ast_mean):
                self.log_recovery_attempt(
                    source="bbref",
                    success=False,
                    entity=player_name,
                    entity_type="player",
                    reason=f"BBRef data incomplete: pts={pts_mean}, reb={reb_mean}, ast={ast_mean}"
                )
                return None
            
            assert pts_mean is not None and reb_mean is not None and ast_mean is not None
            
            context = PlayerContext(
                name=player_name,
                team=data.get("team", ""),
                position=data.get("position", ""),
                usage_rate=float(data.get("usage_rate", 0.15) or 0.15),
                pts_mean=float(pts_mean),
                pts_std=float(pts_mean) * 0.25,
                reb_mean=float(reb_mean),
                reb_std=float(reb_mean) * 0.25,
                ast_mean=float(ast_mean),
                ast_std=float(ast_mean) * 0.25
            )
            
            self.log_recovery_attempt(
                source="bbref",
                success=True,
                entity=player_name,
                entity_type="player",
                reason="Successfully retrieved player stats from BBRef",
                data=context.to_dict()
            )
            
            return context
            
        except Exception as e:
            self.log_recovery_attempt(
                source="bbref",
                success=False,
                entity=player_name,
                entity_type="player",
                reason=f"BBRef error: {str(e)}"
            )
            return None
    
    def _try_perplexity_player(self, player_name: str, league: str) -> Optional[PlayerContext]:
        """Try to get player stats from Perplexity AI."""
        try:
            data = get_player_stats_from_perplexity(player_name, league)
            
            if not data:
                self.log_recovery_attempt(
                    source="perplexity",
                    success=False,
                    entity=player_name,
                    entity_type="player",
                    reason="No data returned from Perplexity"
                )
                return None
            
            if data.get("source") == "baseline":
                self.log_recovery_attempt(
                    source="perplexity",
                    success=False,
                    entity=player_name,
                    entity_type="player",
                    reason="Perplexity returned baseline stats (not real data)"
                )
                return None
            
            pts_mean = data.get("pts_mean")
            reb_mean = data.get("reb_mean")
            ast_mean = data.get("ast_mean")
            
            if not self._validate_player_values(pts_mean, reb_mean, ast_mean):
                self.log_recovery_attempt(
                    source="perplexity",
                    success=False,
                    entity=player_name,
                    entity_type="player",
                    reason=f"Perplexity data incomplete: pts={pts_mean}, reb={reb_mean}, ast={ast_mean}"
                )
                return None
            
            assert pts_mean is not None and reb_mean is not None and ast_mean is not None
            
            context = PlayerContext(
                name=player_name,
                team="",
                position="",
                usage_rate=0.15,
                pts_mean=float(pts_mean),
                pts_std=float(pts_mean) * 0.25,
                reb_mean=float(reb_mean),
                reb_std=float(reb_mean) * 0.25,
                ast_mean=float(ast_mean),
                ast_std=float(ast_mean) * 0.25
            )
            
            self.log_recovery_attempt(
                source="perplexity",
                success=True,
                entity=player_name,
                entity_type="player",
                reason="Successfully retrieved player stats from Perplexity",
                data=context.to_dict()
            )
            
            return context
            
        except Exception as e:
            self.log_recovery_attempt(
                source="perplexity",
                success=False,
                entity=player_name,
                entity_type="player",
                reason=f"Perplexity error: {str(e)}"
            )
            return None
    
    def _try_nba_stats_team(self, team_name: str) -> Optional[TeamContext]:
        """Try to get team stats from NBA.com Stats API."""
        try:
            data = nba_stats_api.get_team_advanced_stats(team_name)
            
            if not data:
                self.log_recovery_attempt(
                    source="nba_stats_api",
                    success=False,
                    entity=team_name,
                    entity_type="team",
                    reason="No data returned from NBA.com Stats API"
                )
                return None
            
            off_rating = data.get("off_rating")
            def_rating = data.get("def_rating")
            pace = data.get("pace")
            
            if not self._validate_team_values(off_rating, def_rating, pace, "NBA"):
                self.log_recovery_attempt(
                    source="nba_stats_api",
                    success=False,
                    entity=team_name,
                    entity_type="team",
                    reason=f"NBA.com data incomplete: off={off_rating}, def={def_rating}, pace={pace}"
                )
                return None
            
            basic_stats = nba_stats_api.get_team_basic_stats(team_name) or {}
            
            context = TeamContext(
                name=team_name,
                league="NBA",
                off_rating=float(off_rating),
                def_rating=float(def_rating),
                pace=float(pace),
                pts_per_game=float(basic_stats.get("pts_per_game", 0) or 0),
                fg_pct=float(basic_stats.get("fg_pct", 0) or 0),
                three_pt_pct=float(basic_stats.get("three_pt_pct", 0) or 0)
            )
            
            self.log_recovery_attempt(
                source="nba_stats_api",
                success=True,
                entity=team_name,
                entity_type="team",
                reason="Successfully retrieved team stats from NBA.com Stats API",
                data=context.to_dict()
            )
            
            return context
            
        except Exception as e:
            self.log_recovery_attempt(
                source="nba_stats_api",
                success=False,
                entity=team_name,
                entity_type="team",
                reason=f"NBA.com Stats API error: {str(e)}"
            )
            return None
    
    def _try_last_known_good_team(self, team_name: str, league: str) -> Optional[TeamContext]:
        """Try to get team stats from Last Known Good storage."""
        try:
            data = last_known_good.load_team_data(team_name, league)
            
            if not data:
                self.log_recovery_attempt(
                    source="last_known_good",
                    success=False,
                    entity=team_name,
                    entity_type="team",
                    reason="No Last Known Good data available"
                )
                return None
            
            off_rating = data.get("off_rating")
            def_rating = data.get("def_rating")
            pace = data.get("pace")
            
            if not off_rating or not def_rating or not pace:
                self.log_recovery_attempt(
                    source="last_known_good",
                    success=False,
                    entity=team_name,
                    entity_type="team",
                    reason="Last Known Good data is incomplete"
                )
                return None
            
            context = TeamContext(
                name=data.get("team_name", team_name),
                league=league.upper(),
                off_rating=float(off_rating),
                def_rating=float(def_rating),
                pace=float(pace),
                pts_per_game=float(data.get("pts_per_game", 0) or 0),
                fg_pct=float(data.get("fg_pct", 0) or 0),
                three_pt_pct=float(data.get("three_pt_pct", 0) or 0)
            )
            
            stale_hours = data.get("stale_hours", "unknown")
            self.log_recovery_attempt(
                source="last_known_good",
                success=True,
                entity=team_name,
                entity_type="team",
                reason=f"Using STALE data (age: {stale_hours} hours) - better than nothing!",
                data=context.to_dict()
            )
            
            return context
            
        except Exception as e:
            self.log_recovery_attempt(
                source="last_known_good",
                success=False,
                entity=team_name,
                entity_type="team",
                reason=f"Last Known Good error: {str(e)}"
            )
            return None
    
    def _try_last_known_good_player(self, player_name: str, league: str) -> Optional[PlayerContext]:
        """Try to get player stats from Last Known Good storage."""
        try:
            data = last_known_good.load_player_data(player_name, league)
            
            if not data:
                self.log_recovery_attempt(
                    source="last_known_good",
                    success=False,
                    entity=player_name,
                    entity_type="player",
                    reason="No Last Known Good data available"
                )
                return None
            
            pts_mean = data.get("pts_mean")
            
            if not pts_mean:
                self.log_recovery_attempt(
                    source="last_known_good",
                    success=False,
                    entity=player_name,
                    entity_type="player",
                    reason="Last Known Good data is incomplete"
                )
                return None
            
            context = PlayerContext(
                name=data.get("player_name", player_name),
                team=data.get("team", ""),
                position=data.get("position", ""),
                usage_rate=float(data.get("usage_rate", 0.15) or 0.15),
                pts_mean=float(pts_mean),
                pts_std=float(data.get("pts_std", pts_mean * 0.25) or pts_mean * 0.25),
                reb_mean=float(data.get("reb_mean", 0) or 0),
                reb_std=float(data.get("reb_std", 0) or 0),
                ast_mean=float(data.get("ast_mean", 0) or 0),
                ast_std=float(data.get("ast_std", 0) or 0)
            )
            
            stale_hours = data.get("stale_hours", "unknown")
            self.log_recovery_attempt(
                source="last_known_good",
                success=True,
                entity=player_name,
                entity_type="player",
                reason=f"Using STALE data (age: {stale_hours} hours) - better than nothing!",
                data=context.to_dict()
            )
            
            return context
            
        except Exception as e:
            self.log_recovery_attempt(
                source="last_known_good",
                success=False,
                entity=player_name,
                entity_type="player",
                reason=f"Last Known Good error: {str(e)}"
            )
            return None
    
    def _validate_team_values(
        self, 
        off_rating: Optional[float], 
        def_rating: Optional[float], 
        pace: Optional[float],
        league: str
    ) -> bool:
        """Validate that team values are present and reasonable."""
        if off_rating is None or def_rating is None or pace is None:
            return False
        
        try:
            off = float(off_rating)
            def_ = float(def_rating)
            p = float(pace)
            
            if off <= 0 or def_ <= 0 or p <= 0:
                return False
            
            if league.upper() == "NBA":
                if off < 90 or off > 140:
                    return False
                if def_ < 90 or def_ > 140:
                    return False
                if p < 85 or p > 115:
                    return False
            
            return True
        except (ValueError, TypeError):
            return False
    
    def _validate_player_values(
        self,
        pts_mean: Optional[float],
        reb_mean: Optional[float],
        ast_mean: Optional[float]
    ) -> bool:
        """Validate that player values are present and reasonable."""
        if pts_mean is None:
            return False
        
        try:
            pts = float(pts_mean)
            if pts <= 0:
                return False
            return True
        except (ValueError, TypeError):
            return False
    
    def get_recovery_stats(self) -> Dict[str, int]:
        """Get statistics about recovery attempts."""
        return self._recovery_stats.copy()


_service_instance: Optional[DataRecoveryService] = None


def get_recovery_service() -> DataRecoveryService:
    """Get singleton instance of DataRecoveryService."""
    global _service_instance
    if _service_instance is None:
        _service_instance = DataRecoveryService()
    return _service_instance
