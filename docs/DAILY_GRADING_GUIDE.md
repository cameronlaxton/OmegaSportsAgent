# Daily Grading & Metrics Update Workflow

**Complete Guide for Task 2: Grade pending bets, update logs, and track cumulative metrics**

---

## Overview

The **Daily Grading Workflow** automates the process of:

1. **Fetching Game Results** - Scrape final scores and player stats from ESPN/NBA/NFL APIs
2. **Grading Pending Bets** - Compare predictions vs actual outcomes, determine Win/Loss/Push
3. **Updating Cumulative Logs** - Update JSON predictions, CSV bet log, and metrics history

No new daily files are created. All results are appended to existing cumulative logs.

---

## Quick Start

### Option A: Command Line (Recommended)

```bash
# Grade yesterday's bets (analyzes all pending bets from yesterday)
python -m omega.workflows.daily_grading

# Grade specific date
python -m omega.workflows.daily_grading --date 2026-01-06

# Grade and save report
python -m omega.workflows.daily_grading --date 2026-01-06 --output outputs/grading_report.json
```

### Option B: Python Module

```python
from omega.workflows.daily_grading import DailyGradingWorkflow

# Initialize workflow for yesterday
workflow = DailyGradingWorkflow()

# Or specify date
workflow = DailyGradingWorkflow(analysis_date="2026-01-06")

# Run complete workflow
report = workflow.run_complete_workflow()

print(f"Graded {report['bets_graded']} bets")
print(f"Profit/Loss: ${report['summary']['total_profit_loss']}")
print(f"ROI: {report['summary']['roi']}")
```

### Option C: Scheduled via Scheduler

```bash
# Automatically graded at 3am ET via scheduler.py results command
python omega/workflows/scheduler.py results
```

---

## Architecture

### Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│  STEP 1: FETCH GAME RESULTS                                │
│  ────────────────────────────────────────────────────────   │
│  - Get final scores (ESPN API)                              │
│  - Get box scores (ESPN, Basketball-Reference, etc)         │
│  - Get player stats (NBA.com, NFL.com)                      │
│                                                              │
│  OUTPUT: GameResults dict with:                             │
│    - games: {game_id -> score, status, box_score}           │
│    - player_stats: {player_name -> stats}                   │
└───────────────────────────────────┬───────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 2: GRADE PENDING BETS                                │
│  ────────────────────────────────────────────────────────   │
│  - Load data/logs/predictions.json                          │
│  - Find all bets with status: "pending"                     │
│  - Match each bet to actual game result                     │
│  - Determine Win/Loss/Push/Void                             │
│  - Calculate profit_loss and payout                         │
│                                                              │
│  OUTPUT: graded_bets list with:                             │
│    - result: "Win", "Loss", "Push", "Void"                 │
│    - actual_value: float (0.0-1.0)                          │
│    - payout: calculated from odds                           │
│    - profit_loss: payout - stake                            │
│                                                              │
│  ALSO: daily_stats dict:                                    │
│    - wins, losses, pushes, voids                            │
│    - win_rate, roi, avg_edge                                │
└───────────────────────────────────┬───────────────────────────┘
                                     │
              ┌──────────────────────┼──────────────────────┐
              │                      │                      │
              ▼                      ▼                      ▼
┌──────────────────────┐  ┌─────────────────────┐  ┌─────────────────┐
│ STEP 3a:             │  │ STEP 3b:            │  │ STEP 3c:        │
│ predictions.json     │  │ BetLog.csv          │  │ cumulative_     │
│                      │  │                     │  │ metrics_report  │
│ - Update status to   │  │ - Append daily rows │  │ - Add daily     │
│   "graded"           │  │ - Headers auto-     │  │   report        │
│ - Add result, payout │  │   written if new    │  │ - Update        │
│ - Add actual_value   │  │ - 15 columns        │  │   cumulative    │
│ - Add profit_loss    │  │                     │  │   summary       │
└──────────────────────┘  └─────────────────────┘  └─────────────────┘
```

---

## Detailed Workflow Steps

### Step 1: Fetch Game Results

Fetches final scores and statistics for all games on the analysis date.

```python
results = workflow.fetch_game_results()

