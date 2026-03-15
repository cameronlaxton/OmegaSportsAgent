"""
FastAPI application for OmegaSportsAgent.

Exposes the simulation engine via JSON-in/JSON-out endpoints only.
No live data fetching; caller supplies games and context. Run: uvicorn server.app:app --reload
"""

from __future__ import annotations

import asyncio
import json
import logging
import queue
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from agent.orchestrator import AgentOrchestrator
from server.session import session_store
from src.contracts.schemas import (
    ChatMessage,
    ChatRequest,
    ErrorResponse,
    GameAnalysisRequest,
    GameAnalysisResponse,
    PlayerPropRequest,
    PlayerPropResponse,
    SlateAnalysisRequest,
    SlateAnalysisResponse,
)
from src.contracts.service import analyze_game, analyze_player_prop, analyze_slate

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("omega.server")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("OmegaSportsAgent API starting up")
    # Start periodic session pruning
    prune_task = asyncio.create_task(_prune_sessions_loop())
    yield
    prune_task.cancel()
    logger.info("OmegaSportsAgent API shutting down")


async def _prune_sessions_loop() -> None:
    """Prune expired sessions every 5 minutes."""
    while True:
        await asyncio.sleep(300)
        try:
            session_store.prune()
        except Exception:
            logger.debug("Session prune failed", exc_info=True)


# Shared orchestrator instance (lazy — only created when /chat is first called)
_orchestrator: AgentOrchestrator | None = None


def _get_orchestrator() -> AgentOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()
    return _orchestrator


app = FastAPI(
    title="OmegaSportsAgent API",
    description="Quantitative sports analytics engine — simulation, calibration, and edge detection.",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS — allow the Next.js frontend (dev and production)
# Set CORS_ORIGINS env var to a comma-separated list for production origins.
import os as _os

_default_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
_extra = _os.environ.get("CORS_ORIGINS", "")
_origins = _default_origins + [o.strip() for o in _extra.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request Logging Middleware ──────────────────────────────


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    elapsed = time.time() - start
    logger.info(
        "%s %s -> %d (%.2fs)",
        request.method,
        request.url.path,
        response.status_code,
        elapsed,
    )
    return response


# ── Endpoints ───────────────────────────────────────────────


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "engine": "OmegaSportsAgent", "version": "2.0.0"}


@app.post("/analyze/game", response_model=GameAnalysisResponse)
async def analyze_game_endpoint(request: GameAnalysisRequest):
    """Analyze a single game matchup.

    Supply home_team, away_team, league, and optionally odds.
    Returns simulation results, edge analysis, and bet recommendation.
    """
    try:
        result = analyze_game(request)
        return result
    except Exception as exc:
        logger.exception("Unhandled error in /analyze/game")
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error_code="INTERNAL_ERROR",
                message=str(exc),
                fallback_hint="Check server logs for details",
            ).model_dump(),
        )


@app.post("/analyze/prop", response_model=PlayerPropResponse)
async def analyze_prop_endpoint(request: PlayerPropRequest):
    """Analyze a single player prop.

    Supply player_name, league, prop_type, line, and optionally odds + context.
    Returns over/under probabilities, edge, and recommendation.
    """
    try:
        result = analyze_player_prop(request)
        return result
    except Exception as exc:
        logger.exception("Unhandled error in /analyze/prop")
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error_code="INTERNAL_ERROR",
                message=str(exc),
                fallback_hint="Check server logs for details",
            ).model_dump(),
        )


@app.post("/analyze/slate", response_model=SlateAnalysisResponse)
async def analyze_slate_endpoint(request: SlateAnalysisRequest):
    """Analyze all games for a league on a given date.

    Returns per-game analysis with edge detection.
    """
    try:
        result = analyze_slate(request)
        return result
    except Exception as exc:
        logger.exception("Unhandled error in /analyze/slate")
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error_code="INTERNAL_ERROR",
                message=str(exc),
                fallback_hint="Check server logs for details",
            ).model_dump(),
        )


# ── Chat Endpoint (SSE Streaming) ─────────────────────────────


def _sse_event(event_type: str, data: Any, session_id: str) -> str:
    """Format a single SSE event."""
    payload = json.dumps({"event_type": event_type, "data": data, "session_id": session_id}, default=str)
    return f"data: {payload}\n\n"


@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """Conversational chat endpoint with SSE streaming.

    Accepts a user message, runs the full agent pipeline, and streams
    progress updates and results as Server-Sent Events.
    """
    session_id = session_store.get_or_create(request.session_id)
    now = datetime.now(timezone.utc).isoformat()

    # Record user message
    session_store.append(session_id, ChatMessage(
        role="user",
        content=request.message,
        timestamp=now,
    ))

    async def event_generator() -> AsyncGenerator[str, None]:
        progress_queue: queue.Queue[Dict[str, Any]] = queue.Queue()

        def progress_callback(stage: str) -> None:
            progress_queue.put({"stage": stage})

        # Run the synchronous agent pipeline in a thread
        orchestrator = _get_orchestrator()
        history = session_store.get_history(session_id)

        # Convert history to simple dicts for the orchestrator
        history_dicts = [
            {"role": m.role, "content": m.content}
            for m in history[:-1]  # exclude the just-appended user message
        ]

        try:
            yield _sse_event("stage_update", "intent_understanding", session_id)

            # Run the pipeline in a thread
            result = await asyncio.to_thread(
                orchestrator.handle_chat,
                user_prompt=request.message,
                history=history_dicts,
                progress_callback=progress_callback,
            )

            # Drain any remaining progress events
            while not progress_queue.empty():
                try:
                    evt = progress_queue.get_nowait()
                    yield _sse_event("stage_update", evt["stage"], session_id)
                except queue.Empty:
                    break

            # Send structured data
            yield _sse_event("structured_data", result, session_id)

            # Extract narrative text from sections for partial_text
            narrative_parts = []
            if isinstance(result, dict):
                for section in result.get("sections", []):
                    narrative = section.get("narrative")
                    if narrative:
                        narrative_parts.append(narrative)

            if narrative_parts:
                full_narrative = "\n\n".join(narrative_parts)
                yield _sse_event("partial_text", full_narrative, session_id)

            # Record assistant response
            assistant_content = "\n\n".join(narrative_parts) if narrative_parts else json.dumps(result, default=str)
            session_store.append(session_id, ChatMessage(
                role="assistant",
                content=assistant_content,
                timestamp=datetime.now(timezone.utc).isoformat(),
                structured_data=result if isinstance(result, dict) else None,
            ))

            yield _sse_event("done", {"session_id": session_id}, session_id)

        except Exception as exc:
            logger.exception("Chat pipeline error")
            yield _sse_event("error", {"message": str(exc)}, session_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
