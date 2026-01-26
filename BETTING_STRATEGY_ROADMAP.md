# OmegaSportsAgent: Strategic Roadmap

## Executive Summary

This document outlines a comprehensive strategy to transform OmegaSportsAgent from a solid quantitative betting engine into a professional-grade sports analytics platform. The roadmap is based on methodologies used by elite betting syndicates (Pinnacle, CRIS-backed groups, Starlizard), quantitative hedge funds (Two Sigma Sports, Susquehanna), and academic research in sports analytics.

---

## Part 1: Industry Analysis - What the Best Use

### 1.1 Sharp Book Methodologies

**Pinnacle Sports Model**
- Market-making algorithm that aggregates sharp action
- Closing Line Value (CLV) as primary model validation metric
- Line moves driven by weighted average of known sharps
- Power ratings updated in real-time with Bayesian inference

**Starlizard (Tony Bloom)**
- £50M+ annual profit from proprietary statistical models
- Employs 160+ quants, data scientists, and former traders
- Key innovation: Expected Goals (xG) modeling before mainstream adoption
- Team-specific situational adjustments (travel, rest, motivation)

**CRIS/Bookmaker.eu Sharp Syndicates**
- Closing line as the "truth" - models validated against close
- Steam move detection (rapid line movement = sharp action)
- Contrarian positioning against recreational money
- Market efficiency exploitation (opening vs closing spreads)

### 1.2 Quantitative Hedge Fund Approaches

**Two Sigma Sports Analytics**
- Machine learning ensembles (XGBoost + Neural Nets + Linear Models)
- Alternative data: player tracking (Second Spectrum), social sentiment
- Real-time odds feed processing at millisecond latency
- Kelly Criterion with modern portfolio theory optimization

**Susquehanna International Group (SIG)**
- Options pricing models applied to sports markets
- Implied volatility from line movement patterns
- Arbitrage detection across 40+ sportsbooks
- High-frequency live betting algorithms

**Renaissance Technologies (Reported Approaches)**
- Hidden Markov Models for game state transitions
- Regime detection (blowout vs competitive vs close game)
- Player fatigue modeling from biomechanical data
- Sentiment analysis from sports media corpus

### 1.3 Academic Research Foundations

| Method | Application | Key Paper/Source |
|--------|-------------|------------------|
| Elo Ratings | Team strength, can be adapted for players | Arpad Elo, FiveThirtyEight implementations |
| Bradley-Terry | Head-to-head probability estimation | Bradley & Terry (1952) |
| Poisson Regression | Score prediction, prop modeling | Maher (1982), Dixon & Coles (1997) |
| Bayesian Hierarchical | Small sample adjustments, injury impact | Gelman et al., sports applications |
| MCMC Simulation | Full distribution estimation | Stern (1991), Glickman |
| Expected Points Added (EPA) | Play value quantification | Burke (2014), nflfastR |
| Win Probability Added (WPA) | Clutch performance measurement | Tango et al. |
| Player Tracking Metrics | RAPTOR, EPM, DARKO (NBA) | FiveThirtyEight, Dunks & Threes |

### 1.4 Modern ML/AI Techniques

**Gradient Boosting (XGBoost, LightGBM, CatBoost)**
- Industry standard for tabular sports data
- Handles feature interactions automatically
- Excellent for player prop modeling

**Deep Learning**
- LSTMs for sequential play-by-play modeling
- Transformers for player embedding (career trajectory)
- Graph Neural Networks for team chemistry modeling

**Reinforcement Learning**
- Dynamic Kelly optimization (bankroll as MDP)
- Live betting decision timing
- Portfolio rebalancing under uncertainty

---

## Part 2: Current State Assessment

### 2.1 What OmegaSportsAgent Does Well

| Component | Status | Notes |
|-----------|--------|-------|
| Monte Carlo Simulation | ✅ Solid | 10K iterations, auto-distribution selection |
| Markov Props Engine | ✅ Good | 50K iterations, data validation |
| Edge Calculation | ✅ Functional | Platt + shrinkage transforms |
| Data Fallback Chain | ✅ Robust | ESPN → BDL → Perplexity → Cache |
| Kelly Staking | ⚠️ Basic | Static quarter-Kelly |
| Calibration System | ⚠️ Manual | Lab exists but not automated |

