## OmegaSportsAgent

**A Professional Decision Support Engine for Sports Analytics**  
*Quantitative research platform for identifying +EV betting opportunities*

---

## 📌 Overview

OmegaSportsAgent is a **quantitative research platform** that calculates true probabilities for sports outcomes using possession-level Markov chains and Monte Carlo simulation. It compares these probabilities against market implied odds to identify positive expected value (+EV) opportunities. The engine is designed for **decision support only**—it does not place bets or interface with sportsbooks.

**Current Status:** 🧪 **QA / Validation Phase** – Core functionality is implemented, but rigorous backtesting and calibration are ongoing. Not yet recommended for live wagering.

---

## 🧠 Philosophy

### Decision Support, Not Execution
This engine does not place bets. It calculates probabilities, identifies +EV opportunities, and provides deep analytical context to help the **human user** make informed decisions. The human is always the final decision-maker.

### Search-First Data Architecture
We have moved away from hardcoded API adapters (e.g., `espn.py`, `oddsapi.py`). Instead, the system is built around an **LLM-driven web search and structured extraction pipeline**. This approach:

- Gathers current sports information from the web dynamically.
- Extracts usable structured facts from multiple sources.
- Normalizes facts into canonical models.
- Validates freshness, agreement, and completeness.
- Fuses results into a single trusted analysis input.

This architecture is more adaptable, resilient to source changes, and leverages the power of LLMs for intelligent data gathering.

### The "Hybrid" Edge
Our data architecture combines:
- **Rigid API Data** (optional fallback): Base statistics, schedules, standings when APIs are reliable.
- **Search-First Extraction**: Primary method for obtaining real-time data (odds, injuries, lineups, advanced stats).
- **JSONB Storage** (PostgreSQL): Sport-agnostic schema that adapts without migrations.

### The "No Defaults" Policy
If essential data (e.g., team offensive/defensive ratings, pace) is missing, the simulation is **skipped** and logged. No game is simulated with incomplete data.

---

## 🏗️ Architecture

### High-Level Pipeline

┌─────────────────────────────────────────────────────────────────────────────┐
│                         SEARCH-FIRST DATA PIPELINE                           │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│  │  Acquisition │───▶│  Extractors  │───▶│ Normalizers  │                  │
│  │  (web search,│    │  (pull facts │    │  (canonical  │                  │
│  │   fetch)     │    │   from raw)  │    │   models)    │                  │
│  └──────────────┘    └──────────────┘    └──────┬───────┘                  │
│                                                   │                          │
│                                                   ▼                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│  │   Fusion     │◀───│  Validators  │◀───│   Sources    │                  │
│  │  (combine,   │    │  (freshness, │    │  (trust,     │                  │
│  │   resolve)   │    │   agreement) │    │   priorities)│                  │
│  └──────┬───────┘    └──────────────┘    └──────────────┘                  │
│         │                                                                   │
│         ▼                                                                   │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│  │   Models     │    │  Orchestration│   │    Cache     │                  │
│  │ (canonical   │    │ (flow control)│   │ (storage,    │                  │
│  │  structures) │    │              │   │  freshness)  │                  │
│  └──────────────┘    └──────────────┘    └──────────────┘                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            SIMULATION CORE                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  OmegaSimulationEngine                                                       │
│  ├── run_game_simulation()      → Team markets (spread, total, ML)          │
│  ├── run_player_prop_simulation() → Player props (pts, reb, pass_yds)       │
│  └── run_fast_game_simulation()   → Quick edge detection for dashboards     │
│                                                                              │
│  MarkovSimulator                                                             │
│  ├── TransitionMatrix (league-specific state probabilities)                 │
│  ├── simulate_game() → Play-by-play with player stat accumulation           │
│  └── Autonomous Calibration → Parameters tuned from historical outcomes     │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            ANALYSIS LAYER                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  Odds Evaluation (odds_eval.py)                                             │
│  ├── american_to_decimal()      → Odds format conversion                    │
│  ├── implied_probability()      → Market's implied win % (vig-removed)      │
│  ├── edge_percentage()          → (True Prob - Implied Prob) × 100          │
│  └── expected_value_percent()   → EV as % of stake                          │
│                                                                              │
│  Kelly Staking (kelly_staking.py)                                           │
│  ├── kelly_fraction()           → Raw Kelly optimal fraction                │
│  └── recommend_stake()          → Quarter-Kelly with caps & adjustments     │
│      ├── Tier caps (A: 2.0u, B: 1.5u, C: 1.0u)                             │
│      ├── Losing streak penalty                                              │
│      ├── Drawdown protection                                                │
│      └── Hard cap: 2.5% of bankroll                                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              OUTPUT                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  Edge Report                                                                 │
│  {                                                                           │
│    "matchup": "Lakers vs Warriors",                                         │
│    "market": "Lakers ML",                                                   │
│    "true_prob": 0.58,                                                       │
│    "implied_prob": 0.476,                                                   │
│    "edge": 10.4%,                                                           │
│    "recommended_units": 1.25,                                               │
│    "confidence_tier": "B"                                                   │
│  }                                                                           │
└─────────────────────────────────────────────────────────────────────────────┘

