# Ingestion Guide for LLM Agents

This project is data-source agnostic. LLM agents can plug in scraped/web data for: schedules & matchups, team context (off/def ratings, pace, injuries), player stats/usage, odds (current + historical), and weather/news signals. Normalize odds by separating spread value vs. price (juice); use American odds for price fields (e.g., -110).

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
