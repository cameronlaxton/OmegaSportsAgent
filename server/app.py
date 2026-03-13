"""
FastAPI application for OmegaSportsAgent.

Exposes the simulation engine via JSON-in/JSON-out endpoints only.
No live data fetching; caller supplies games and context. Run: uvicorn server.app:app --reload
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.contracts.schemas import (
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
    yield
    logger.info("OmegaSportsAgent API shutting down")


app = FastAPI(
    title="OmegaSportsAgent API",
    description="Quantitative sports analytics engine — simulation, calibration, and edge detection.",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS — allow the Next.js frontend (default dev port 3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
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