### Detailed Data Pipeline Components

| Directory | Purpose |
|-----------|---------|
| `src/data/acquisition/` | Gets raw data from the outside world: web search, page fetches, cached retrieval, and optional direct API calls. |
| `src/data/sources/` | Defines source trust, preferred sites by sport/data type, and source-specific rules without making every source a full adapter. |
| `src/data/extractors/` | Pulls structured candidate facts out of raw pages, snippets, and search results: schedules, odds, stats, injuries, lineups, game logs, etc. |
| `src/data/normalizers/` | Converts extracted facts into canonical internal models: standardizes team names, player identities, markets, statuses, dates, and stat fields. |
| `src/data/validators/` | Checks whether extracted data is usable: freshness, completeness, agreement across sources, contradiction detection, and sanity checks. |
| `src/data/fusion/` | Merges multiple validated source results into one trusted view: resolves conflicts, assigns confidence, and chooses the best combined output. |
| `src/data/models/` | Holds the canonical data structures used by the rest of the system: games, markets, props, stats, injuries, lineups, and provenance-bearing result objects. |
| `src/data/orchestration/` | Coordinates the end-to-end retrieval flow: decides what to search, what to fetch next, which extractors to run, and when to stop or fall back. |
| `src/data/cache/` | Stores prior retrievals, parsed pages, normalized results, and freshness metadata to reduce repeated work and improve speed/stability. |
| `src/data/tests/` | Validates extraction quality, normalization consistency, validation logic, fusion behavior, and retrieval orchestration reliability. |

---

## 📊 Methodology

We reject naive approaches. Our probability engine uses:

### 1. Possession-Level Markov Chains
- Games are simulated play-by-play, not as single random variables.
- State transitions model real game flow (possessions, downs, plate appearances).
- Player involvement is weighted by usage rates and target shares.
- **Sport‑specific state encodings** (e.g., down & distance for NFL, possession type for NBA) are used.

### 2. Monte Carlo Simulation
- 1,000–10,000 iterations per matchup.
- Full distribution outputs (mean, std, percentiles P10/P25/P50/P75/P90).
- Captures tail risk and variance.

### 3. Sport-Specific Distributions
- **Poisson**: Discrete counts (goals, touchdowns, receptions).
- **Normal**: Continuous metrics (yards, points in high-scoring sports).
- Distribution selection is automatic based on `(metric_key, league)` pairs.

### 4. Team Context Adjustment
- Offensive/Defensive ratings modify transition probabilities.
- Pace factors scale possession counts.
- No simulation runs on "default" data—incomplete games are skipped.

The output is a **True Probability** that we compare against **Market Implied Probability** (vig-removed) to find edges.

---

## 🔬 Validation & Calibration (Phase 2 – In Progress)

The simulation engine must earn its confidence. We are actively building:

