# Integration Guide: OmegaSports Validation Lab ↔ OmegaSportsAgent

**Version:** 1.0.0  
**Date:** 2026-01-05  
**Status:** Design Complete, Implementation Pending

---

## Overview

This guide describes how to integrate the OmegaSports Validation Lab (calibrator) with OmegaSportsAgent (simulation engine) for automated parameter tuning and deployment.

### Current State (Phase 1)
- ✅ Validation Lab: DB-only backtesting and calibration
- ✅ Calibration Pack Schema defined (JSON)
- ✅ Adapter stubs created for future integration
- ⏳ OmegaSportsAgent: Not yet linked (open in separate window)

### Future State (Phase 2)
- 🔄 OmegaSportsAgent outputs → Validation Lab (for analysis)
- 🔄 Calibration Pack → OmegaSportsAgent (for deployment)
- 🔄 Automated feedback loop

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   OmegaSports Ecosystem                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────┐      ┌──────────────────────┐   │
│  │  OmegaSportsAgent     │      │  Validation Lab      │   │
│  │  (Simulation Engine)  │◄────►│  (Calibrator)        │   │
│  │                       │      │                      │   │
│  │  • Live predictions   │      │  • Historical data   │   │
│  │  • Monte Carlo sims   │      │  • Backtesting       │   │
│  │  • JSON outputs       │      │  • Calibration       │   │
│  └──────────────────────┘      └──────────────────────┘   │
│           │                              │                 │
│           │ (1) Agent Outputs            │ (2) Calibration │
│           │     (JSON)                   │     Pack (JSON) │
│           ▼                              ▼                 │
│  ┌──────────────────────────────────────────────────────┐ │
│  │           adapters/agent_outputs_adapter.py          │ │
│  │           adapters/apply_calibration.py              │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### Flow 1: Agent → Lab (Analysis)

**Purpose:** Analyze agent performance and identify calibration opportunities

```
OmegaSportsAgent/outputs/*.json
    ↓
adapters/agent_outputs_adapter.py (parse & validate)
    ↓
core/calibration_runner.py (analyze performance)
    ↓
data/experiments/backtests/{run_id}/metrics.json
```

**Implementation Status:** ⏳ Stub (not yet implemented)

**Expected Agent Output Format:**
```json
{
  "date": "2026-01-05",
  "league": "NBA",
  "bets": [
    {
      "game_id": "401234567",
      "market_type": "spread",
      "recommendation": "HOME",
      "edge": 0.045,
      "model_probability": 0.545,
      "market_probability": 0.500,
      "stake": 2.5,
      "confidence": "high"
    }
  ]
}
```

### Flow 2: Lab → Agent (Deployment)

**Purpose:** Deploy calibrated parameters to production agent

```
core/calibration_runner.py (run calibration)
    ↓
data/experiments/backtests/{run_id}/calibration_pack.json
    ↓
adapters/apply_calibration.py (generate patch plan)
    ↓
[Manual Review & Approval]
    ↓
OmegaSportsAgent/config/*.py (updated parameters)
```

**Implementation Status:** ✅ Stub created, prints patch plan

**Calibration Pack Format:**
```json
{
  "version": "1.0.0",
  "league": "NBA",
  "edge_thresholds": {
    "moneyline": 0.02,
    "spread": 0.03,
    "total": 0.03
  },
  "kelly_policy": {
    "method": "fractional",
    "fraction": 0.25,
    "max_stake": 0.05
  },
  "metrics": {
    "roi": 0.053,
    "sharpe": 1.25,
    "hit_rate": 0.523
  }
}
```

See: [calibration_pack_schema.json](calibration_pack_schema.json) for complete schema.

---

## Integration Scenarios

### Scenario A: DB-Only Calibration (Current - Phase 1)

**Use Case:** Calibrate parameters using only Validation Lab historical data

**Workflow:**
1. Validation Lab has complete historical data in `sports_data.db`
2. Run calibration pipeline: `python -m core.calibration_runner --league NBA`
3. Review metrics and reliability curves
4. Generate calibration pack: `calibration_pack_nba.json`
5. **Manually** apply parameters to OmegaSportsAgent config files

**Status:** ✅ Implemented

**Commands:**
```bash
# Run calibration
python -m core.calibration_runner \
    --league NBA \
    --start-date 2020-01-01 \
    --end-date 2024-12-31 \
    --output calibration_pack_nba.json

# Generate patch plan (dry-run)
python -m adapters.apply_calibration \
    --calibration-pack calibration_pack_nba.json \
    --agent-repo ~/OmegaSportsAgent

# Manually update OmegaSportsAgent config files
# (Future: Automated application)
```

### Scenario B: Agent Output Analysis (Future - Phase 2)

**Use Case:** Analyze OmegaSportsAgent live performance and re-calibrate

