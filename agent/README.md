# Agent Layer

LLM + web search. This is the **only** place that should fetch live data (schedules, stats, odds) and call external APIs (ESPN, Perplexity, NBA Stats API, etc.).

- Call `src/data/` modules that perform HTTP/API here (e.g. `stats_ingestion.get_team_context`, `schedule_api.get_todays_games`).
- Then call FastAPI with fully-populated requests (`GameAnalysisRequest` with `home_context`/`away_context`, `SlateAnalysisRequest` with `games`).
- When adding an orchestrator: it must not be called automatically from engine or service code; engine/service are input-driven only.