- **Prediction Ledger**: Stores all model predictions with timestamps.
- **Outcome Reconciliation**: Automated grading against final scores.
- **Calibration Metrics**:
  - Brier Score (probability accuracy)
  - Log Loss (confidence calibration)
  - Hit Rate by Edge Bucket (5%+ edge should hit >55%)
- **Parameter Tuning**: Auto-calibrator adjusts Markov transition probabilities based on historical performance.
- **CLV Tracking**: Compare entry odds vs closing line to validate edge detection.

**⚠️ Important**: Until Phase 2 is complete, all probabilities and edge recommendations should be considered **experimental**. Do not use for real-money betting.

---

## 🧩 Key Files Reference

| Path | Purpose |
|------|---------|
| `src/simulation/simulation_engine.py` | Monte Carlo engine, `OmegaSimulationEngine` class |
| `src/simulation/markov_engine.py` | Play-by-play Markov simulator |
| `src/betting/kelly_staking.py` | Quarter-Kelly stake recommendations |
| `src/betting/odds_eval.py` | EV/edge calculations (with vig removal) |
| `src/data/orchestration/` | Main entry point for data retrieval flows |
| `src/data/models/` | Canonical data structures (Game, Market, PlayerProp, etc.) |
| `src/calibration/prediction_audit.py` | Prediction logging and grading |
| `src/calibration/calibrator.py` | Calibration metrics and parameter tuning |

---

## 🤖 LLM Agent Integration Guide

OmegaSportsAgent is designed to be driven by an LLM agent that gathers context, runs simulations, and interprets results. The following sections summarize the key knowledge base articles (KBAs) located in `knowledgebase/`. Agents should follow these guidelines when interacting with the system.

### 1. Context Gathering Per Sport (KB-A1)

Before calling OmegaSportsAgent, the agent must collect structured game context via web search/APIs.

**Common game-level context (all sports):**
- Basic identifiers: date, league, teams (canonical names), home/away.
- Market data: spread, total, moneyline odds (with vig).
- Team recent form: last N games record, average margin, key trends.
- Injuries/absences: list of out/questionable players, impact label.
- Venue context: home/away, travel/rest days.

**Sport-specific requirements:**
- **NBA**: offensive/defensive ratings, pace, shooting profile, home/road splits.
- **NFL**: offensive/defensive efficiency (points per drive, EPA), tempo, weather, injuries to key players.
- **NCAAB/NCAAF**: similar to NBA/NFL but with college-specific adjustments.
- **Soccer/Hockey**: goals for/against, xG, home/away splits, schedule congestion.

**Player props (NBA example):**
- Player scoring and minutes (season, last 5/10).
- Usage rate, starter/bench status.
- Game pace, opponent defensive rating.
- Market line and odds.

The agent should compute derived parameters (e.g., expected λ for Poisson models) and construct a clean JSON payload matching OmegaSportsAgent’s input contracts.

### 2. Game Market Probability Calculation (KB-G1)

Given simulation outputs (scores per iteration), the agent can compute:
- Win probabilities: `P_home_win = count(margin > 0) / N`
- Spread probabilities: `P_home_cover = count(margin > spread_line) / N`
- Total probabilities: `P_over = count(total > total_line) / N`
- Predicted spread/total: mean of margins/totals.

These probabilities feed into edge calculation.

### 3. Player Prop Modeling (KB-P1, KB-P2)

For count-based props (points, rebounds, assists), use a Poisson-style model:
- Estimate baseline λ from recent and season averages.
- Adjust for minutes, pace, and matchup defense.
- Compute `P_over` and `P_under` using Poisson CDF.
- Pass true probabilities to OmegaSportsAgent for edge and Kelly.

### 4. Edge and Kelly Staking (KB-B1)

Given true probability `p` and market odds (American):
- Convert odds to decimal and implied probability `q`.
- Compute edge percentage: `(p - q) * 100`.
- If EV > 0, apply Kelly formula: `f* = (p*(odds_decimal-1) - (1-p)) / (odds_decimal-1)`.
- Use fractional Kelly (e.g., 0.25 or 0.5) based on confidence tier.
- Apply bankroll constraints and tier caps.