# Returns:
{
    "date": "2026-01-06",
    "games": {
        "NBA_celtics_vs_pacers_2026_01_06": {
            "league": "NBA",
            "home_team": "Boston Celtics",
            "away_team": "Indiana Pacers",
            "home_score": 118,
            "away_score": 112,
            "status": "Final",
            "box_score": {...}  # Full box score data
        },
        # ... more games
    },
    "player_stats": {
        "Jayson Tatum": {
            "points": 35,
            "rebounds": 8,
            "assists": 3,
            "field_goal_pct": 0.528,
            # ... more stats
        },
        # ... more players
    }
}
```

**Data Sources:**
- [ESPN NBA Schedule](https://www.espn.com/nba/schedule)
- [ESPN NFL Schedule](https://www.espn.com/nfl/schedule)
- [Basketball-Reference](https://www.basketball-reference.com/) - Box scores
- [Pro-Football-Reference](https://www.pro-football-reference.com/) - Box scores
- [NBA.com](https://www.nba.com/) - Player stats
- [NFL.com](https://www.nfl.com/) - Player stats

### Step 2: Grade Pending Bets

Compares each pending bet against actual game results.

```python
graded_bets = workflow.grade_pending_bets(game_results)

# Each graded bet contains:
{
    "bet_id": "bet_12345",
    "date": "2026-01-06",
    "league": "NBA",
    "matchup": "Celtics vs Pacers",
    "bet_type": "moneyline",
    "pick": "Boston Celtics ML",
    "odds": -150,
    "stake": 100.0,
    "edge_pct": 5.2,
    
    # Grading results:
    "result": "Win",
    "actual_value": 1.0,  # 1.0 = win, 0.5 = push, 0.0 = loss
    "payout": 166.67,  # $100 stake + profit
    "profit_loss": 66.67,  # $100 * (100/150)
    "graded_date": "2026-01-07T07:06:26Z",
    "status": "graded"
}
```

#### Bet Type Grading Logic

**Moneyline (ML):**
- Pick: Team name + "ML"
- Win if picked team wins game
- Example: "Boston Celtics ML" wins if Celtics score > Pacers score

**Spread:**
- Pick: Team name + spread direction
- Line: Point spread (e.g., -4.5, +3.0)
- Win if: (home_score - away_score - line) covers the spread
- Example: "Celtics -4.5" wins if Celtics win by 5+ points

**Total (Over/Under):**
- Pick: "Over" or "Under" + total
- Line: Total points (e.g., 220.5)
- Win if: total points > line (over) or < line (under)
- Example: "Over 220.5" wins if total = 221+ points

**Player Props:**
- Pick: "Player Name STAT OVER/UNDER LINE"
- Line: Prop line (e.g., 28.5 points)
- Win if: player stat > line (over) or < line (under)
- Example: "Jayson Tatum Points Over 28.5" wins if Tatum scores 29+

#### Daily Stats Calculated

```python
daily_stats = {
    "date": "2026-01-06",
    "total_bets_graded": 15,
    "wins": 10,
    "losses": 4,
    "pushes": 1,
    "voids": 0,
    "total_stake": 1500.0,
    "total_payout": 1666.50,
    "total_profit_loss": 166.50,
    "win_rate": 0.714,  # 10 wins / 14 decided
    "roi": 0.111,  # 166.50 / 1500.0
    "avg_edge": 4.2  # Average edge of graded bets
}
```

### Step 3a: Update predictions.json

Updates the master prediction log with grading results.

**File:** `data/logs/predictions.json`

```json
[
  {
    "bet_id": "bet_12345",
    "date": "2026-01-06",
    "league": "NBA",
    "matchup": "Celtics vs Pacers",
    "bet_type": "moneyline",
    "pick": "Boston Celtics ML",
    "odds": -150,
    "stake": 100.0,
    "edge_pct": 5.2,
    "confidence": "A",
    
    "status": "graded",  # Changed from "pending"
    "result": "Win",
    "actual_value": 1.0,
    "payout": 166.67,
    "profit_loss": 66.67,
    "graded_date": "2026-01-07T07:06:26Z"
  },
  // ... more bets
]
```

**Changes Made:**
- `status`: "pending" → "graded" (or "voided" if no matching game)
- Add `result`: Win/Loss/Push/Void
- Add `actual_value`: 1.0/0.5/0.0 for win/push/loss
- Add `payout`: Calculated from odds and result
- Add `profit_loss`: payout - stake
- Add `graded_date`: ISO timestamp when graded

### Step 3b: Update BetLog.csv

Appends daily graded bets to the cumulative bet log CSV.

**File:** `data/exports/BetLog.csv`

```csv
bet_id,date,league,matchup,bet_type,pick,line,odds,stake,edge_pct,confidence,result,actual_value,payout,profit_loss,graded_date
bet_12345,2026-01-06,NBA,Celtics vs Pacers,moneyline,Boston Celtics ML,,−150,100.0,5.2,A,Win,1.0,166.67,66.67,2026-01-07T07:06:26Z
bet_12346,2026-01-06,NBA,Celtics vs Pacers,spread,Celtics -4.5,−4.5,−110,100.0,3.1,B,Win,1.0,190.91,90.91,2026-01-07T07:06:26Z
bet_12347,2026-01-06,NBA,Celtics vs Pacers,total,Over 220.5,220.5,−110,50.0,2.5,C,Loss,0.0,0.00,−50.00,2026-01-07T07:06:26Z
```

**Columns:**
- `bet_id`: Unique bet identifier
- `date`: Date bet was placed
- `league`: NBA, NFL, etc.
- `matchup`: Team matchup description
- `bet_type`: moneyline, spread, total, prop
- `pick`: Actual pick text
- `line`: For spread/total bets, the line value
- `odds`: American odds (-150, +120, etc.)
- `stake`: Amount wagered
- `edge_pct`: % edge vs market
- `confidence`: Confidence tier (A, B, C)
- `result`: Win, Loss, Push, Void
- `actual_value`: 1.0, 0.5, 0.0
- `payout`: Total payout (stake + profit)
- `profit_loss`: Net profit or loss
- `graded_date`: When the bet was graded

### Step 3c: Update cumulative_metrics_report.json

Appends today's daily stats to cumulative metrics history.

**File:** `data/logs/cumulative_metrics_report.json`

```json
{
  "daily_reports": [
    {
      "date": "2026-01-06",
      "total_bets_graded": 15,
      "wins": 10,
      "losses": 4,
      "pushes": 1,
      "voids": 0,
      "total_stake": 1500.0,
      "total_payout": 1666.50,
      "total_profit_loss": 166.50,
      "win_rate": 0.714,
      "roi": 0.111,
      "avg_edge": 4.2
    },
    {
      "date": "2026-01-05",
      "total_bets_graded": 12,
      "wins": 8,
      "losses": 3,
      "pushes": 1,
      "voids": 0,
      "total_stake": 1200.0,
      "total_payout": 1314.50,
      "total_profit_loss": 114.50,
      "win_rate": 0.727,
      "roi": 0.0954,
      "avg_edge": 3.8
    }
    // ... more daily reports
  ],
  "cumulative_summary": {
    "report_generated": "2026-01-07T07:06:26Z",
    "total_days_graded": 2,
    "total_bets_graded": 27,
    "total_wins": 18,
    "total_losses": 7,
    "cumulative_win_rate": 0.720,  # 18 / (18+7)
    "total_stake": 2700.0,
    "total_profit_loss": 281.0,
    "cumulative_roi": 0.1041  # 281.0 / 2700.0
  }
}
```

**Summary Metrics:**
- `total_days_graded`: How many daily reports
- `cumulative_win_rate`: Overall win % across all days
- `cumulative_roi`: Overall ROI across all days
- `total_profit_loss`: Total $ profit/loss

---

## Output Report

### Console Output

```
================================================================================
GRADING WORKFLOW SUMMARY
================================================================================
{
  "win_loss_record": "10-4",
  "total_stake": "$1500.00",
  "total_profit_loss": "$166.50",
  "roi": "11.10%",
  "win_rate": "71.43%"
}
================================================================================
```

### JSON Report (Optional)

```bash
python -m omega.workflows.daily_grading --output outputs/grading_report_2026_01_06.json
```

```json
{
  "workflow_date": "2026-01-07T07:06:26Z",
  "analysis_date": "2026-01-06",
  "bets_graded": 15,
  "workflow_status": "COMPLETE",
  "duration_seconds": 12.34,
  "daily_stats": {
    "date": "2026-01-06",
    "total_bets_graded": 15,
    "wins": 10,
    "losses": 4,
    "pushes": 1,
    "voids": 0,
    "total_stake": 1500.0,
    "total_payout": 1666.50,
    "total_profit_loss": 166.50,
    "win_rate": 0.714,
    "roi": 0.111
  },
  "graded_bets": [
    // Individual graded bets...
  ],
  "summary": {
    "win_loss_record": "10-4",
    "total_stake": "$1500.00",
    "total_profit_loss": "$166.50",
    "roi": "11.10%",
    "win_rate": "71.43%"
  }
}
```

---

## Integration with Scheduler

The workflow is automatically invoked by the scheduler at **3:00 AM ET** daily:

```python
# In omega/workflows/scheduler.py
def run_result_updates():
    from omega.workflows.daily_grading import DailyGradingWorkflow
    
    workflow = DailyGradingWorkflow()  # Yesterday's date auto-selected
    report = workflow.run_complete_workflow()
    
    # Workflow updates all three log files automatically