### 2.2 Critical Gaps vs Industry Leaders

| Gap | Current State | Industry Standard | Impact |
|-----|--------------|-------------------|--------|
| **CLV Tracking** | None | Core validation metric | Can't measure model quality |
| **Real-Time Updates** | Daily batch | Continuous | Miss injury/lineup value |
| **ML Models** | None | XGBoost/Neural ensembles | Lower prediction accuracy |
| **Sharp/Public Splits** | None | 70%+ coverage | Miss contrarian value |
| **Book-Specific Lines** | Single line | Multi-book arbitrage | Leave money on table |
| **Player Tracking Data** | None | Second Spectrum integration | Inferior prop modeling |
| **Automated Calibration** | Manual | Continuous refit | Stale probability estimates |
| **Uncertainty Quantification** | None | Confidence intervals | Overconfident Kelly sizing |

### 2.3 Usage Pattern Analysis

Based on recent activity, the system is being used for:
1. **Daily NBA prop betting** (primary use case)
2. **Multi-sport coverage** (NFL, MLB, NHL when in season)
3. **Tiered confidence reporting** (A/B/C picks)
4. **Manual review workflow** (narrative + categorical summaries)

---

## Part 3: Strategic Roadmap

### Phase 1: Foundation Strengthening (4-6 weeks)

**Goal**: Fix critical gaps that limit model validation and decision quality

#### 1.1 Closing Line Value (CLV) Tracking System

**Why**: CLV is the gold standard for model validation. Profitable bettors consistently beat the closing line.

```python
# Proposed CLV calculation
clv = (closing_implied_prob - opening_implied_prob_at_bet_time) / opening_implied_prob_at_bet_time * 100

# Target metrics
# - CLV > 0%: Model has predictive power
# - CLV > 2%: Strong edge (sharp-level)
# - CLV > 4%: Elite performance
```

**Implementation Tasks**:
1. Store bet placement timestamp + odds in BetLog
2. Fetch closing lines at game start (new API call)
3. Calculate CLV per bet and aggregate by market type
4. Add CLV columns to predictions.json and BetLog.csv
5. Create CLV dashboard/report in daily narrative

**Files to Modify**:
- `src/betting/bet_tracker.py` (new file)
- `src/data/odds_ingestion.py` (add closing line fetch)
- `data/exports/BetLog.csv` (add columns)

#### 1.2 Real-Time Odds Monitoring

**Why**: Lines move. A 3% edge at 9 AM may be -2% by noon.

**Implementation Tasks**:
1. Create odds snapshot service (every 15 minutes for active games)
2. Detect steam moves (rapid line changes > 0.5 points in <30 min)
3. Alert system for significant line movement
4. Stale odds detection before bet logging

**New Components**:
```
src/data/
├── odds_monitor.py         # Real-time odds polling
├── steam_detector.py       # Sharp action identification
└── line_movement_alert.py  # Notification system
```

#### 1.3 Database Migration

**Why**: JSON/CSV don't scale. Need relational queries for analysis.

**Schema Design**:
```sql
-- Core tables
bets (id, game_id, market_type, pick, odds, model_prob, implied_prob, edge, ev, tier, status, result, clv)
games (id, league, home_team, away_team, start_time, final_score_home, final_score_away)
odds_snapshots (id, game_id, market_type, book, odds, timestamp)
calibration_runs (id, timestamp, params, validation_metrics)
model_predictions (id, game_id, market_type, predicted_prob, actual_outcome)
```

**Implementation**:
- Complete Alembic migrations in `src/db/`
- Add SQLAlchemy ORM models
- Create data export scripts for historical migration
- Build query layer for analytics

#### 1.4 Automated Calibration Pipeline

**Why**: Markets evolve. Manual calibration lags reality.

**Process**:
```
Weekly Calibration Cycle:
1. Pull last 30 days of bet outcomes
2. Calculate reliability diagrams per market type
3. Refit Platt scaling parameters (a, b)
4. Validate on holdout set
5. Auto-deploy if improvement > threshold
6. Log all calibration runs for audit
```

**Files to Create**:
- `lab/automation/weekly_calibration.py`
- `lab/automation/calibration_validator.py`
- `config/calibration/calibration_history/` (versioned params)

---

### Phase 2: Advanced Modeling (6-10 weeks)