### 5. Markov Possession-Based Models (KB-M1)

For sports where play-by-play dynamics matter (NBA, NFL, hockey), the engine uses a Markov chain. The agent does not need to implement this but should understand that:
- States represent possession, time, score, and sport-specific context.
- Transition probabilities are calibrated from historical data.
- The engine outputs final scores and derived probabilities.

### 6. Calibration Loop (KB-C1)

To improve model accuracy, the agent should participate in the Predict–Grade–Tune loop:
- **Predict**: Log each bet recommendation with true probability, odds, stake, and identifiers.
- **Grade**: After games settle, record outcomes (win/loss/push) and closing lines.
- **Tune**: Periodically run calibration to adjust shrinkage, caps, or recalibrate probabilities.

The calibration engine computes Brier score, ECE, and updates parameters in `league_calibrations.yaml`.

---

## 🚀 Setup

### Requirements
- Python 3.10+
- PostgreSQL 15+ (for JSONB GIN indexing)
- Docker (recommended)

### Installation
```bash
# Clone repository
git clone https://github.com/cameronlaxton/OmegaSportsAgent.git
cd OmegaSportsAgent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt
```

### Environment Variables
```bash
# .env file
DATABASE_URL=postgresql://user:pass@localhost:5432/omega_sports
# Optional: API keys for fallback direct calls
ODDS_API_KEY=your_odds_api_key
BALLDONTLIE_API_KEY=your_balldontlie_key
```

### Database Setup
```bash
# Start PostgreSQL (Docker)
docker-compose up -d postgres

# Apply migrations
alembic upgrade head

# Seed initial data (optional)
python -m src.db.seed
```

### Running
```bash
# Run example simulation with league filtering
python main.py --league NBA

# Analyze specific matchup
python main.py --league NBA --home "Lakers" --away "Warriors"

# Output as JSON for programmatic consumption
python main.py --league NBA --home "Celtics" --away "Heat" --json
```

---

## 📚 Knowledge Base

Detailed guidelines for LLM agents are maintained in the `knowledgebase/` directory:

| File | Description |
|------|-------------|
| `KB-A1_Context_per_Sport.txt` | Required context for different sports and markets. |
| `KB-G1_Generic_Game_Markets.txt` | Turning simulation outputs into game market metrics. |
| `KB-B1_Kelly_Staking.txt` | Computing and interpreting Kelly stakes. |
| `KB-M1_Markov_Models.txt` | Using Markov chains for possession-based sports. |
| `KB-S1_NBA_Full_Game.txt` | NBA full-game modeling specifics. |
| `KB-P2_NBA_Points_Prop.txt` | NBA points prop modeling. |
| `KB-P1_Player_Props_Count_Models.txt` | General count models for player props. |
| `KB-C1_Calibration.txt` | Probability calibration and Predict–Grade–Tune loop. |

Agents should consult these files for detailed instructions.

---

## 📈 Supported Leagues

| League | Game Simulation | Player Props | Data Collector | Status |
|--------|-----------------|--------------|----------------|--------|
| NBA | ✅ Full | ✅ Full | Search-first + NBA Stats API | Production |
| NFL | ✅ Full | ✅ Full | Search-first + ESPN / PFR | Production |
| NCAAB | ✅ Full | Beta | Search-first | Beta |
| NCAAF | ✅ Full | Beta | Search-first | Beta |
| MLB | ❌ Not yet | ❌ None | Development | Development |
| NHL | ❌ Not yet | ❌ None | Development | Development |

---

## 📄 License

Private repository - authorized use only.

---

## ⚠️ Disclaimer

**The goal is not to predict the future. The goal is to have a more accurate probability distribution than the market.**  
This software is for research and informational purposes only. Always gamble responsibly. Never bet money you cannot afford to lose.
```

This README now fully integrates the search-first data architecture, the detailed KBA guidelines, and the previous content. It serves as a comprehensive guide for both developers and LLM agents.
