# OmegaSportsAgent

## A Professional Decision Support Engine for Sports Analytics

---

## Project Philosophy

### Decision Support, Not Execution

> **This engine does not place bets.** It calculates probabilities, identifies +EV (Positive Expected Value) opportunities, and provides deep analytical context to help the human user make informed decisions.

OmegaSportsAgent is a quantitative research platform. It exists to answer one question: *"What is the true probability of this outcome, and how does it compare to the market's opinion?"*

The engine outputs:
- **True Probabilities** derived from simulation
- **Edge Calculations** (True Prob - Implied Prob)
- **Suggested Unit Sizing** via Kelly Criterion
- **Confidence Tiers** (A/B/C) based on data quality

It does NOT:
- Execute trades or place wagers
- Interface with sportsbook APIs
- Make autonomous financial decisions

The human is always the final decision-maker.

---

### The "Hybrid" Edge

Our competitive advantage comes from a deliberate data architecture strategy:

| Layer | Source | Purpose |
|-------|--------|---------|
| **Rigid API Data** | ESPN, BallDontLie, Official Stats | Base statistics, schedules, standings—structured and reliable |
| **Scraping Layer** | Targeted sources | Granular data not available via API (usage rates, advanced metrics, injury context) |
| **JSONB Storage** | PostgreSQL Hybrid Schema | Sport-agnostic storage: `{"pts": 24}` for NBA, `{"pass_yds": 280}` for NFL |

This hybrid approach allows us to:
1. Maintain data integrity with canonical entity resolution
2. Adapt to new metrics without schema migrations
3. Feed a unified simulation engine regardless of sport

---

### Methodology

We reject naive approaches. Our probability engine uses:

#### 1. Possession-Level Markov Chains

- Games are simulated play-by-play, not as single random variables
- State transitions model real game flow (possessions, downs, plate appearances)
- Player involvement is weighted by usage rates and target shares

#### 2. Monte Carlo Simulation

- 1,000–10,000 iterations per matchup
- Full distribution outputs (mean, std, percentiles P10/P25/P50/P75/P90)
- Captures tail risk and variance, not just point estimates

#### 3. Sport-Specific Distributions

- **Poisson**: Discrete counts (goals, touchdowns, receptions)
- **Normal**: Continuous metrics (yards, points in high-scoring sports)
- Distribution selection is automatic based on `(metric_key, league)` pairs

#### 4. Team Context Adjustment

- Offensive/Defensive ratings modify transition probabilities
- Pace factors scale possession counts
- No simulation runs on "default" data—incomplete games are skipped

The output is a **True Probability** that we compare against **Market Implied Probability** to find edges.

---

## System Architecture (The Pipeline)

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA INGESTION                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  Schedule API  ──►  Stats Scraper  ──►  Entity Resolver  ──►  JSONB Store  │
│  (ESPN)              (Multi-source)      (Alias → UUID)       (PostgreSQL)  │
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
│  ├── implied_probability()      → Market's implied win %                    │
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
```

---

## How to Query This Engine (For AI Agents)

This section is the **LLM Operator Manual**. When integrated with an AI agent, the engine should be queried systematically, not ad-hoc.

### The "Search → Sim → Report" Loop

When a user asks: *"What are the best NBA bets today?"*

**Do NOT guess.** Execute this workflow:

```text
1. FETCH SCHEDULE
   └── get_todays_games("NBA") → List of matchups with odds

2. FOR EACH MATCHUP:
   └── VALIDATE data completeness
       └── If missing team context → SKIP (do not simulate with defaults)
   └── RUN SIMULATION
       └── engine.run_game_simulation(home, away, "NBA", n_iter=1000)
       └── Extract: true_prob_home, true_prob_away, predicted_spread, predicted_total

3. FETCH MARKET ODDS
   └── From schedule response or odds_snapshots table
   └── Convert to implied probabilities

4. CALCULATE EDGES
   └── edge = true_prob - implied_prob
   └── Filter: Only return edges > threshold (e.g., 3%)

5. APPLY KELLY SIZING
   └── recommend_stake(true_prob, odds, bankroll, confidence_tier)

6. FORMAT REPORT
   └── Sort by edge descending
   └── Include confidence tier, units, and data quality notes
```

### Pseudo-Code Example

```python
from src.data.schedule_api import get_todays_games
from src.simulation.simulation_engine import OmegaSimulationEngine
from src.betting.odds_eval import implied_probability, edge_percentage
from src.betting.kelly_staking import recommend_stake

def find_daily_edges(league: str, bankroll: float, edge_threshold: float = 0.03):
    """
    The canonical workflow for finding +EV opportunities.
    Returns edges, not bets. Human decides.
    """
    engine = OmegaSimulationEngine()
    games = get_todays_games(league)
    edges = []

    for game in games:
        home = game["home_team"]["name"]
        away = game["away_team"]["name"]
        market_odds = game.get("odds", {})

        # Run simulation
        sim_result = engine.run_fast_game_simulation(
            home_team=home,
            away_team=away,
            league=league,
            n_iterations=1000
        )

        # Skip games with incomplete data
        if not sim_result.get("success"):
            continue

        true_prob_home = sim_result["home_win_prob"] / 100

        # Calculate edge vs market
        if market_odds.get("spread_home"):
            market_implied = implied_probability(market_odds["spread_home"])
            edge = edge_percentage(true_prob_home, market_implied)

            if abs(edge) > edge_threshold * 100:
                # Determine confidence tier based on data quality
                tier = "A" if sim_result.get("iterations", 0) >= 1000 else "B"

                stake = recommend_stake(
                    true_prob=true_prob_home,
                    odds=market_odds["spread_home"],
                    bankroll=bankroll,
                    confidence_tier=tier
                )

                edges.append({
                    "matchup": f"{away} @ {home}",
                    "selection": f"{home} spread",
                    "true_prob": round(true_prob_home, 3),
                    "market_implied": round(market_implied, 3),
                    "edge_pct": round(edge, 1),
                    "recommended_units": stake["units"],
                    "confidence_tier": tier,
                    "predicted_spread": sim_result["predicted_spread"],
                    "predicted_total": sim_result["predicted_total"]
                })

    # Sort by edge, descending
    return sorted(edges, key=lambda x: abs(x["edge_pct"]), reverse=True)