**Workflow:**
1. OmegaSportsAgent runs for N days, outputs JSON files
2. Validation Lab ingests outputs: `adapters/agent_outputs_adapter.py`
3. Compare actual results vs. predictions
4. Re-calibrate if needed
5. Deploy updated calibration pack

**Status:** ⏳ Not implemented (stub exists)

**Future Commands:**
```bash
# Ingest agent outputs
python -m adapters.agent_outputs_adapter \
    --agent-repo ~/OmegaSportsAgent \
    --start-date 2026-01-01 \
    --end-date 2026-01-31

# Re-run calibration with agent data
python -m core.calibration_runner \
    --league NBA \
    --use-agent-outputs \
    --start-date 2026-01-01 \
    --end-date 2026-01-31
```

### Scenario C: Automated Feedback Loop (Future - Phase 3)

**Use Case:** Continuous calibration and deployment

**Workflow:**
1. OmegaSportsAgent runs and outputs data
2. Validation Lab automatically ingests outputs (daily cron)
3. Re-calibrates weekly if performance drifts
4. Generates new calibration pack
5. **Optionally** auto-applies with human approval

**Status:** 🔮 Future work

---

## Implementation Roadmap

### Phase 1: DB-Only Calibration ✅ COMPLETE
- [x] Create `core/calibration_runner.py`
- [x] Implement edge threshold tuning
- [x] Implement metrics calculation (ROI, Sharpe, Brier)
- [x] Generate calibration pack JSON
- [x] Define calibration pack schema
- [x] Create adapter stubs

### Phase 2: Agent Integration (Next)
- [ ] Implement `AgentOutputsAdapter.load_outputs()`
- [ ] Define agent output schema (coordinate with agent team)
- [ ] Parse agent JSON files
- [ ] Validate agent output data
- [ ] Integrate with calibration pipeline

### Phase 3: Automated Application
- [ ] Implement `CalibrationApplicator.apply_patch()`
- [ ] Read current parameters from agent config
- [ ] Generate detailed diff/patch
- [ ] Apply changes with user confirmation
- [ ] Add rollback mechanism
- [ ] Add automated testing before/after

### Phase 4: Continuous Calibration
- [ ] Scheduled calibration runs (cron)
- [ ] Drift detection (performance degradation)
- [ ] Alert system for significant changes
- [ ] A/B testing framework
- [ ] Production monitoring dashboard

---

## Schema Contracts

### Calibration Pack Schema

**File:** `docs/calibration_pack_schema.json`  
**Version:** 1.0.0

**Required Fields:**
- `version`: Schema version (semantic versioning)
- `league`: League (NBA, NFL, etc.)
- `edge_thresholds`: Dict of thresholds by market type
- `variance_scalars`: Dict of variance adjustments
- `kelly_policy`: Staking policy parameters
- `metrics`: Performance metrics from test period

**Validation:** JSON Schema validation before deployment

### Agent Output Schema (Expected)

**Status:** ⏳ Not yet defined (coordinate with agent team)

**Expected Fields:**
```json
{
  "date": "string (YYYY-MM-DD)",
  "league": "string",
  "bets": [
    {
      "game_id": "string",
      "market_type": "string (moneyline|spread|total|props)",
      "recommendation": "string (HOME|AWAY|OVER|UNDER)",
      "edge": "number (0.0-1.0)",
      "model_probability": "number (0.0-1.0)",
      "market_probability": "number (0.0-1.0)",
      "stake": "number",
      "confidence": "string (high|medium|low)"
    }
  ],
  "metadata": {
    "simulations_run": "integer",
    "execution_time_ms": "number"
  }
}
```

**Validation:** TBD (implement in `AgentOutputsAdapter.validate_schema()`)

---

## Adapter Configuration

### AgentOutputsAdapter Configuration

**Location:** `adapters/agent_outputs_adapter.py`

**Configuration (Future):**
```python
adapter = AgentOutputsAdapter(
    agent_repo_path="/path/to/OmegaSportsAgent",
    outputs_dir="outputs",  # Relative to agent repo
    file_pattern="recommendations_*.json",
    cache_dir="data/cache/agent_outputs"
)
```

### CalibrationApplicator Configuration

**Location:** `adapters/apply_calibration.py`

**Configuration (Future):**
```python
applicator = CalibrationApplicator(
    agent_repo_path="/path/to/OmegaSportsAgent",
    parameter_files={
        'edge_thresholds': 'config/thresholds.py',
        'variance_scalars': 'config/variance.py',
        'kelly_policy': 'config/staking.py'
    },
    backup_dir="data/backups/agent_configs"
)
```

---

## Testing Strategy

### Unit Tests
- [ ] Test calibration pack validation
- [ ] Test agent output parsing
- [ ] Test parameter diff generation
- [ ] Test patch application (dry-run)