**Goal**: Integrate machine learning and advanced statistical methods

#### 2.1 XGBoost Ensemble Layer

**Why**: XGBoost consistently outperforms simple Monte Carlo on tabular sports data.

**Model Architecture**:
```
Input Features:
├── Team metrics (ORtg, DRtg, pace, Four Factors)
├── Player metrics (usage, efficiency, minutes projection)
├── Situational (rest days, travel distance, altitude)
├── Historical (H2H record, recent form last 10 games)
├── Market (opening line, current line, line movement)
└── Contextual (playoff implications, rivalry, national TV)

Output: Probability distribution per market type
```

**Implementation**:
```python
# Proposed ensemble structure
class EnsemblePredictor:
    def __init__(self):
        self.monte_carlo = MonteCarloEngine()
        self.xgboost = XGBoostModel()
        self.markov = MarkovEngine()

    def predict(self, game_data):
        mc_prob = self.monte_carlo.simulate(game_data)
        xgb_prob = self.xgboost.predict(game_data)
        markov_prob = self.markov.simulate(game_data)

        # Weighted ensemble (weights from calibration)
        return self.blend([mc_prob, xgb_prob, markov_prob],
                          weights=[0.3, 0.5, 0.2])
```

**Training Pipeline**:
1. Historical data collection (3+ seasons)
2. Feature engineering pipeline
3. Walk-forward cross-validation
4. Hyperparameter optimization (Optuna)
5. Production model registry

#### 2.2 Bayesian Hierarchical Modeling

**Why**: Better handles small samples (early season, player injuries, team changes).

**Use Cases**:
- Player projection with limited games after trade
- Team performance with new coach
- Rookie season projections
- Injury return performance estimation

**Implementation**:
```python
# PyMC implementation for player projection
with pm.Model() as player_model:
    # League-wide prior
    league_mean = pm.Normal('league_mean', mu=20, sigma=5)

    # Player-specific deviation
    player_offset = pm.Normal('player_offset', mu=0, sigma=3)

    # Observed performance
    points = pm.Normal('points',
                       mu=league_mean + player_offset,
                       sigma=5,
                       observed=player_data)
```

#### 2.3 Player Tracking Integration

**Why**: Second Spectrum / NBA Advanced Stats provide ground truth for player performance.

**Data Sources**:
- NBA Stats API (tracking data)
- PBP Stats (play-by-play parsing)
- Cleaning the Glass (shot quality metrics)

**Key Metrics to Integrate**:
```
NBA:
├── True Shooting Attempts (TSA)
├── Shot Quality (expected eFG%)
├── Defensive Rating (on/off)
├── Box Creation
└── Estimated Plus-Minus (EPM)

NFL:
├── Expected Points Added (EPA)
├── Completion Probability Over Expected (CPOE)
├── Separation metrics
├── Yards After Catch Over Expected
└── Rush Yards Over Expected (RYOE)
```

#### 2.4 Uncertainty Quantification

**Why**: Point estimates hide risk. Need confidence intervals for proper Kelly sizing.

**Implementation**:
```python
# Bootstrap confidence intervals
def predict_with_uncertainty(game_data, n_bootstrap=1000):
    predictions = []
    for _ in range(n_bootstrap):
        sample = bootstrap_sample(game_data)
        pred = model.predict(sample)
        predictions.append(pred)

    return {
        'point_estimate': np.mean(predictions),
        'ci_lower': np.percentile(predictions, 2.5),
        'ci_upper': np.percentile(predictions, 97.5),
        'std': np.std(predictions)
    }

# Adjusted Kelly with uncertainty
def uncertainty_adjusted_kelly(edge, odds, uncertainty):
    base_kelly = edge / (odds - 1)
    # Penalize high uncertainty
    penalty = 1 - (uncertainty / 0.10)  # 10% std = 0 bet
    return max(0, base_kelly * penalty)
```

---

### Phase 3: Market Intelligence (8-12 weeks)

**Goal**: Understand market dynamics and exploit inefficiencies

#### 3.1 Sharp vs Public Money Tracking

**Why**: Fading public and following sharps is a proven edge source.

**Data Sources**:
- Action Network API (public betting %)
- Pregame.com (sharp reports)
- Sports Insights (steam moves)
- Scraped data from betting Twitter/forums