```

### Query Examples for AI Agents

| User Query | Agent Action |
|------------|--------------|
| "What are the best NBA bets today?" | Run `find_daily_edges("NBA", bankroll)` → Return top 3-5 edges |
| "Analyze Lakers vs Warriors" | Run `run_game_simulation("Lakers", "Warriors", "NBA")` → Full breakdown |
| "Should I bet LeBron over 25.5 points?" | Run `run_player_prop_simulation("LeBron James", ...)` → Compare to line |
| "Show me all edges above 5%" | Filter simulation results by `edge_pct > 5` |
| "What's the true probability of Bills winning?" | Run NFL simulation → Return `true_prob` with confidence interval |

### Data Validation Rules

The engine enforces **NO DEFAULTS** policy:

- If `off_rating`, `def_rating`, or `pace` is missing → Game is **SKIPPED**
- If player has no historical stats → Player prop is **SKIPPED**
- Skipped items are logged to `data/logs/data_integrity_log.json`

An AI agent should **report skipped games** to the user, not hide them:

```text
"3 games were skipped due to incomplete data:
 - Magic vs Hornets (Missing: Magic defensive rating)
 - Jazz vs Spurs (Missing: Both teams pace data)"
```

---

## Roadmap

### Phase 1: Foundation ✓ (Completed)

- [x] **Hybrid Schema**: PostgreSQL with JSONB for sport-agnostic box scores
- [x] **Entity Resolution**: `canonical_names` table + alias mapping service
- [x] **Simulation Engine**: Monte Carlo with Poisson/Normal distribution selection
- [x] **Markov Engine**: Play-by-play simulation with player stat accumulation
- [x] **Kelly Staking**: Quarter-Kelly with tier caps and risk controls
- [x] **Odds Evaluation**: EV calculations and edge detection

### Phase 2: The "Validator-Lab" 🔄 (In Progress)

The simulation engine must **earn its confidence**. This phase builds the backtesting infrastructure:

- [ ] **Prediction Ledger**: Store all model predictions with timestamps
- [ ] **Outcome Reconciliation**: Automated grading against final scores
- [ ] **Calibration Metrics**:
  - Brier Score (probability accuracy)
  - Log Loss (confidence calibration)
  - Hit Rate by Edge Bucket (5%+ edge should hit >55%)
- [ ] **Parameter Tuning**: Auto-calibrator adjusts Markov transition probabilities based on historical performance
- [ ] **CLV Tracking**: Compare entry odds vs closing line to validate edge detection

### Phase 3: The Analyst Interface 📋 (Planned)

Deep integration with LLMs for complex analytical queries:

- [ ] **Text-to-SQL Layer**: Natural language → JSONB queries
  - *"Show me all QBs with >10% variance in passing yards vs market lines"*
  - *"Which players have hit their prop over in 4+ of last 5 games?"*
- [ ] **Contextual Narratives**: Simulation results + injury reports + historical matchups → Written analysis
- [ ] **Scenario Modeling**: "What if Player X is ruled out?" → Re-run simulations with adjusted rosters
- [ ] **Portfolio View**: Track aggregate exposure across correlated bets

---

## Key Files Reference

| Path | Purpose |
|------|---------|
| `src/simulation/simulation_engine.py` | Monte Carlo engine, `OmegaSimulationEngine` class |
| `src/simulation/markov_engine.py` | Play-by-play Markov simulator |
| `src/betting/kelly_staking.py` | Quarter-Kelly stake recommendations |
| `src/betting/odds_eval.py` | EV/edge calculations |
| `src/data/schedule_api.py` | ESPN schedule fetching |
| `src/data/stats_ingestion.py` | Team/player context retrieval |
| `src/db/schema.py` | Hybrid Schema (SQLAlchemy 2.0) |
| `src/utils/entity_resolver.py` | Alias → UUID resolution |

---

## Setup

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
# Run example simulation (default: Lakers vs Warriors)
python main.py

# Analyze specific matchup
python main.py --home "Lakers" --away "Warriors" --league NBA

# Output as JSON for programmatic consumption
python main.py --home "Celtics" --away "Heat" --json
```

---

## Supported Leagues

| League | Game Simulation | Player Props | Status |
|--------|-----------------|--------------|--------|
| NBA | ✅ Full | ✅ Full | Production |
| NFL | ✅ Full | ✅ Full | Production |
| NCAAB | ✅ Full | ⚠️ Limited | Beta |
| NCAAF | ✅ Full | ⚠️ Limited | Beta |
| MLB | ⚠️ Basic | ❌ Not yet | Development |
| NHL | ⚠️ Basic | ❌ Not yet | Development |

---

## License

Private repository - authorized use only.

---

> *"The goal is not to predict the future. The goal is to have a more accurate probability distribution than the market."*