```

---

## Error Handling

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| "No pending bets to grade" | No bets with status="pending" | Check predictions.json has pending bets |
| "No matching game found" | Game not in results | Verify game was played on analysis date |
| "Player stats not available" | Player prop but no stats | Check player name spelling in prop |
| "File not found" | Missing data/logs/ or data/exports/ | Directories auto-created, verify write permissions |
| Partial grades (some pending) | Some games not finalized | Re-run workflow after games complete |

### Validation

The workflow validates:
- ✓ predictions.json exists and is valid JSON
- ✓ Each pending bet has required fields (pick, line, odds, stake)
- ✓ Game results match bet matchups
- ✓ Calculations (payout, profit_loss) are correct
- ✓ Output files are valid JSON/CSV

---

## Examples

### Example 1: Grade Yesterday's Bets

```bash
python -m omega.workflows.daily_grading
```

Output:
```
2026-01-07 07:06:26 - daily_grading - INFO - Initialized daily grading workflow for 2026-01-06
2026-01-07 07:06:26 - daily_grading - INFO - ================================================================================
2026-01-07 07:06:26 - daily_grading - INFO - DAILY GRADING & METRICS UPDATE WORKFLOW
2026-01-07 07:06:26 - daily_grading - INFO - ================================================================================
2026-01-07 07:06:26 - daily_grading - INFO - Step 1: Fetching game results for 2026-01-06...
2026-01-07 07:06:28 - daily_grading - INFO -   ✓ Fetched 10 NBA games
2026-01-07 07:06:29 - daily_grading - INFO -   ✓ Fetched 2 NFL games
2026-01-07 07:06:30 - daily_grading - INFO -   ✓ Fetched player stats (342 players)
2026-01-07 07:06:30 - daily_grading - INFO - Step 1 complete: 12 games, 342 players
2026-01-07 07:06:31 - daily_grading - INFO - Step 2: Grading pending bets...
2026-01-07 07:06:31 - daily_grading - INFO -   Found 15 pending bets to grade
2026-01-07 07:06:32 - daily_grading - INFO - Step 2 complete: Graded 15 bets
2026-01-07 07:06:32 - daily_grading - INFO -   Wins: 10, Losses: 4, Pushes: 1
2026-01-07 07:06:32 - daily_grading - INFO -   Profit/Loss: $166.50
2026-01-07 07:06:32 - daily_grading - INFO - Step 3a: Updating predictions.json...
2026-01-07 07:06:32 - daily_grading - INFO -   ✓ Updated 15 predictions in data/logs/predictions.json
2026-01-07 07:06:33 - daily_grading - INFO - Step 3b: Updating BetLog.csv...
2026-01-07 07:06:33 - daily_grading - INFO -   ✓ Appended 15 rows to data/exports/BetLog.csv
2026-01-07 07:06:33 - daily_grading - INFO - Step 3c: Updating cumulative_metrics_report.json...
2026-01-07 07:06:33 - daily_grading - INFO -   ✓ Updated data/logs/cumulative_metrics_report.json
2026-01-07 07:06:33 - daily_grading - INFO -   Cumulative: 10-4 record, $166.50 profit/loss
2026-01-07 07:06:33 - daily_grading - INFO - ================================================================================
2026-01-07 07:06:33 - daily_grading - INFO - WORKFLOW COMPLETE
2026-01-07 07:06:33 - daily_grading - INFO -   Status: COMPLETE
2026-01-07 07:06:33 - daily_grading - INFO -   Bets Graded: 15
2026-01-07 07:06:33 - daily_grading - INFO -   Duration: 7.3s
2026-01-07 07:06:33 - daily_grading - INFO - ================================================================================

