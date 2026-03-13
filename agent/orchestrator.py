"""
Agent Orchestrator — browsing-capable LLM that bridges natural language
to the OmegaSportsAgent engine.

Flow:
    1. Parse natural-language prompt → identify league, teams, markets
    2. Use LLM web search/fetch to gather odds + public stats
    3. Normalize into engine schemas (GameAnalysisRequest)
    4. Call the backend service (in-process or via HTTP)
    5. Handle errors with structured retries / fallbacks
    6. Return strict JSON (GameAnalysisResponse) for the frontend

This module is the ONLY place that fetches live data. The engine and
service layers are input-driven and never make network calls.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from src.contracts.schemas import (
    ErrorResponse,
    GameAnalysisRequest,
    GameAnalysisResponse,
    OddsInput,
    SlateAnalysisRequest,
    SlateAnalysisResponse,
)
from src.contracts.service import analyze_game, analyze_slate
from src.simulation.sport_archetypes import (
    get_archetype,
    get_required_inputs,
    LEAGUE_TO_ARCHETYPE,
)

logger = logging.getLogger("omega.agent")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class AgentConfig:
    """Runtime configuration for the agent orchestrator."""

    # LLM provider settings (Claude, OpenAI, local, etc.)
    llm_provider: str = "anthropic"  # "anthropic", "openai", "local"
    llm_model: str = "claude-sonnet-4-20250514"
    llm_api_key: str = ""  # Set from env

    # Backend mode: "in_process" calls service.py directly (no HTTP);
    # "http" calls the FastAPI server.
    backend_mode: str = "in_process"
    backend_url: str = "http://localhost:8000"

    # Retry / error handling
    max_retries: int = 2
    retry_delay_sec: float = 1.0

    # Cache
    cache_dir: str = ".omega_cache/agent"
    cache_ttl_sec: int = 300  # 5 minutes for odds, 3600 for stats

    # Bankroll default
    default_bankroll: float = 1000.0

    def __post_init__(self) -> None:
        if not self.llm_api_key:
            self.llm_api_key = os.environ.get("ANTHROPIC_API_KEY", "")


# ---------------------------------------------------------------------------
# Structured error model
# ---------------------------------------------------------------------------

@dataclass
class AgentError:
    """Structured error with context for the LLM to decide next action."""

    code: str  # PARSE_FAILED, DATA_MISSING, SIM_FAILED, NETWORK_ERROR
    message: str
    context: Dict[str, Any] = field(default_factory=dict)
    fallback_hint: Optional[str] = None
    retryable: bool = False


# ---------------------------------------------------------------------------
# Simple file-based cache
# ---------------------------------------------------------------------------

class AgentCache:
    """TTL-aware file cache to avoid redundant LLM calls and re-simulations."""

    def __init__(self, cache_dir: str = ".omega_cache/agent") -> None:
        self.cache_dir = os.path.abspath(cache_dir)
        os.makedirs(self.cache_dir, exist_ok=True)

    def _key_path(self, key: str) -> str:
        h = hashlib.sha256(key.encode()).hexdigest()[:16]
        return os.path.join(self.cache_dir, f"{h}.json")

    def get(self, key: str, ttl_sec: int = 300) -> Optional[Dict[str, Any]]:
        path = self._key_path(key)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            cached_at = payload.get("cached_at", 0)
            if time.time() - cached_at > ttl_sec:
                return None
            return payload.get("data")
        except (json.JSONDecodeError, KeyError):
            return None

    def set(self, key: str, data: Dict[str, Any]) -> None:
        path = self._key_path(key)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"key": key, "cached_at": time.time(), "data": data}, f, default=str)


# ---------------------------------------------------------------------------
# Agent Orchestrator
# ---------------------------------------------------------------------------

class AgentOrchestrator:
    """
    Stateful agent that takes natural-language betting questions,
    gathers data via web search, and returns structured analysis.

    Usage:
        agent = AgentOrchestrator()
        response = agent.handle_query("Who has an edge in Lakers vs Warriors tonight?")
    """

    def __init__(self, config: Optional[AgentConfig] = None) -> None:
        self.config = config or AgentConfig()
        self.cache = AgentCache(self.config.cache_dir)
        self._http_client: Optional[httpx.Client] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def handle_query(self, user_prompt: str) -> Dict[str, Any]:
        """
        Main entry point. Takes a natural-language prompt and returns
        a dict compatible with GameAnalysisResponse or SlateAnalysisResponse.

        Returns error dict on failure (never raises).
        """
        logger.info("Agent query: %s", user_prompt[:120])

        # Step 1: Parse intent
        intent = self.parse_intent(user_prompt)
        if intent.get("error"):
            return self._error_response(AgentError(
                code="PARSE_FAILED",
                message=intent["error"],
                fallback_hint="Rephrase with a specific matchup, e.g. 'Lakers vs Warriors NBA'",
            ))

        query_type = intent.get("type", "game")
        league = intent.get("league", "NBA")

        # Step 2: Gather data (odds + stats) — web search or cache
        try:
            data = self.gather_data(intent)
        except Exception as exc:
            logger.warning("Data gathering failed: %s", exc)
            return self._error_response(AgentError(
                code="DATA_MISSING",
                message=str(exc),
                fallback_hint="Try providing odds manually or check team name spelling",
                retryable=True,
            ))

        # Step 3: Build engine request and call backend
        for attempt in range(1 + self.config.max_retries):
            try:
                if query_type == "slate":
                    result = self._run_slate(intent, data)
                else:
                    result = self._run_game(intent, data)

                # Check for missing_requirements → try to self-heal
                missing = result.get("missing_requirements") or []
                if missing and attempt < self.config.max_retries:
                    logger.info("Missing requirements %s, re-fetching...", missing)
                    data = self._fill_missing(data, missing, intent)
                    continue

                return result

            except Exception as exc:
                logger.warning("Attempt %d failed: %s", attempt + 1, exc)
                if attempt < self.config.max_retries:
                    time.sleep(self.config.retry_delay_sec)
                    continue
                return self._error_response(AgentError(
                    code="SIM_FAILED",
                    message=str(exc),
                    fallback_hint="Engine simulation error — check input data",
                ))

        return self._error_response(AgentError(
            code="MAX_RETRIES",
            message="All retry attempts exhausted",
        ))

    # ------------------------------------------------------------------
    # Intent parsing (rule-based; LLM-assisted in production)
    # ------------------------------------------------------------------

    def parse_intent(self, prompt: str) -> Dict[str, Any]:
        """
        Parse a natural-language prompt into structured intent.

        Returns dict with: type, league, home_team, away_team, etc.
        In production this would call the LLM; here we use heuristics
        with fallback to LLM when available.
        """
        prompt_lower = prompt.lower().strip()

        # Detect league
        league = self._detect_league(prompt_lower)

        # Detect query type
        query_type = "game"
        if any(kw in prompt_lower for kw in ["slate", "all games", "today's games", "full card"]):
            query_type = "slate"

        # Extract team names (heuristic: "X vs Y" or "X at Y")
        home, away = self._extract_teams(prompt)

        if query_type == "game" and (not home or not away):
            return {"error": "Could not identify two teams. Try: 'Lakers vs Warriors NBA'"}

        return {
            "type": query_type,
            "league": league,
            "home_team": home,
            "away_team": away,
            "raw_prompt": prompt,
        }

    def _detect_league(self, text: str) -> str:
        """Detect league from text. Returns uppercase league code."""
        league_keywords = {
            "NBA": ["nba", "basketball"],
            "NFL": ["nfl", "football"],
            "MLB": ["mlb", "baseball"],
            "NHL": ["nhl", "hockey"],
            "EPL": ["epl", "premier league", "soccer", "football club"],
            "UFC": ["ufc", "mma", "fighting"],
            "ATP": ["atp", "tennis"],
            "PGA": ["pga", "golf"],
            "CS2": ["cs2", "csgo", "counter-strike", "esports"],
            "NCAAB": ["ncaab", "march madness", "college basketball"],
            "NCAAF": ["ncaaf", "college football"],
        }
        for league, keywords in league_keywords.items():
            for kw in keywords:
                if kw in text:
                    return league
        return "NBA"  # default

    def _extract_teams(self, prompt: str) -> tuple:
        """Extract home/away teams from prompt. Returns (home, away) or (None, None)."""
        import re

        # Try "X vs Y", "X versus Y", "X at Y", "X @ Y"
        patterns = [
            r"(.+?)\s+(?:vs\.?|versus|v\.?)\s+(.+?)(?:\s+(?:nba|nfl|mlb|nhl|epl|ufc|atp|pga|cs2|ncaab|ncaaf)|\s*$)",
            r"(.+?)\s+(?:at|@)\s+(.+?)(?:\s+(?:nba|nfl|mlb|nhl|epl|ufc|atp|pga|cs2|ncaab|ncaaf)|\s*$)",
        ]

        for pattern in patterns:
            match = re.search(pattern, prompt, re.IGNORECASE)
            if match:
                team_a = match.group(1).strip().strip('"\'')
                team_b = match.group(2).strip().strip('"\'')
                # "A vs B" → A=away, B=home (conventional); "A at B" → A=away, B=home
                return team_b, team_a

        return None, None

    # ------------------------------------------------------------------
    # Data gathering (stub for web search — plug in LLM provider)
    # ------------------------------------------------------------------

    def gather_data(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gather odds and stats for the intent.

        In production, this calls:
          - LLM with web_search tool to get current odds
          - LLM with web_search tool to get team stats
          - Normalizes everything into engine-compatible dicts

        For now, returns a minimal structure that the engine can work with
        using archetype defaults.
        """
        league = intent.get("league", "NBA")
        home = intent.get("home_team", "")
        away = intent.get("away_team", "")

        cache_key = f"data:{league}:{home}:{away}:{datetime.now().strftime('%Y-%m-%d')}"
        cached = self.cache.get(cache_key, ttl_sec=self.config.cache_ttl_sec)
        if cached:
            logger.info("Cache hit for %s vs %s", away, home)
            return cached

        # Try to fetch via the data layer modules
        data: Dict[str, Any] = {
            "home_context": None,
            "away_context": None,
            "odds": None,
        }

        # Attempt to use free data sources
        data["home_context"] = self._fetch_team_context(home, league)
        data["away_context"] = self._fetch_team_context(away, league)
        data["odds"] = self._fetch_odds(home, away, league)

        self.cache.set(cache_key, data)
        return data

    def _fetch_team_context(self, team: str, league: str) -> Optional[Dict[str, Any]]:
        """Fetch team context. Tries free sources, then falls back to LLM web search."""
        # Try in-repo free sources first
        try:
            from src.data.free_sources import get_team_stats_free
            stats = get_team_stats_free(team, league)
            if stats:
                return stats
        except (ImportError, Exception) as exc:
            logger.debug("free_sources unavailable: %s", exc)

        # Fallback: LLM web search would go here
        # For now, return None (engine will report missing_requirements)
        return None

    def _fetch_odds(self, home: str, away: str, league: str) -> Optional[Dict[str, Any]]:
        """Fetch odds. Tries free sources, then falls back to LLM web search."""
        try:
            from src.data.free_sources import get_odds_free
            odds = get_odds_free(home, away, league)
            if odds:
                return odds
        except (ImportError, Exception) as exc:
            logger.debug("free_sources odds unavailable: %s", exc)
        return None

    def _fill_missing(
        self, data: Dict[str, Any], missing: List[str], intent: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Try to fill missing requirements by re-fetching specific fields."""
        # In production, the LLM would be asked to specifically search for
        # the missing keys (e.g. "home_context.off_rating for Lakers NBA").
        # For now, just return data unchanged.
        logger.info("Would re-fetch missing: %s", missing)
        return data

    # ------------------------------------------------------------------
    # Backend calls
    # ------------------------------------------------------------------

    def _run_game(self, intent: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """Build a GameAnalysisRequest and call the backend."""
        odds_input = None
        if data.get("odds"):
            odds_input = OddsInput(**data["odds"])

        request = GameAnalysisRequest(
            home_team=intent["home_team"],
            away_team=intent["away_team"],
            league=intent["league"],
            odds=odds_input,
            home_context=data.get("home_context"),
            away_context=data.get("away_context"),
        )

        if self.config.backend_mode == "in_process":
            result = analyze_game(request, bankroll=self.config.default_bankroll)
            return result.model_dump()
        else:
            return self._http_post("/analyze/game", request.model_dump())

    def _run_slate(self, intent: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """Build a SlateAnalysisRequest and call the backend."""
        request = SlateAnalysisRequest(
            league=intent["league"],
            bankroll=self.config.default_bankroll,
            games=data.get("games", []),
        )

        if self.config.backend_mode == "in_process":
            result = analyze_slate(request)
            return result.model_dump()
        else:
            return self._http_post("/analyze/slate", request.model_dump())

    def _http_post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """POST to the FastAPI backend."""
        if self._http_client is None:
            self._http_client = httpx.Client(base_url=self.config.backend_url, timeout=30)
        resp = self._http_client.post(path, json=payload)
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # Error formatting
    # ------------------------------------------------------------------

    @staticmethod
    def _error_response(err: AgentError) -> Dict[str, Any]:
        """Format an AgentError into the standard error response shape."""
        return {
            "status": "error",
            "error_code": err.code,
            "message": err.message,
            "context": err.context,
            "fallback_hint": err.fallback_hint,
            "retryable": err.retryable,
        }
