"""
Agent Orchestrator — execution lifecycle controller.

Orchestrates the full pipeline:
    1. Intent Understanding → QueryUnderstanding
    2. Answer Strategist → AnswerPlan
    3. Requirement Planner → List[GatherSlot]
    4. Fact Gatherer → List[GatheredFact]
    5. Quality Gate → revised AnswerPlan
    6. Execution Engine → ExecutionResult
    7. Response Composer → structured response

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

from agent.llm_client import LLMClient
from agent.answer_strategist import build_answer_plan
from agent.fact_gatherer import (
    build_data_completeness,
    compute_aggregate_quality,
    critical_inputs_filled,
    gather_facts,
    important_inputs_filled,
)
from agent.intent_understanding import understand
from agent.models import (
    AnswerPlan,
    Entity,
    EntityRole,
    ExecutionMode,
    ExecutionResult,
    GatheredFact,
    OutputPackage,
    QueryUnderstanding,
    Subject,
)
from agent.quality_gate import apply_quality_gate
from agent.requirement_planner import build_gather_list
from agent.response_composer import compose_response, compose_response_with_llm
from src.contracts.schemas import (
    GameAnalysisRequest,
    OddsInput,
    SlateAnalysisRequest,
)
from src.contracts.service import analyze_game, analyze_slate

logger = logging.getLogger("omega.agent")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class AgentConfig:
    """Runtime configuration for the agent orchestrator."""

    llm_provider: str = "anthropic"
    llm_model: str = "claude-opus-4-20250514"
    llm_api_key: str = ""

    backend_mode: str = "in_process"
    backend_url: str = "http://localhost:8000"

    max_retries: int = 2
    retry_delay_sec: float = 1.0

    cache_dir: str = ".omega_cache/agent"
    cache_ttl_sec: int = 300

    default_bankroll: float = 1000.0

    def __post_init__(self) -> None:
        if not self.llm_api_key:
            env_keys = {
                "anthropic": "ANTHROPIC_API_KEY",
                "openai": "OPENAI_API_KEY",
            }
            env_var = env_keys.get(self.llm_provider, "ANTHROPIC_API_KEY")
            self.llm_api_key = os.environ.get(env_var, "")


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
    gathers data via the provider registry, and returns structured analysis.

    Usage:
        agent = AgentOrchestrator()
        response = agent.handle_query("Who has an edge in Lakers vs Warriors tonight?")
    """

    def __init__(self, config: Optional[AgentConfig] = None) -> None:
        self.config = config or AgentConfig()
        self.cache = AgentCache(self.config.cache_dir)
        self._http_client: Optional[httpx.Client] = None
        self.llm = LLMClient(
            provider=self.config.llm_provider,
            model=self.config.llm_model,
            api_key=self.config.llm_api_key,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def handle_query(self, user_prompt: str) -> Dict[str, Any]:
        """
        Main entry point. Executes the full lifecycle pipeline.

        Returns a structured response dict (never raises).
        """
        logger.info("Agent query: %s", user_prompt[:120])
        start_time = time.time()

        # Stage 1: Intent Understanding
        try:
            understanding = understand(user_prompt, llm_client=self.llm)
        except Exception as exc:
            logger.warning("Intent understanding failed: %s", exc)
            return self._error_response(AgentError(
                code="PARSE_FAILED",
                message=str(exc),
                fallback_hint="Rephrase with a specific matchup, e.g. 'Lakers vs Warriors NBA'",
            ))

        # Stage 2: Answer Strategy
        plan = build_answer_plan(understanding)

        # Short-circuit: clarification needed
        if plan.clarification_needed:
            return {
                "type": "clarification",
                "question": plan.clarification_question,
                "metadata": {"execution_mode": "none", "duration_ms": _elapsed_ms(start_time)},
            }

        # Stage 3: Requirement Planning
        gather_slots = build_gather_list(understanding, plan)

        # Stage 4: Fact Gathering
        facts = gather_facts(gather_slots)

        # Stage 4b: Slate Expansion — expand schedule into per-game slots
        if Subject.SLATE in understanding.subjects:
            expanded_slots = self._expand_slate_slots(understanding, facts)
            if expanded_slots:
                logger.info("Slate expansion: %d additional slots", len(expanded_slots))
                expanded_facts = gather_facts(expanded_slots)
                facts.extend(expanded_facts)

        # Stage 5: Quality Gate — revise plan if data quality insufficient
        revised_plan = apply_quality_gate(plan, facts)

        # Stage 6: Execution
        execution_result = self._execute(understanding, revised_plan, facts)

        # Stage 7: Response Composition
        if self.llm.is_available():
            response = compose_response_with_llm(
                understanding, revised_plan, execution_result, facts, self.llm,
            )
        else:
            response = compose_response(understanding, revised_plan, execution_result, facts)

        elapsed = _elapsed_ms(start_time)
        response.setdefault("metadata", {})["duration_ms"] = elapsed

        # Stage 8: Audit trail (best-effort, never blocks response)
        try:
            from src.storage import get_session
            from src.storage.execution_store import record_execution

            session = get_session()
            if session is not None:
                record_execution(
                    session, user_prompt, understanding, revised_plan,
                    facts, execution_result, elapsed,
                )
                session.close()
        except Exception:
            logger.debug("Failed to record execution audit trail", exc_info=True)

        return response

    # ------------------------------------------------------------------
    # Chat API — multi-turn with progress callbacks
    # ------------------------------------------------------------------

    def handle_chat(
        self,
        user_prompt: str,
        history: Optional[List[Dict[str, Any]]] = None,
        progress_callback: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Chat-oriented entry point with conversation history and progress.

        Like ``handle_query`` but accepts conversation history for multi-turn
        context and calls ``progress_callback(stage_name)`` at each stage.
        """
        logger.info("Chat query: %s", user_prompt[:120])
        start_time = time.time()

        def _progress(stage: str) -> None:
            if progress_callback:
                try:
                    progress_callback(stage)
                except Exception:
                    pass

        # Stage 1: Intent Understanding
        _progress("intent_understanding")
        try:
            understanding = understand(user_prompt, llm_client=self.llm)
        except Exception as exc:
            logger.warning("Intent understanding failed: %s", exc)
            return self._error_response(AgentError(
                code="PARSE_FAILED",
                message=str(exc),
                fallback_hint="Rephrase with a specific matchup, e.g. 'Lakers vs Warriors NBA'",
            ))

        # Stage 2: Answer Strategy
        _progress("answer_strategy")
        plan = build_answer_plan(understanding)

        if plan.clarification_needed:
            return {
                "type": "clarification",
                "question": plan.clarification_question,
                "metadata": {"execution_mode": "none", "duration_ms": _elapsed_ms(start_time)},
            }

        # Stage 3: Requirement Planning
        _progress("requirement_planning")
        gather_slots = build_gather_list(understanding, plan)

        # Stage 4: Fact Gathering
        _progress("fact_gathering")
        facts = gather_facts(gather_slots)

        # Stage 4b: Slate Expansion — expand schedule into per-game slots
        if Subject.SLATE in understanding.subjects:
            _progress("slate_expansion")
            expanded_slots = self._expand_slate_slots(understanding, facts)
            if expanded_slots:
                logger.info("Slate expansion: %d additional slots", len(expanded_slots))
                expanded_facts = gather_facts(expanded_slots)
                facts.extend(expanded_facts)

        # Stage 5: Quality Gate
        _progress("quality_gate")
        revised_plan = apply_quality_gate(plan, facts)

        # Stage 6: Execution
        _progress("execution")
        execution_result = self._execute(understanding, revised_plan, facts)

        # Stage 7: Response Composition
        _progress("response_composition")
        if self.llm.is_available():
            response = compose_response_with_llm(
                understanding, revised_plan, execution_result, facts, self.llm,
            )
        else:
            response = compose_response(understanding, revised_plan, execution_result, facts)

        elapsed = _elapsed_ms(start_time)
        response.setdefault("metadata", {})["duration_ms"] = elapsed

        return response

    # ------------------------------------------------------------------
    # Legacy API — preserved for backward compatibility
    # ------------------------------------------------------------------

    def parse_intent(self, prompt: str) -> Dict[str, Any]:
        """Legacy intent parser. Delegates to the new understand() function."""
        understanding = understand(prompt)
        # Convert to legacy format
        home = None
        away = None
        for ent in understanding.entities:
            if ent.role.value == "home":
                home = ent.name
            elif ent.role.value in ("away", "subject"):
                away = away or ent.name
        if not home and understanding.entities:
            home = understanding.entities[0].name
        if not away and len(understanding.entities) > 1:
            away = understanding.entities[1].name

        query_type = "slate" if any(
            s.value == "slate" for s in understanding.subjects
        ) else "game"

        return {
            "type": query_type,
            "league": understanding.league or "NBA",
            "home_team": home,
            "away_team": away,
            "raw_prompt": prompt,
        }

    # ------------------------------------------------------------------
    # Execution engine dispatcher
    # ------------------------------------------------------------------

    def _execute(
        self,
        understanding: QueryUnderstanding,
        plan: AnswerPlan,
        facts: List[GatheredFact],
    ) -> ExecutionResult:
        """Execute the answer plan using the appropriate engine(s).

        Routes to:
        - Native simulation via service.py for NATIVE_SIM mode
        - Research synthesis for RESEARCH mode
        - Kelly/staking calculator for BANKROLL_CALC mode
        - Narrative-only for NARRATIVE mode
        """
        aggregate_quality = compute_aggregate_quality(facts)
        completeness = build_data_completeness(facts)

        # Determine primary execution mode
        primary_mode = plan.execution_modes[0] if plan.execution_modes else ExecutionMode.NARRATIVE

        if primary_mode in (ExecutionMode.NATIVE_SIM, ExecutionMode.MIXED):
            return self._execute_simulation(understanding, plan, facts, aggregate_quality, completeness)

        # Research / Narrative / Bankroll — no simulation
        return ExecutionResult(
            mode=primary_mode,
            simulation=None,
            edges=[],
            best_bet=None,
            research_facts=facts,
            data_quality_score=aggregate_quality,
            data_completeness=completeness,
        )

    def _execute_simulation(
        self,
        understanding: QueryUnderstanding,
        plan: AnswerPlan,
        facts: List[GatheredFact],
        aggregate_quality: float,
        completeness: Dict[str, str],
    ) -> ExecutionResult:
        """Run native simulation via the existing service layer."""
        league = understanding.league or "NBA"
        home_team = None
        away_team = None

        for ent in understanding.entities:
            if ent.role.value == "home":
                home_team = ent.name
            elif ent.role.value in ("away", "subject"):
                if away_team is None:
                    away_team = ent.name

        # Fallback entity assignment
        if not home_team and understanding.entities:
            home_team = understanding.entities[0].name
        if not away_team and len(understanding.entities) > 1:
            away_team = understanding.entities[1].name

        if not home_team or not away_team:
            return ExecutionResult(
                mode=ExecutionMode.RESEARCH,
                research_facts=facts,
                data_quality_score=aggregate_quality,
                data_completeness=completeness,
            )

        # Build team contexts from gathered facts
        home_context = self._build_team_context(facts, "home_team")
        away_context = self._build_team_context(facts, "away_team")

        # Build odds from gathered facts
        odds_input = self._build_odds_input(facts)

        try:
            request = GameAnalysisRequest(
                home_team=home_team,
                away_team=away_team,
                league=league,
                odds=odds_input,
                home_context=home_context or None,
                away_context=away_context or None,
            )

            if self.config.backend_mode == "in_process":
                result = analyze_game(request, bankroll=self.config.default_bankroll)
                result_dict = result.model_dump()
            else:
                result_dict = self._http_post("/analyze/game", request.model_dump())

            # Extract edges and best bet from service result
            edges = []
            best_bet = None
            sim_data = result_dict.get("simulation")

            if result_dict.get("best_bet"):
                best_bet = result_dict["best_bet"]

            if result_dict.get("edges"):
                edges = result_dict["edges"]

            return ExecutionResult(
                mode=ExecutionMode.NATIVE_SIM,
                simulation=sim_data,
                edges=edges,
                best_bet=best_bet,
                research_facts=facts,
                data_quality_score=aggregate_quality,
                data_completeness=completeness,
            )

        except Exception as exc:
            logger.warning("Simulation failed, falling back to research: %s", exc)
            return ExecutionResult(
                mode=ExecutionMode.RESEARCH,
                research_facts=facts,
                data_quality_score=aggregate_quality,
                data_completeness=completeness,
            )

    def _build_team_context(
        self, facts: List[GatheredFact], prefix: str
    ) -> Optional[Dict[str, Any]]:
        """Assemble a team context dict from gathered facts matching a prefix."""
        context: Dict[str, Any] = {}
        for fact in facts:
            if fact.filled and fact.result and fact.slot.key.startswith(f"{prefix}."):
                stat_key = fact.slot.key.split(".", 1)[1]
                context[stat_key] = fact.result.data.get(stat_key)
                # Also merge any extra data from the provider
                for k, v in fact.result.data.items():
                    if k not in context:
                        context[k] = v
        return context if context else None

    def _build_odds_input(self, facts: List[GatheredFact]) -> Optional[OddsInput]:
        """Build an OddsInput from gathered odds facts."""
        for fact in facts:
            if fact.filled and fact.result and fact.slot.data_type == "odds":
                data = fact.result.data
                try:
                    return OddsInput(**data)
                except Exception:
                    logger.debug("Could not build OddsInput from %s", data)
        return None

    # ------------------------------------------------------------------
    # Slate Expansion
    # ------------------------------------------------------------------

    def _expand_slate_slots(
        self,
        understanding: QueryUnderstanding,
        facts: List[GatheredFact],
    ) -> List:
        """Expand a slate query's schedule facts into per-game gather slots.

        After the initial fact gathering for a slate query, the schedule fact
        contains a list of games. This method creates per-game QueryUnderstanding
        objects with home/away entities and generates gather slots for
        odds, team stats, and injuries for each game.
        """
        from agent.requirement_planner import build_gather_list

        league = understanding.league or "NBA"
        games = []

        # Find the schedule fact with games data
        for fact in facts:
            if fact.filled and fact.result and fact.slot.data_type == "schedule":
                data = fact.result.data
                if isinstance(data, dict) and "games" in data:
                    games = data["games"]
                    break

        if not games:
            logger.debug("No games found in schedule facts for slate expansion")
            return []

        # Collect existing slot keys to avoid duplicates
        existing_keys = {f.slot.key for f in facts}

        all_expanded_slots = []
        for game in games:
            home_raw = game.get("home_team") or game.get("home", "")
            away_raw = game.get("away_team") or game.get("away", "")

            # Team values may be dicts ({"name": "...", "abbreviation": "..."})
            # or plain strings — normalize to string team names
            home = home_raw.get("name", "") if isinstance(home_raw, dict) else str(home_raw)
            away = away_raw.get("name", "") if isinstance(away_raw, dict) else str(away_raw)

            if not home or not away:
                continue

            # Build a per-game QueryUnderstanding
            game_understanding = QueryUnderstanding(
                subjects=[Subject.GAME],
                league=league,
                entities=[
                    Entity(name=home, role=EntityRole.HOME, entity_type="team"),
                    Entity(name=away, role=EntityRole.AWAY, entity_type="team"),
                ],
                goal=understanding.goal,
                wants_betting_advice=understanding.wants_betting_advice,
                tone=understanding.tone,
                raw_prompt=f"{away} @ {home} ({league})",
            )

            # Build a minimal plan for per-game data
            game_plan = AnswerPlan(
                output_packages=[OutputPackage.COMPACT_SUMMARY],
                execution_modes=[ExecutionMode.NATIVE_SIM],
                data_requirements=["odds", "team_stat", "injury"],
                minimum_confidence=0.3,
            )

            game_slots = build_gather_list(game_understanding, game_plan)

            # Filter out schedule slots (already have schedule) and duplicates
            for slot in game_slots:
                if slot.data_type == "schedule":
                    continue
                if slot.key in existing_keys:
                    continue
                existing_keys.add(slot.key)
                all_expanded_slots.append(slot)

        logger.info(
            "Slate expansion: %d games → %d new gather slots",
            len(games), len(all_expanded_slots),
        )
        return all_expanded_slots

    # ------------------------------------------------------------------
    # HTTP backend
    # ------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _elapsed_ms(start: float) -> int:
    return int((time.time() - start) * 1000)