================================================================================
GRADING WORKFLOW SUMMARY
================================================================================
{
  "win_loss_record": "10-4",
  "total_stake": "$1500.00",
  "total_profit_loss": "$166.50",
  "roi": "11.10%",
  "win_rate": "71.43%"
}
================================================================================
```

### Example 2: Grade Specific Date with Report

```bash
python -m omega.workflows.daily_grading --date 2026-01-05 --output outputs/grading_2026_01_05.json
```

Generates report file and prints summary.

### Example 3: Python API

```python
from omega.workflows.daily_grading import DailyGradingWorkflow
import json

# Initialize
workflow = DailyGradingWorkflow(analysis_date="2026-01-06")

# Fetch results
results = workflow.fetch_game_results()
print(f"Games found: {len(results['games'])}")
print(f"Player stats: {len(results['player_stats'])}")

# Grade bets
graded = workflow.grade_pending_bets(results)
print(f"Bets graded: {len(graded)}")

# Update logs
workflow.update_predictions_json()
workflow.update_bet_log_csv()
workflow.update_cumulative_metrics()

# Get report
report = workflow.get_grading_report()
print(json.dumps(report['summary'], indent=2))
```

---

## File Structure After Grading

After running the workflow:

```
data/
├── logs/
│   ├── predictions.json                    # ← UPDATED (status: pending → graded)
│   └── cumulative_metrics_report.json       # ← UPDATED (daily report appended)
└── exports/
    └── BetLog.csv                          # ← UPDATED (rows appended)

