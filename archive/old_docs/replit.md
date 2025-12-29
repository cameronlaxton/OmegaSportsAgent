# OmegaSports Headless Simulation Engine

## Overview
OmegaSports is a **headless sports analytics and simulation engine** designed for execution by Perplexity Spaces/Agents via GitHub. It runs Monte Carlo simulations to identify +EV betting opportunities across NBA, NFL, MLB, NHL, NCAAB, and NCAAF. This is a data-processing pipeline with no web interface - all operations output JSON/Markdown files for agent consumption.

## User Preferences
- Simple language preferred
- Iterative development approach
- Ask before making major changes
- Detailed explanations requested
- Preserve archive/ folder contents

## Recent Changes
- **2025-12-27**: Added Universal Sports Schema with Pydantic
  - Added: `omega/schema.py` with Pydantic models (GameData, BettingLine, PropBet, DailySlate, etc.)
  - Added: `parse_to_game_data()` and `validate_game_data()` in scraper_engine.py
  - Updated: `AGENT_INSTRUCTIONS.md` with Data Feeding Protocol for strict data validation
  - Schema auto-detects American vs decimal odds formats
  
- **2025-12-27**: Pivoted from web application to headless simulation engine
  - Removed: Express.js server, Node.js dependencies, web UI components
  - Added: `scraper_engine.py` with Playwright/system Chromium for live data fetching
  - Added: `AGENT_INSTRUCTIONS.md` for Perplexity Agent integration
  - Refactored: `main.py` as CLI entry point with command-line options
  - Created: `logs/` and `outputs/` directories for simulation results

## System Architecture

### Entry Points
| File | Purpose |
|------|---------|
| `main.py` | Primary CLI - all simulation commands |
| `scraper_engine.py` | Web scraper with JavaScript rendering |
| `omega/workflows/morning_bets.py` | Automated bet generation |

### CLI Commands
```bash
python main.py --morning-bets --leagues NBA NFL   # Generate daily picks
python main.py --analyze "Team A" "Team B"        # Matchup analysis
python main.py --simulate NBA --iterations 10000  # League simulation
python main.py --audit --start-date 2025-01-01    # Backtest audit
python main.py --scrape "https://espn.com/..."    # Fetch live data
```

### Core Modules (`omega/`)
- **schema.py**: Universal Sports Schema with Pydantic models for data validation
- **simulation/**: Monte Carlo and Markov chain engines
- **data/**: Stats ingestion, scrapers, API integrations
- **betting/**: Odds evaluation, Kelly staking, edge calculation
- **analytics/**: League baselines, market analysis
- **modeling/**: Probability calibration, projections
- **workflows/**: Automated morning bet workflows
- **utilities/**: Logging, persistence, output formatting

### Universal Sports Schema (`omega/schema.py`)
Pydantic models that enforce data quality:
- `GameData` - Primary game structure with betting lines
- `BettingLine` - Individual betting line (auto-detects American/decimal odds)
- `PropBet` - Player prop bet structure
- `DailySlate` - Collection of games for a day
- `BetRecommendation` - Output structure for picks

### Data Flow
1. `scraper_engine.py` fetches live sports data as Markdown
2. `omega/data/` modules process and structure the data
3. `omega/simulation/` runs Monte Carlo simulations
4. `omega/betting/` evaluates edges and recommends bets
5. Results saved to `outputs/` as JSON

## Output Locations
- `outputs/morning_bets_*.json` - Daily bet recommendations
- `outputs/analysis_*.json` - Matchup analyses
- `outputs/simulation_*.json` - League simulation results
- `logs/omega_engine.log` - Execution logs
- `data/cache/` - Cached API responses
- `data/logs/` - Bet and simulation history

## External Dependencies
- **ESPN API**: Game schedules, team/player statistics, injury data (free)
- **The Odds API**: Live betting odds (free tier)
- **Perplexity API**: Narrative generation, data enrichment (optional)
- **Ball Don't Lie API**: NBA player statistics (fallback)
- **PostgreSQL**: Persistent storage for historical data

## Environment Variables
| Variable | Purpose |
|----------|---------|
| `PERPLEXITY_API_KEY` | Data enrichment (optional) |
| `BALLDONTLIE_API_KEY` | NBA stats fallback |
| `THE_ODDS_API_KEY` | Live odds data |

## Project Structure
```
omega-sports-engine/
├── main.py                    # CLI entry point
├── scraper_engine.py          # Crawl4AI web scraper
├── AGENT_INSTRUCTIONS.md      # Perplexity Agent guide
├── omega/                     # Core simulation modules
│   ├── simulation/            # Monte Carlo engines
│   ├── data/                  # Data ingestion
│   ├── betting/               # Edge evaluation
│   └── workflows/             # Automated tasks
├── logs/                      # Execution logs
├── outputs/                   # Simulation results
├── data/                      # Cache & historical data
├── config/                    # Agent configuration
└── archive/                   # Documentation & specs
```

## Workflow
The `OmegaSports Engine` workflow runs:
```bash
python main.py --morning-bets --leagues NBA
```
This evaluates all NBA games, runs 10,000 simulations per game, and outputs qualified bets to `outputs/`.

## GitHub Integration
Repository syncs to GitHub for Perplexity Spaces access. All outputs are file-based JSON/Markdown for easy parsing by external agents.
