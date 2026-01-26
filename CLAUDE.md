# CLAUDE.md - OmegaSportsAgent Project Context

## Project Overview

**OmegaSportsAgent** is a quantitative sports betting analytics engine that generates daily bet recommendations using Monte Carlo simulation, Markov chain modeling, and statistical edge detection. It is designed as a headless CLI tool for automated daily bet generation across NBA, NFL, MLB, NHL, NCAAB, and NCAAF.

## Quick Start Commands

```bash
# Run daily bet generation workflow
python main.py daily-bets

# Execute full pipeline with output
python execute_daily_bets.py

# Run calibration lab
python -m lab.core.calibration_runner

# Check data integrity
python -m src.data.data_integrity_check
```

## Architecture Overview

```
OmegaSportsAgent/
├── main.py                     # CLI entry point
├── daily_bet_generation.py     # Daily workflow orchestrator
├── execute_daily_bets.py       # Production executable
├── src/
│   ├── data/                   # Data ingestion (ESPN, Odds API, Ball Don't Lie)
│   ├── simulation/             # Monte Carlo (10K iter) + Markov (50K iter)
│   ├── betting/                # Edge calc, Kelly staking, correlation
│   ├── workflows/              # Morning bets, daily grading
│   ├── analytics/              # League baselines (Four Factors, EPA, xG)
│   ├── narratives/             # Game analysis generation
│   └── calibration/            # Probability transforms (Platt, shrinkage)
├── lab/                        # Validation & backtesting
├── config/                     # Calibration packs & settings
├── outputs/                    # Daily reports (timestamped)
└── data/                       # Logs, exports, cache
```

## Core Algorithms

### 1. Monte Carlo Simulation (`src/simulation/simulation_engine.py`)
- 10,000+ iterations per game
- Auto-selects Poisson (discrete) vs Normal (continuous) distributions
- Outputs: win probabilities, score distributions, spread/total projections

### 2. Markov Chain Engine (`src/simulation/markov_engine.py`)
- 50,000 iterations for player props
- State-based play-by-play modeling
- Strict no-defaults policy (skips bets if data missing)

### 3. Edge Calculation (`src/betting/odds_eval.py`)
```python
edge = (model_probability - implied_probability) * 100
ev = (model_prob * (decimal_odds - 1) - (1 - model_prob)) * 100
```

### 4. Kelly Staking (`src/betting/kelly_staking.py`)
- Quarter-Kelly (0.25 fraction) with tier multipliers
- Drawdown penalties, losing streak adjustments
- Hard cap: 2.5% of bankroll per bet

## Data Sources & Fallback Chain

| Priority | Source | Coverage |
|----------|--------|----------|
| 1 | ESPN API | Schedule, scores, injuries |
| 2 | The Odds API | Live odds (multi-book) |
| 3 | Ball Don't Lie | Team/player stats |
| 4 | Perplexity AI | Enrichment fallback |
| 5 | Stale Cache | Last known good data |

## Bet Qualification Thresholds

| Tier | Min Edge | Min EV | Max Units |
|------|----------|--------|-----------|
| A | 7%+ | 5%+ | 2.0 |
| B | 4-6.9% | 3-4.9% | 1.5 |
| C | 3-3.9% | 2.5-2.9% | 1.0 |

## Key Configuration Files

- `config/calibration/universal_latest.json` - Edge thresholds, Kelly params, transforms
- `config/settings.yaml` - Timezone, books, logging mode
- `.env` - API keys (ODDS_API_KEY, PERPLEXITY_API_KEY, etc.)

## Output Files

| File | Location | Purpose |
|------|----------|---------|
| BetLog.csv | `data/exports/` | All qualified bets (append-only) |
| predictions.json | `data/logs/` | Daily predictions with metadata |
| daily_narrative_*.md | `outputs/` | Game analysis reports |
| categorical_summary_*.md | `outputs/` | Best plays by tier |

## Development Guidelines

### Code Style
- Python 3.10+ with type hints
- Pydantic for data validation
- Async/await for I/O operations

### Data Integrity Rules
1. **NEVER use defaults** - Skip bets if critical data missing
2. **Log all data sources** - Track provenance in data_integrity_log.json
3. **Prefer stale over None** - Use cache fallback before giving up

### Adding New Markets
1. Define market type in `src/betting/market_types.py`
2. Add simulation logic in `src/simulation/`
3. Create threshold config in `config/calibration/`
4. Add to edge calculation in `src/betting/odds_eval.py`

### Testing
```bash
# Run unit tests
pytest tests/

# Run integration tests
pytest tests/integration/

# Run calibration validation
python -m lab.validation.validate_calibration
```

## Known Limitations

1. **Daily-only updates** - No intra-day injury/line adjustments
2. **Static variance scalars** - Hardcoded per sport
3. **Manual calibration** - Requires periodic manual refit
4. **API rate limits** - The Odds API can 429 on heavy days
5. **Player name matching** - Exact match only (no fuzzy)

## Roadmap Priority

See `BETTING_STRATEGY_ROADMAP.md` for comprehensive improvement plan covering:
- Advanced ML models (XGBoost, neural nets)
- Real-time CLV tracking
- Dynamic Kelly optimization
- Automated calibration pipeline
- Closing line value analysis

## Troubleshooting

### Common Issues

**"No odds data for game"**
- Check The Odds API key is valid
- Verify game hasn't already started
- Check `data/logs/data_integrity_log.json` for API errors

**"Simulation returned None"**
- Critical stats missing - check Ball Don't Lie API
- Run `python -m src.data.stats_ingestion --debug`

**"Edge below threshold"**
- Model probability close to market implied
- Consider reviewing calibration transforms

### Debug Mode
```bash
# Enable verbose logging
export LOG_LEVEL=DEBUG
python execute_daily_bets.py

# Check data sources
python -c "from src.data import schedule_ingestion; schedule_ingestion.fetch_today(debug=True)"
```

## Contributing

1. All changes must pass existing tests
2. New simulation methods need backtesting validation
3. Calibration changes require lab validation
4. Document data source changes in this file

## API Key Requirements

```env
ODDS_API_KEY=xxx          # theOddsAPI.com
PERPLEXITY_API_KEY=xxx    # perplexity.ai (fallback)
BALLDONTLIE_API_KEY=xxx   # Ball Don't Lie (All-Star tier for NFL)
ESPN_API_KEY=xxx          # Optional - ESPN public API
```

## Contact & Resources

- Primary docs: `GUIDE.md`, `SYSTEM_ARCHITECTURE.md`
- Calibration docs: `config/calibration/README.md`
- Lab documentation: `lab/README.md`