**Implementation**:
```python
class MarketIntelligence:
    def get_sharp_signals(self, game_id):
        return {
            'public_spread_pct': 0.72,  # 72% on favorite
            'money_spread_pct': 0.45,   # 45% money on favorite
            'reverse_line_movement': True,  # Line moved against public
            'steam_move_detected': False,
            'sharp_consensus': 'underdog',
            'signal_strength': 0.85
        }

    def contrarian_edge(self, public_pct, money_pct):
        # RLM (Reverse Line Movement) indicator
        if public_pct > 0.65 and money_pct < 0.50:
            return 'strong_fade'  # Sharp action against public
        return 'neutral'
```

#### 3.2 Cross-Book Arbitrage Detection

**Why**: Different books = different lines = arbitrage opportunities.

**Supported Books** (priority order):
1. Pinnacle (sharpest lines, benchmark)
2. Circa Sports (sharp-friendly)
3. BetMGM, DraftKings, FanDuel (recreational)
4. Regional books (often stale)

**Arbitrage Scanner**:
```python
def find_arbitrage(game_id, market_type):
    all_odds = fetch_all_book_odds(game_id, market_type)

    best_home = max(all_odds, key=lambda x: x['home_odds'])
    best_away = max(all_odds, key=lambda x: x['away_odds'])

    implied_total = 1/best_home['home_odds'] + 1/best_away['away_odds']

    if implied_total < 1.0:
        return {
            'arbitrage': True,
            'profit_pct': (1 - implied_total) * 100,
            'home_book': best_home['book'],
            'away_book': best_away['book']
        }
    return {'arbitrage': False}
```

#### 3.3 Line Shopping Optimization

**Why**: Getting the best line is often worth more than model improvements.

**Implementation**:
```python
def optimal_line_shop(bet_recommendation):
    all_odds = get_all_book_odds(bet_recommendation)

    best_odds = max(all_odds.values())
    worst_odds = min(all_odds.values())

    # Calculate line shopping value (LSV)
    lsv = (implied_prob(worst_odds) - implied_prob(best_odds)) * 100

    return {
        'recommended_book': best_book,
        'best_odds': best_odds,
        'line_shopping_value': lsv,  # Often 1-3% edge improvement
        'all_lines': all_odds
    }
```

#### 3.4 Steam Move Detection & Alerts

**Why**: Steam moves indicate sharp action. Get there first.

**Detection Algorithm**:
```python
def detect_steam(game_id, market_type):
    history = get_line_history(game_id, market_type, last_hours=4)

    for i in range(1, len(history)):
        time_delta = (history[i].timestamp - history[i-1].timestamp).seconds
        line_delta = abs(history[i].line - history[i-1].line)

        # Steam criteria: >0.5 point move in <30 minutes
        if time_delta < 1800 and line_delta >= 0.5:
            return {
                'steam_detected': True,
                'direction': 'home' if history[i].line < history[i-1].line else 'away',
                'magnitude': line_delta,
                'time_seconds': time_delta
            }
    return {'steam_detected': False}
```

---

### Phase 4: Operational Excellence (10-14 weeks)

**Goal**: Production-ready system with monitoring and automation

#### 4.1 Real-Time Dashboard

**Components**:
- Daily P&L tracker with running total
- Hit rate by market type, tier, league
- CLV performance tracking
- Model confidence vs actual outcomes
- Bankroll growth visualization

**Tech Stack**:
- Streamlit or Plotly Dash for web UI
- PostgreSQL for data backend
- Redis for real-time odds caching
- Celery for async task processing

#### 4.2 Alerting & Monitoring

**Alert Types**:
```yaml
alerts:
  - name: "Data Source Down"
    condition: "api_errors > 3 in 1 hour"
    severity: critical

  - name: "CLV Negative"
    condition: "rolling_7d_clv < -1%"
    severity: warning

  - name: "Steam Move Detected"
    condition: "line_movement > 0.5 in 30min"
    severity: info

  - name: "Model Degradation"
    condition: "rolling_30d_roi < -5%"
    severity: critical
```

#### 4.3 Backtesting Infrastructure

**Why**: Can't deploy new models without validation.

