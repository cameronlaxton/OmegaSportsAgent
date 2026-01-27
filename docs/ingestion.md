# Ingestion Guide for LLM Agents

This project is data-source agnostic. LLM agents can plug in scraped/web data for:
- Schedules & matchups
- Team context (off/def ratings, pace, injuries)
- Player stats/usage
- Odds (current + historical)
- Weather/news signals

## Provider Interfaces
See `src/data/providers.py`:
- `GamesProvider(league) -> List[dict]`
- `TeamContextProvider(team, league) -> TeamContextInput`
- `PlayerContextProvider(player, league) -> PlayerContextInput`
- `OddsProvider(game, league) -> OddsQuote|dict`
- `WeatherNewsProvider(game, league) -> WeatherNewsSignal`

## Web Provider Stubs
Implement your scraping/search in `src/data/providers_web.py`:
- `fetch_team_context_web`
- `fetch_odds_web`
- `fetch_weather_news_web`

These should normalize outputs to the provider schemas. Return `None` to let the engine fallback.

## Analyst Engine Wiring
`AnalystEngine` accepts providers:
- games_provider
- team_context_provider
- player_context_provider
- odds_provider
- weather_news_provider

Use `analyze_edges` or `find_daily_edges` (via `src/interface.py`) and inject providers or pre-fetched games/odds.

## Context & Features
`src/data/context_features.py` contains helpers to turn scraped stats into:
- off/def ratings, pace
- injury adjustments
- weather adjustments

## Odds History
`src/data/odds_store.py` offers simple JSONL persistence for historical odds. Swap in your own store if needed.

## Calibration
Ingested probabilities can be calibrated via `src/validation/probability_calibration.py`. AnalystEngine already applies a combined shrink+cap calibration to damp extreme win probs.

## Error Handling
- Always null-check team/player/odds fields before use.
- Provide defaults or skip malformed games to avoid crashes when sources are incomplete.
