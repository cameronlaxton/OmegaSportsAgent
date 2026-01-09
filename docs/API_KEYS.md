## API Keys & GitHub Secrets

Set these as GitHub Actions secrets (Repo Settings → Secrets → Actions):

| Secret | Service | Purpose | Notes |
| ------ | -------- | ------- | ----- |
| `ODDS_API_KEY` | The Odds API | Live odds for games/props | Free tier: 500 req/mo |
| `BALLDONTLIE_API_KEY` | BallDontLie | NBA/NFL stats | Free tier available |

Usage in workflows:
- Daily predictions: `main.py --morning-bets` (uses both)
- Daily grading: `omega.workflows.daily_grading` (BallDontLie)
- Weekly calibration: `lab/core/calibration_runner.py --use-agent-outputs` (uses both)

Local override (optional):
```bash
export ODDS_API_KEY=your_key
export BALLDONTLIE_API_KEY=your_key
```