### Integration Tests
- [ ] End-to-end calibration pipeline
- [ ] Agent output ingestion → calibration → pack generation
- [ ] Patch generation → validation → application

### Validation Tests
- [ ] JSON schema validation
- [ ] Parameter range validation
- [ ] Backward compatibility tests

---

## Error Handling

### Common Errors

**1. Agent Output Schema Mismatch**
```
Error: Invalid agent output schema
Field 'edge' missing in bet recommendation

Solution: Check agent output format against expected schema
```

**2. Calibration Pack Version Mismatch**
```
Error: Calibration pack version 1.0.0 not compatible with agent version 2.0.0

Solution: Update calibration pack schema or agent parser
```

**3. Parameter File Not Found**
```
Error: Could not locate parameter file: config/thresholds.py

Solution: Update PARAMETER_FILES mapping in CalibrationApplicator
```

---

## Security & Safety

### Safety Measures

1. **No Automatic Application:** Require manual approval for parameter changes
2. **Dry-Run First:** Always generate patch plan before applying
3. **Backup Before Apply:** Backup config files before modification
4. **Validation After Apply:** Run agent tests after parameter changes
5. **Rollback Mechanism:** Keep previous calibration packs for quick rollback

### Security Considerations

1. **No Credentials in Packs:** Calibration packs contain no secrets
2. **Version Control:** All calibration packs in git for audit trail
3. **Code Review:** Parameter changes require PR review
4. **Testing Gate:** Changes must pass agent test suite

---

## Troubleshooting

### Issue: Adapter not finding agent outputs

**Symptoms:**
```
FileNotFoundError: No such file or directory: 'outputs/recommendations_20260105.json'
```

**Solutions:**
1. Check agent repo path is correct
2. Verify outputs directory exists
3. Check file naming pattern matches
4. Ensure agent has run and generated outputs

### Issue: Calibration pack validation fails

**Symptoms:**
```
ValidationError: 'edge_thresholds' is a required property
```

**Solutions:**
1. Check calibration pack against schema
2. Verify all required fields present
3. Check data types match schema
4. Validate value ranges (0-1 for probabilities, etc.)

### Issue: Patch application fails

**Symptoms:**
```
NotImplementedError: CalibrationApplicator.apply_patch() is a stub
```

**Solutions:**
1. This is expected - auto-application not yet implemented
2. Use patch plan to manually update agent config
3. Follow manual application instructions in patch plan notes

---

## FAQ

### Q: Can I run calibration without OmegaSportsAgent?

**A:** Yes! Phase 1 (DB-only calibration) works independently using historical data in `sports_data.db`. You only need the agent for Phase 2+ (analyzing live outputs).

### Q: How often should I re-calibrate?

**A:** Recommended schedule:
- Weekly: Check performance metrics
- Monthly: Re-calibrate if ROI drops >1%
- Quarterly: Full re-calibration with latest data
- Ad-hoc: After significant market changes or injuries

### Q: What if calibration degrades performance?

**A:** Safety measures:
1. Always test on historical data first
2. Use A/B testing (old vs. new parameters)
3. Monitor live performance closely
4. Keep previous calibration pack for rollback
5. Revert if ROI drops >2% within 1 week

### Q: Can I calibrate multiple leagues simultaneously?

**A:** Yes, but run separate calibration for each league:
```bash
python -m core.calibration_runner --league NBA --output pack_nba.json
python -m core.calibration_runner --league NFL --output pack_nfl.json
```

### Q: How do I share calibration packs between team members?

**A:** Calibration packs are JSON files in git:
1. Commit calibration pack to repo
2. Push to shared branch
3. Team members pull and review
4. Apply after code review approval

---

## Next Steps

### Immediate (Phase 1 Complete) ✅
1. ✅ Create calibration runner
2. ✅ Define calibration pack schema
3. ✅ Create adapter stubs
4. ✅ Document integration workflow

### Next (Phase 2 - Agent Integration)
1. Coordinate with OmegaSportsAgent team on output schema
2. Implement `AgentOutputsAdapter.load_outputs()`
3. Test with sample agent outputs
4. Integrate with calibration pipeline

### Future (Phase 3 - Automation)
1. Implement `CalibrationApplicator.apply_patch()`
2. Add automated testing
3. Build continuous calibration system
4. Add monitoring and alerts

---

## Contact & Support

**Questions about integration?**
- See: [ARCHITECTURE.md](../ARCHITECTURE.md) for system design
- See: [docs/audit_repo.md](audit_repo.md) for repo structure
- See: [calibration_pack_schema.json](calibration_pack_schema.json) for schema

**Need help?**
- File an issue: GitHub Issues
- Check examples: `examples/` directory
- Review tests: `tests/` directory

---

**Status:** ✅ Phase 1 Complete - Ready for Phase 2 Agent Integration  
**Last Updated:** 2026-01-05