outputs/
└── grading_report_2026-01-07T07-06-26Z.json  # ← OPTIONAL (if --output specified)
```

---

## Troubleshooting

### No Bets Graded

**Check 1:** Verify pending bets exist
```bash
cat data/logs/predictions.json | grep '"status": "pending"'
```

**Check 2:** Verify game results were fetched
```python
from omega.workflows.daily_grading import DailyGradingWorkflow
workflow = DailyGradingWorkflow()
results = workflow.fetch_game_results()
print(f"Games: {len(results['games'])}")
```

### Partial Results (Some Games Not Graded)

**Cause:** Some games not finalized by workflow runtime
**Solution:** Re-run workflow after all games have completed

### CSV Format Issues

**Cause:** Excel/sheet application uses different encoding
**Solution:** Open with UTF-8 encoding or use Python for parsing

---

## Next Steps

- **Calibration:** Run `python omega/workflows/scheduler.py calibration` weekly to auto-tune parameters based on outcomes
- **Analysis:** Query `BetLog.csv` for performance analysis (ROI by league, bet type, confidence tier)
- **Backtesting:** Use historical logs to backtest new strategies

---

## API Reference

### DailyGradingWorkflow

```python
class DailyGradingWorkflow:
    def __init__(self, analysis_date: Optional[str] = None)
    def fetch_game_results(self) -> Dict[str, Any]
    def grade_pending_bets(self, game_results: Dict[str, Any]) -> List[Dict[str, Any]]
    def update_predictions_json(self) -> bool
    def update_bet_log_csv(self) -> bool
    def update_cumulative_metrics(self) -> bool
    def get_grading_report(self) -> Dict[str, Any]
    def run_complete_workflow(self) -> Dict[str, Any]
```

### Usage

```python
workflow = DailyGradingWorkflow(analysis_date="2026-01-06")
report = workflow.run_complete_workflow()
```

---

## Summary

The **Daily Grading Workflow** is a complete, automated system for:

✓ Fetching game results from live sports data sources  
✓ Grading pending bets against actual outcomes  
✓ Updating master JSON and CSV logs  
✓ Tracking cumulative performance metrics  
✓ Generating detailed reports  

Run daily (3 AM ET via scheduler or manually) to keep betting logs current and track system performance.