**Framework**:
```python
class Backtester:
    def __init__(self, start_date, end_date, initial_bankroll=10000):
        self.start_date = start_date
        self.end_date = end_date
        self.bankroll = initial_bankroll

    def run(self, strategy, model):
        results = []
        for date in self.date_range():
            games = self.get_historical_games(date)
            predictions = model.predict(games)
            bets = strategy.select_bets(predictions)
            outcomes = self.get_outcomes(games)

            daily_pnl = self.calculate_pnl(bets, outcomes)
            self.bankroll += daily_pnl

            results.append({
                'date': date,
                'bets': len(bets),
                'pnl': daily_pnl,
                'bankroll': self.bankroll
            })
        return BacktestResults(results)
```

**Validation Requirements**:
- Walk-forward optimization (no future data leakage)
- Out-of-sample testing (minimum 20% holdout)
- Monte Carlo simulation of returns
- Drawdown analysis and risk metrics

#### 4.4 CI/CD Pipeline

**Automated Testing**:
```yaml
# .github/workflows/test.yml
name: Test Pipeline
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run unit tests
        run: pytest tests/unit/
      - name: Run integration tests
        run: pytest tests/integration/
      - name: Validate calibration
        run: python -m lab.validation.validate_calibration
      - name: Check model performance
        run: python -m lab.validation.model_sanity_check
```

---

### Phase 5: Advanced Strategies (14-20 weeks)

**Goal**: Implement sophisticated strategies used by professional operations

#### 5.1 Dynamic Kelly Optimization

**Why**: Static quarter-Kelly leaves money on table or takes excess risk.

**Implementation**:
```python
class DynamicKelly:
    def __init__(self, base_fraction=0.25):
        self.base_fraction = base_fraction

    def calculate_fraction(self, edge, confidence_interval, bankroll_state):
        # Base Kelly
        base = edge / (decimal_odds - 1)

        # Confidence adjustment (wider CI = lower fraction)
        ci_width = confidence_interval['upper'] - confidence_interval['lower']
        ci_penalty = max(0, 1 - ci_width / 0.20)

        # Bankroll state adjustment
        if bankroll_state['drawdown'] > 0.10:
            drawdown_penalty = 0.5
        else:
            drawdown_penalty = 1.0

        # Correlation adjustment (many similar bets = reduce each)
        correlation_penalty = 1 / (1 + bankroll_state['correlated_exposure'])

        final_fraction = (base * self.base_fraction *
                         ci_penalty * drawdown_penalty * correlation_penalty)

        return min(final_fraction, 0.05)  # Hard cap 5% of bankroll
```

#### 5.2 Portfolio Optimization

**Why**: Bets are correlated. Optimize the portfolio, not individual bets.

**Mean-Variance Optimization**:
```python
from scipy.optimize import minimize

def optimize_portfolio(bets, bankroll):
    n = len(bets)
    expected_returns = np.array([b['expected_value'] for b in bets])
    cov_matrix = estimate_covariance(bets)

    def objective(weights):
        portfolio_return = np.dot(weights, expected_returns)
        portfolio_variance = np.dot(weights.T, np.dot(cov_matrix, weights))
        # Maximize Sharpe ratio
        return -portfolio_return / np.sqrt(portfolio_variance)

    constraints = [
        {'type': 'eq', 'fun': lambda w: np.sum(w) - 1},  # Weights sum to 1
        {'type': 'ineq', 'fun': lambda w: w}  # All weights >= 0
    ]

    result = minimize(objective, x0=np.ones(n)/n, constraints=constraints)
    return result.x * bankroll
```

#### 5.3 Live Betting Engine

**Why**: Live markets are less efficient. More edge opportunities.

**Architecture**:
```
Live Betting Pipeline:
1. Real-time game state ingestion (play-by-play)
2. Win probability model update (every play)
3. Compare to live market odds
4. Execute if edge > threshold AND liquidity available
5. Track slippage and execution quality
```

**Considerations**:
- Latency requirements (<500ms decision loop)
- Odds staleness detection
- Position limits (max exposure per game)
- Hedging logic for locked-in profit

#### 5.4 Derivative Strategies

**Alternative Betting Markets**:
1. **SGP (Same Game Parlays)** - Often mispriced due to correlation miscalculation
2. **Player Props Arbitrage** - Different limits across books
3. **Futures Hedging** - Lock in profit as season progresses
4. **Alt Lines** - Buy/sell points when market misprices

