# Bet Log Template

Record every recommendation here; update closing data and results once known.

## Reference Columns

This template includes all columns for comprehensive bet tracking and analysis. Use this as a reference when logging bets via `modules/utilities/sandbox_persistence.OmegaCacheLogger.log_bet_recommendation()`.

### Required Columns (for log_bet_recommendation)

| Column | Description | Example | Required |
| --- | --- | --- | --- |
| **bet_id** | Unique identifier | `2025-11-24_NBA_1` | Auto-generated |
| **date** | Date of bet/game | `2025-11-24` | Yes |
| **league** | League identifier | `NBA`, `NFL`, `MLB`, `NHL` | Yes |
| **matchup** | Teams/participants | `Pistons vs Pacers` | Yes |
| **game_id** | Unique game identifier | `NBA_DET_IND` | Optional |
| **pick** | Bet selection | `DET -9.5`, `Over 225.5` | Yes |
| **bet_type** | Type of bet | `spread`, `total`, `moneyline`, `prop` | Yes |
| **odds** | Opening odds (American) | `-110`, `+150` | Yes |
| **implied_prob** | Implied probability from odds | `0.524` | Yes |
| **model_prob** | Model probability | `0.54` | Yes |
| **edge_pct** | Edge percentage | `1.6` | Yes |
| **confidence** | Confidence tier | `High`, `Medium`, `Low` | Yes |
| **predicted_outcome** | Model prediction | `DET 123, IND 110` | Yes |
| **factors** | Key factors/explanation | `Home court advantage; back-to-back` | Yes |

### Optional Columns

| Column | Description | Example | When Added |
| --- | --- | --- | --- |
| **stake_units** | Stake in units | `2.5` | When staking calculated |
| **stake_amount** | Stake in dollars | `12.50` | When staking calculated |
| **result** | Bet outcome | `Win`, `Loss`, `Push` | After game finishes |
| **final_score** | Actual final score | `DET 125, IND 115` | After game finishes |
| **closing_odds** | Closing odds (American) | `-112` | After market closes |
| **clv_pct** | Closing Line Value % | `0.45` | Calculated from closing odds |
| **logged_at** | Timestamp when logged | `2025-11-24T13:00:00Z` | Auto-generated |
| **updated_at** | Timestamp when updated | `2025-11-24T23:30:00Z` | Auto-updated |

### Additional Reference Columns (for manual tracking)

| Column | Description | Example | Notes |
| --- | --- | --- | --- |
| **bookmaker** | Betting platform | `DraftKings`, `FanDuel` | Manual tracking |
| **event_date** | Scheduled game date/time | `2025-11-24 19:00 EST` | Manual tracking |
| **potential_payout** | Potential return if win | `22.73` | Calculated: stake × (decimal_odds - 1) |
| **actual_payout** | Actual amount received | `22.73` | After bet settles |
| **pnl** | Profit/Loss | `+10.23` or `-12.50` | Calculated after result |

## BetLog.csv Format (Cumulative Export)

The cumulative `BetLog.csv` export uses this format (matches existing BetLog.csv):

| Date | League | Game_ID | Pick | Odds_American | Implied_Prob | Model_Prob | Edge_% | Confidence_Tier | Predicted Outcome | Factors | Final Box Score | Result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2025-11-24 | NBA | DET_IND | DET -9.5 | -110 | 0.524 | 0.54 | 1.6 | 🔵 High | DET 123, IND 110 | Home court advantage | DET 125, IND 115 | Win |

**Confidence Tier Format in CSV:**
- `🔵 High` for High confidence
- `🟢 Med` for Medium confidence  
- `🟡 Low` for Low confidence

## Instructions

1. **Log immediately**: Use `modules/utilities/sandbox_persistence.OmegaCacheLogger.log_bet_recommendation()` after generating each bet recommendation (even before placing the bet).

2. **Update closing odds**: Once market closes, update with `logger.update_bet_result(bet_id, result=None, closing_odds="-112")` to calculate CLV.

3. **Update results**: After game finishes, update with `logger.update_bet_result(bet_id, result="Win", final_score="DET 125, IND 115")`.

4. **Cumulative export**: Use `logger.update_pending_bets_and_export()` in TASK 2 to generate cumulative BetLog.csv with all historical bets.

5. **Reference for audits**: Bet logs are stored in `data/logs/bet_log.json` during session and exported to `data/exports/BetLog.csv`. Files must be delivered as attachments at end of task to persist across sessions.

## Example Bet Record (JSON format in bet_log.json)

```json
{
  "bet_id": "2025-11-24_NBA_1",
  "date": "2025-11-24",
  "league": "NBA",
  "matchup": "Pistons vs Pacers",
  "game_id": "NBA_DET_IND",
  "pick": "DET -9.5",
  "bet_type": "spread",
  "odds": "-110",
  "implied_prob": 0.524,
  "model_prob": 0.54,
  "edge_pct": 1.6,
  "confidence": "High",
  "predicted_outcome": "DET 123, IND 110",
  "factors": "Pistons home court advantage; Pacers on back-to-back",
  "stake_units": 2.5,
  "result": "Win",
  "final_score": "DET 125, IND 115",
  "closing_odds": "-112",
  "clv_pct": 0.45,
  "logged_at": "2025-11-24T13:00:00Z",
  "updated_at": "2025-11-24T23:30:00Z"
}
```

## Notes

- All bets are automatically logged to `data/logs/bet_log.json` via `OmegaCacheLogger` during the session
- **IMPORTANT**: Files in sandbox may not persist after session ends - must be delivered as attachments
- The cumulative `BetLog.csv` is generated daily via task and contains all historical bets
- Files are delivered as attachments at end of each task and retrieved from previous thread attachments
- Use this template as a reference for required and optional fields when logging bets
- For manual tracking outside the system, you can use the additional reference columns

