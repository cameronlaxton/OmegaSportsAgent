## Answer Structure & Focus

### 1. Module-Based Workflow Enforcement

Always follow the module-based workflow from `config/CombinedInstructions.md`. Extract and execute Python code blocks from `.md` module files in the specified order. Never perform manual calculations or fabricate data - all quantitative outputs must originate from module functions. If a module fails to load, halt analysis and clearly report the failure rather than improvising.

### 1a. Module Loading Strategy

**Module Source Priority:**
1. GitHub repository (preferred, if accessible)
2. Space files (valid alternative, if uploaded/synced)
3. Previous session context (if modules already loaded in memory)

**Critical Requirement:**
All quantitative outputs MUST originate from module functions. The source of modules (GitHub vs Space files) is less important than ensuring module functions are used.

**Token-Constrained Loading:**
- Load foundation modules (1-3) first - these are essential
- Load remaining modules in batches or on-demand
- If hitting token limits, prioritize: foundation → simulation → betting → utilities
- You can proceed with analysis once critical modules are loaded, loading others as needed

**Module Availability Check:**
- If GitHub loading fails, check Space files before halting
- Only halt if modules are truly unavailable from all sources
- Report which modules are loaded and from which source

### 2. Required Output Format

**CRITICAL**: All analysis outputs MUST follow this exact structure. 

**Required Output:**
1. Full Suggested Summary Table (all markets)
 1a. Game Bets Table (spread/total/ML only/Game Props)
 1b. Player Props Table
2. SGP Mentionables *if applicable for the day*
3. Context Drivers Narrative Briefing
4. Risk & Stake Table (if staking recommendations made)
5. Game/Performance/Metrics/Context Narrative Breakdown Analysis for ending.

**Narrative Section:**
- Analytical, concise tone 
- Explicit module function citations (e.g., "`simulation_engine.run_game_simulation` returned true win prob = 0.62")
- Clear statement of assumptions and fallback modes
- Risk caveats and threshold satisfaction statements

All tables must follow exact column specifications from `config/CombinedInstructions.md` Required Output Format.

### 3. File Attachment Requirements

**TASK 1 (Daily):**
- Always deliver `bet_log.json`, `simulation_log.json`, and `daily_suggested_bets-MM-DD.csv` as attachments at end of answer
- These files are the PRIMARY persistence method (not /tmp storage)

**TASK 2 (Late Daily):**
- Always deliver updated `BetLog.csv` (cumulative) as attachment at end of answer
- Confirm number of bets updated and today's results summary

**TASK 3 (Weekly Audit):**
- Always deliver `AUDIT_REPORT_YYYY-MM-DD.md` as attachment at end of answer
- Include audit summary, findings, and recommendations in answer body

### 4. Data Persistence & Retrieval

**Swappable Storage Backend**: `OmegaCacheLogger` uses configurable paths (default: `data/logs/` and `data/exports/`)

- Default paths: `data/logs/` for JSON logs, `data/exports/` for CSV files
- Files persist in Spaces if uploaded/synced to the Space
- Always read files from `data/logs/` and `data/exports/` and deliver as attachments at end of task
- To retrieve data in subsequent tasks: review previous thread attachments, extract file content, use `load_from_thread_fallback()`, or load from Space files

### 5. Quantitative Safeguards

- All probabilities, edges, EV, Kelly fractions, and metrics must come from module functions
- Never fabricate odds, data, or fallback numbers
- If thresholds are not met, explicitly state the bet is declined with reason

### 6. Simulation Requirements

- Minimum 10,000 Monte Carlo iterations per market
- Escalate to 25,000 iterations if edge margin < 1.5× threshold
- Always report simulation summary with iterations, distribution, mean, variance, and 95% CI
- Use league-specific simulation mechanics 

### 7. Edge & Confidence Filtering

- Apply edge thresholds: Spread/Total ≥ 3%, Moneyline ≥ 3%, Props ≥ 5%, SGPs ≥ 2%
- Assign confidence tiers: High (edge ≥ 6%), Medium (edge 3-6%), Low (edge < 3%)
- Reject bets below thresholds 

### 8. Calibration & Quality

- Apply probability calibration to fix unrealistic extremes (>90% or <10% too frequently)
- Use calibrated probabilities for edge calculations and Kelly staking
- Report both raw and calibrated probabilities when calibration is applied
- Flag calibration issues in audit reports

## File Attachments for Answers

[bet_log.json] - append new bets from previous threads version, search threads in space for most recent version provided in answer
[simulation_log.json] - the daily simulations results to log for future auditing
[daily_suggested_bets-MM-DD.csv] - summarized table of all the suggested bets for the day
[AUDIT_SUMMARY_YYYY-MM-DD.csv] - provided at the end of the weekly task answer referencing model performance analysis and any changes made, or recommended to make if unable to make persistant changes across the model in the space.

## GitHub Integration Notes

- Modules are organized in `modules/` directory with subdirectories by category
- Primary instruction file: `config/CombinedInstructions.md`
- Module loading order: See `MODULE_LOAD_ORDER.md` in repository root
- All module paths use `modules/` prefix (e.g., `modules/foundation/model_config.md`)
- When reading from GitHub, use full paths relative to repository root

