# Database Integration Examples

This directory contains practical, working examples that demonstrate how to use the SQLite database for sports betting analysis.

## 📚 Available Examples

### Example 1: Basic Queries
**File:** `example_01_basic_queries.py`

Learn the fundamentals of database access:
- Connecting to the SQLite database
- Querying games by sport and date
- Accessing betting lines data
- Filtering by team or date range
- Running aggregation queries

**Run it:**
```bash
python examples/example_01_basic_queries.py
```

**Prerequisites:** 
- Collect some data first: `python scripts/collect_historical_sqlite.py --sports NBA --start-year 2023 --end-year 2024`

---

### Example 2: Player Props and Statistics
**File:** `example_02_player_props.py`

Learn to work with player performance data:
- Querying player props
- Calculating hit rates
- Analyzing player performance trends
- Finding top performers
- Measuring prop line accuracy

**Run it:**
```bash
python examples/example_02_player_props.py
```

**Prerequisites:** 
- Collect data with player props: `python scripts/collect_historical_sqlite.py --sports NBA --start-year 2023 --end-year 2024`

---

### Example 3: Simple Backtesting
**File:** `example_03_backtesting.py`

Learn to backtest betting strategies:
- Testing simple betting strategies
- Calculating ROI and win rates
- Analyzing performance over time
- Understanding the importance of edge detection

**Run it:**
```bash
python examples/example_03_backtesting.py
```

**Prerequisites:** 
- Collect complete data: `python scripts/collect_historical_sqlite.py --sports NBA --start-year 2023 --end-year 2024`

---

## 🚀 Quick Start

### 1. Collect Sample Data
```bash
# Collect 2 years of NBA data (faster for testing)
python scripts/collect_historical_sqlite.py \
    --sports NBA \
    --start-year 2023 \
    --end-year 2024 \
    --workers 2
```

### 2. Run Examples
```bash
# Run all examples in order
python examples/example_01_basic_queries.py
python examples/example_02_player_props.py
python examples/example_03_backtesting.py
```

### 3. Modify and Experiment
- Open any example file
- Modify the queries to explore different data
- Try different filters, aggregations, or analyses
- Learn by doing!

---

## 📊 What Each Example Teaches

| Example | Key Concepts | Use Cases |
|---------|--------------|-----------|
| **01: Basic Queries** | SQL basics, database connection, filtering | Understanding your data |
| **02: Player Props** | Aggregations, joins, performance analysis | Player-focused strategies |
| **03: Backtesting** | Strategy testing, ROI calculation, time series | Validating betting strategies |

---

## 💡 Tips for Learning

### Start Simple
1. Run Example 1 first to understand the database structure
2. Then move to Example 2 for more complex queries
3. Finally try Example 3 to see practical applications

### Modify and Experiment
Each example includes comments explaining what each query does. Try:
- Changing the date ranges
- Filtering by different teams or players
- Adding new calculations or metrics
- Combining multiple queries

### Use These as Templates
These examples are designed to be copied and modified for your own analysis:
```python
# Copy example_01_basic_queries.py
cp examples/example_01_basic_queries.py my_custom_analysis.py

# Modify it for your specific needs
nano my_custom_analysis.py
```

---

## 🔍 Database Schema Reference

### Main Tables

**games**
```sql
game_id, date, sport, league, season,
home_team, away_team, home_score, away_score,
moneyline_home, moneyline_away,
spread_line, spread_home_odds, spread_away_odds,
total_line, total_over_odds, total_under_odds,
home_team_stats, away_team_stats (JSON)
```

**player_props**
```sql
prop_id, game_id, date, sport,
player_name, player_team, opponent_team,
prop_type, line, actual_value
```

**odds_history**
```sql
game_id, bookmaker, market_type, timestamp,
home_odds, away_odds, line
```

---

## 🎯 Common Queries

### Get all NBA games from 2024
```python
cursor.execute("""
    SELECT * FROM games 
    WHERE sport = 'NBA' AND date LIKE '2024%'
""")
```

### Get Lakers home games with spreads
```python
cursor.execute("""
    SELECT * FROM games 
    WHERE home_team LIKE '%Lakers%' 
      AND spread_line IS NOT NULL
""")
```

### Get LeBron James points props
```python
cursor.execute("""
    SELECT * FROM player_props 
    WHERE player_name = 'LeBron James' 
      AND prop_type = 'points'
""")
```

### Calculate win rate by month
```python
cursor.execute("""
    SELECT strftime('%Y-%m', date) as month,
           COUNT(*) as games,
           SUM(CASE WHEN home_score > away_score THEN 1 ELSE 0 END) as home_wins
    FROM games
    WHERE sport = 'NBA'
    GROUP BY month
""")
```

---

## 🐛 Troubleshooting

### "No such table: games"
**Solution:** You need to collect data first:
```bash
python scripts/collect_historical_sqlite.py --sports NBA --start-year 2023 --end-year 2024
```

### "Database is locked"
**Solution:** Close any other programs accessing the database, or wait for collection to finish.

### "No data returned"
**Solution:** Check if data exists for your query parameters:
```bash
sqlite3 data/sports_data.db "SELECT COUNT(*) FROM games WHERE sport='NBA';"
```

### "Module not found"
**Solution:** Run examples from the repository root:
```bash
cd /path/to/OmegaSports-Validation-Lab
python examples/example_01_basic_queries.py
```

---

## 📖 Related Documentation

- **[START_HERE.md](../START_HERE.md)** - Repository overview
- **[DATABASE_STORAGE_GUIDE.md](../DATABASE_STORAGE_GUIDE.md)** - Complete database documentation
- **[scripts/README.md](../scripts/README.md)** - Data collection scripts
- **[SQLITE_MIGRATION_COMPLETE.md](../SQLITE_MIGRATION_COMPLETE.md)** - Database architecture details

---

## 🎓 Next Steps

After working through these examples, you're ready to:

1. **Run Module 1**: Edge threshold calibration
   ```bash
   python run_all_modules.py --module 01
   ```

2. **Build Custom Analysis**: Use examples as templates for your own queries

3. **Explore Advanced Modules**: Check out other experimental modules in `modules/`

4. **Read Full Documentation**: See [DATABASE_STORAGE_GUIDE.md](../DATABASE_STORAGE_GUIDE.md) for complete API reference

---

**Questions?** See [START_HERE.md](../START_HERE.md) for help navigating the repository.