---

## Part 4: Implementation Priorities

### Immediate Actions (This Week)

1. **Add CLV tracking to BetLog.csv** - Critical for model validation
2. **Implement closing line fetch** - Required for CLV calculation
3. **Create bet placement timestamp logging** - Foundation for all analysis
4. **Set up PostgreSQL database** - Move off JSON/CSV

### Short-Term (Next 30 Days)

1. **Automated weekly calibration pipeline**
2. **XGBoost model prototype for NBA spreads**
3. **Real-time odds monitoring (15-min snapshots)**
4. **Basic dashboard with daily P&L**

### Medium-Term (60-90 Days)

1. **Full ML ensemble (MC + XGBoost + Markov)**
2. **Sharp/public money integration**
3. **Multi-book line shopping**
4. **Uncertainty quantification for all predictions**

### Long-Term (6+ Months)

1. **Live betting engine**
2. **Portfolio optimization framework**
3. **Player tracking data integration**
4. **Full backtesting infrastructure**

---

## Part 5: Success Metrics

### Model Quality Metrics

| Metric | Target | Current | Notes |
|--------|--------|---------|-------|
| CLV | > 2% | Not tracked | Primary validation |
| Log Loss | < 0.68 | Unknown | Calibration quality |
| Brier Score | < 0.24 | Unknown | Probability accuracy |
| AUC-ROC | > 0.55 | Unknown | Discrimination power |

### Financial Metrics

| Metric | Target | Current | Notes |
|--------|--------|---------|-------|
| ROI | > 3% | Unknown | After vig |
| Hit Rate | > 52% | Unknown | Depends on odds |
| Max Drawdown | < 20% | Unknown | Risk management |
| Sharpe Ratio | > 1.0 | Unknown | Risk-adjusted returns |

### Operational Metrics

| Metric | Target | Current | Notes |
|--------|--------|---------|-------|
| Data Uptime | > 99% | ~95% | API reliability |
| Bet Execution | < 5 min | Manual | Time to place |
| Model Latency | < 30 sec | ~60 sec | Per-game prediction |

---

## Part 6: Technology Stack Recommendations

### Current Stack (Keep)
- Python 3.10+ (core language)
- Pydantic (data validation)
- NumPy/Pandas (numerical computing)
- SQLAlchemy (ORM)

### Additions Recommended

| Category | Tool | Purpose |
|----------|------|---------|
| ML Framework | scikit-learn, XGBoost | Model training |
| Bayesian | PyMC, Stan | Hierarchical models |
| Dashboard | Streamlit | Real-time monitoring |
| Task Queue | Celery + Redis | Async processing |
| Monitoring | Prometheus + Grafana | System health |
| CI/CD | GitHub Actions | Automated testing |
| Database | PostgreSQL + TimescaleDB | Time-series odds data |

---

## Part 7: Risk Management

### Model Risks
- **Overfitting**: Mitigate with walk-forward validation
- **Regime change**: Markets evolve; continuous recalibration required
- **Data quality**: Garbage in = garbage out; robust validation

### Operational Risks
- **API downtime**: Multiple fallback sources
- **Rate limits**: Caching and request throttling
- **Data staleness**: Timestamp validation before use

### Financial Risks
- **Drawdown**: Dynamic Kelly reduces exposure in losing streaks
- **Correlation**: Portfolio optimization limits correlated bets
- **Bankroll depletion**: Hard stop-loss at 30% drawdown

---

## Conclusion

OmegaSportsAgent has a solid foundation with Monte Carlo simulation, Markov modeling, and edge detection. The path to professional-grade performance requires:

1. **Validation infrastructure** (CLV tracking, backtesting)
2. **Advanced models** (ML ensemble, Bayesian methods)
3. **Market intelligence** (sharp tracking, line shopping)
4. **Operational excellence** (monitoring, automation)

The roadmap prioritizes high-impact, foundational improvements first (CLV, database, calibration) before advancing to sophisticated strategies (live betting, portfolio optimization).

**Target State**: A fully automated, self-calibrating sports analytics engine that consistently beats closing lines and generates sustainable positive ROI across all supported markets.

---

*Document Version: 1.0*
*Created: 2026-01-26*
*Last Updated: 2026-01-26*
